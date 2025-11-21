"""
LLM-Based Classification Agent - 10 Categories (Phase 8)

Extended LLM classification with:
- 10 fine-grained categories (instead of 6)
- Primary + Secondary category detection
- Ollama-first + OpenAI fallback (unchanged)
- Agent SDK integration (unchanged)
- Structured outputs via Pydantic (enhanced)

Categories:
1. wichtig_todo - Action required, decisions, tasks
2. termine - Calendar, events, appointments
3. finanzen - Invoices, payments, financial
4. bestellungen - Orders, shipping, tracking
5. job_projekte - Business, projects, customers
6. vertraege - Contracts, authorities, formal
7. persoenlich - Family, friends, personal
8. newsletter - Regular updates, content
9. werbung - Marketing, promotions, sales
10. spam - Spam, phishing, junk
"""

import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from agents import Agent

from agent_platform.classification.models import EmailCategory, CATEGORY_IMPORTANCE_MAP
from agent_platform.llm.providers import get_llm_provider


# ============================================================================
# STRUCTURED OUTPUT MODEL (Enhanced for 10 Categories + Primary/Secondary)
# ============================================================================

class LLMClassificationOutput10Cat(BaseModel):
    """
    Enhanced structured output for 10-category classification.

    Supports:
    - Primary category (1 per email)
    - Secondary categories (0-3 additional tags)
    - Category-based importance scoring
    - Confidence and reasoning
    """

    primary_category: EmailCategory = Field(
        ...,
        description="The primary/main category for this email (one of: wichtig_todo, termine, finanzen, bestellungen, job_projekte, vertraege, persoenlich, newsletter, werbung, spam)"
    )

    secondary_categories: List[EmailCategory] = Field(
        default_factory=list,
        max_length=3,
        description="Optional secondary/additional categories (0-3 tags). Use when email fits multiple categories. Example: An email about a project meeting with invoice attached would be primary=wichtig_todo, secondary=[termine, finanzen]"
    )

    importance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (low priority) to 1.0 (high priority). Consider: urgency, requires action, sender importance, content significance."
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this classification from 0.0 (uncertain) to 1.0 (certain). Be honest - if unsure, use lower confidence."
    )

    reasoning: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="Brief explanation (2-3 sentences) of why this classification was chosen. Mention key signals that led to the decision."
    )

    key_signals: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Key signals that influenced the classification (max 5). Examples: 'Rechnung im Subject', 'Fragezeichen am Ende', 'Tracking-Nummer', 'Absender ist Shop'"
    )


# ============================================================================
# PROMPTS (Updated for 10 Categories + Primary/Secondary)
# ============================================================================

SYSTEM_PROMPT_10CAT = """Du bist ein intelligenter Email-Klassifizierungs-Assistent.

Deine Aufgabe ist es, Emails in 10 fein-granulare Kategorien einzuordnen mit PRIMARY + SECONDARY Klassifikation:

**PRIMARY CATEGORY** (genau EINE):

1. **wichtig_todo** - Emails die AKTION erfordern
   - Rückfragen, Entscheidungen, Aufgaben
   - Fragezeichen im Subject (?)
   - "Bitte um Rückmeldung", "Action Required", "Dringend"
   - Deadlines, Fristen, "bis wann"

2. **termine** - Kalender & Veranstaltungen
   - Meeting-Einladungen (Zoom, Teams)
   - Termine, Appointments
   - "Einladung", "Event", "Veranstaltung"
   - Datum/Uhrzeit im Text
   - .ics Anhänge

3. **finanzen** - Finanz & Rechnungen
   - Rechnungen, Invoices
   - Zahlungen, Überweisungen
   - Mahnungen, Kontoauszüge
   - "Rechnung", "Invoice", "Betrag", "IBAN"
   - PDF-Rechnungen als Anhang

4. **bestellungen** - Bestellungen & Versand
   - Bestellbestätigungen
   - Tracking-Nummern
   - Versand-Updates, Lieferstatus
   - "Bestellung #", "Order Confirmation", "Tracking"

5. **job_projekte** - Berufliche Kommunikation
   - Projekt-Updates
   - Kunden-Emails
   - Business-Kommunikation
   - "Projekt", "Client", "Kunde", "Proposal"

6. **vertraege** - Verträge & Offizielles
   - Verträge, Vereinbarungen
   - Behörden-Post (Amt, Stadt, Finanzamt)
   - Rechtliche Dokumente
   - Vermieter, Stadtwerke
   - "Vertrag", "Behörde", "Aktenzeichen"

7. **persoenlich** - Persönliche Nachrichten
   - Familie, Freunde
   - Private Verabredungen
   - Freemail-Adressen (gmail, gmx, web.de)
   - "Hallo!", "Hey", "Liebe Grüße"

8. **newsletter** - Newsletter & Infos
   - Regelmäßige Updates
   - Content-Newsletter, Blogs
   - "Newsletter", "Weekly Update", "Digest"
   - "Unsubscribe" Link
   - Bulk/Marketing Headers

9. **werbung** - Marketing & Promo
   - Rabatt-Aktionen, Sales
   - Produktwerbung
   - "50% Rabatt", "Sale", "Limited Offer"
   - "Jetzt kaufen", "Shop now"

10. **spam** - Spam & Phishing
    - Offensichtlicher Spam
    - Phishing-Versuche
    - "Gewinnspiel", "Gewonnen", "Viagra"
    - Verdächtige Links
    - "Verify Account Immediately"

**SECONDARY CATEGORIES** (0-3 zusätzliche Tags):

Nutze Secondary Categories wenn Email in MEHRERE Kategorien passt:
- Email über Projekt-Meeting mit Rechnung → PRIMARY: wichtig_todo, SECONDARY: [termine, finanzen]
- Bestellbestätigung mit Rechnung → PRIMARY: bestellungen, SECONDARY: [finanzen]
- Meeting-Einladung die Antwort braucht → PRIMARY: wichtig_todo, SECONDARY: [termine]

**WICHTIGKEIT** (0.0 - 1.0):
- wichtig_todo, termine, vertraege: 0.85-0.95 (sehr wichtig)
- finanzen, job_projekte: 0.75-0.85 (wichtig)
- bestellungen, persoenlich: 0.65-0.75 (mittel)
- newsletter: 0.30-0.50 (niedrig)
- werbung: 0.15-0.30 (sehr niedrig)
- spam: 0.00-0.10 (minimal)

**CONFIDENCE** (0.0 - 1.0):
- 0.9-1.0: Sehr sicher (klare Signale)
- 0.7-0.9: Sicher (mehrere Signale)
- 0.5-0.7: Mittlere Sicherheit (einige Signale)
- 0.3-0.5: Unsicher (wenige Signale)
- 0.0-0.3: Sehr unsicher (keine klaren Signale)

Analysiere die Email sorgfältig und gib PRIMARY + SECONDARY Klassifizierung zurück."""


def build_user_prompt_10cat(
    email_id: str,
    subject: str,
    body: str,
    sender: str,
    rule_context: Optional[Dict[str, Any]] = None,
    history_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build user prompt with email content and context for 10-category classification.

    Args:
        email_id: Email ID
        subject: Email subject
        body: Email body
        sender: Sender email address
        rule_context: Optional context from Rule Layer (10-cat version)
        history_context: Optional context from History Layer

    Returns:
        Formatted user prompt string
    """
    prompt_parts = []

    # Email content
    prompt_parts.append("📧 EMAIL ZU KLASSIFIZIEREN:")
    prompt_parts.append(f"Von: {sender}")
    prompt_parts.append(f"Betreff: {subject}")
    prompt_parts.append(f"\nNachricht:\n{body[:1000]}")  # First 1000 chars

    # Context from Rule Layer (10-cat version)
    if rule_context:
        prompt_parts.append("\n--- 🔍 KONTEXT AUS REGEL-ANALYSE (10 Kategorien) ---")

        if rule_context.get('primary_category'):
            primary = rule_context['primary_category']
            conf = rule_context.get('primary_confidence', 0)
            prompt_parts.append(f"Regel-Vorschlag PRIMARY: {primary} (Confidence: {conf:.2f})")

        if rule_context.get('secondary_categories'):
            secondary = ', '.join(rule_context['secondary_categories'])
            prompt_parts.append(f"Regel-Vorschlag SECONDARY: {secondary}")

        if rule_context.get('reasoning'):
            prompt_parts.append(f"Begründung: {rule_context['reasoning']}")

    # Context from History Layer
    if history_context:
        if history_context.get('sender_preference_found'):
            prompt_parts.append("\n--- 📊 KONTEXT AUS SENDER-HISTORIE ---")
            prompt_parts.append(f"Sender: {history_context['sender_email']}")
            prompt_parts.append(f"Historische Emails: {history_context['total_historical_emails']}")

            if history_context.get('historical_reply_rate') is not None:
                reply_rate = history_context['historical_reply_rate']
                prompt_parts.append(f"Antwort-Rate: {reply_rate:.0%}")

            if history_context.get('average_importance') is not None:
                avg_imp = history_context['average_importance']
                prompt_parts.append(f"Durchschnittliche Wichtigkeit: {avg_imp:.2f}")

            if history_context.get('preferred_primary_category'):
                pref_cat = history_context['preferred_primary_category']
                prompt_parts.append(f"Bevorzugte Kategorie: {pref_cat}")

        elif history_context.get('domain_preference_found'):
            prompt_parts.append("\n--- 📊 KONTEXT AUS DOMAIN-HISTORIE ---")
            prompt_parts.append(f"Domain: {history_context['sender_domain']}")
            prompt_parts.append(f"Historische Emails von dieser Domain: {history_context['total_historical_emails']}")

    # Instructions
    prompt_parts.append("\n--- 🎯 AUFGABE ---")
    prompt_parts.append("Klassifiziere diese Email in PRIMARY + SECONDARY Kategorien.")
    prompt_parts.append("Berücksichtige:")
    prompt_parts.append("1. Den Email-Inhalt (Betreff + Nachricht)")
    prompt_parts.append("2. Die Regel-Analyse (falls vorhanden)")
    prompt_parts.append("3. Die Sender-Historie (falls vorhanden)")
    prompt_parts.append("")
    prompt_parts.append("Gib zurück:")
    prompt_parts.append("- primary_category: Die EINE Hauptkategorie")
    prompt_parts.append("- secondary_categories: 0-3 zusätzliche passende Kategorien")
    prompt_parts.append("- importance_score: 0.0-1.0 basierend auf Kategorie")
    prompt_parts.append("- confidence: 0.0-1.0 basierend auf Signalstärke")
    prompt_parts.append("- reasoning: 2-3 Sätze Begründung")
    prompt_parts.append("- key_signals: Max 5 wichtige Signale")

    return "\n".join(prompt_parts)


async def classify_email_with_llm_10cat(
    email_id: str,
    subject: str,
    body: str,
    sender: str,
    rule_context: Optional[Dict[str, Any]] = None,
    history_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Classify email using LLM with 10 categories + primary/secondary.

    Strategy (unchanged):
    - Primary: Try Ollama first (local, free)
    - Fallback: Use OpenAI on any error (cloud, paid)
    - Structured output: Use Pydantic model for type safety

    Args:
        email_id: Email ID
        subject: Email subject
        body: Email body
        sender: Sender email address
        rule_context: Optional context from Rule Layer (10-cat)
        history_context: Optional context from History Layer

    Returns:
        Dictionary with classification results:
        - primary_category: str
        - secondary_categories: List[str]
        - importance_score: float
        - confidence: float
        - reasoning: str
        - key_signals: List[str]
        - llm_provider_used: str (ollama or openai_fallback)
        - llm_response_time_ms: float
    """
    start_time = time.time()

    # Build prompts
    system_prompt = SYSTEM_PROMPT_10CAT
    user_prompt = build_user_prompt_10cat(
        email_id=email_id,
        subject=subject,
        body=body,
        sender=sender,
        rule_context=rule_context,
        history_context=history_context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Get LLM provider (Ollama-first + OpenAI fallback)
    provider = get_llm_provider()

    # Try classification with structured output
    try:
        # Call LLM with Pydantic model for structured output
        response, provider_used = await provider.complete(
            messages=messages,
            response_format=LLMClassificationOutput10Cat,
            temperature=0.1,  # Low temperature for consistent classification
        )

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Extract parsed model from response
        # OpenAI returns ParsedChatCompletion[T], parsed model is in choices[0].message.parsed
        if hasattr(response, 'choices') and len(response.choices) > 0:
            parsed_model = response.choices[0].message.parsed
        else:
            # Fallback for direct Pydantic model
            parsed_model = response

        # Convert Pydantic model to dict
        result = {
            'primary_category': parsed_model.primary_category,
            'secondary_categories': parsed_model.secondary_categories,
            'importance_score': parsed_model.importance_score,
            'confidence': parsed_model.confidence,
            'reasoning': parsed_model.reasoning,
            'key_signals': parsed_model.key_signals,
            'llm_provider_used': provider_used,  # ollama or openai
            'llm_response_time_ms': response_time_ms,
        }

        return result

    except Exception as e:
        # Fallback: Return low-confidence default
        response_time_ms = (time.time() - start_time) * 1000

        return {
            'primary_category': 'newsletter',  # Safe default
            'secondary_categories': [],
            'importance_score': 0.40,
            'confidence': 0.20,
            'reasoning': f"LLM classification failed: {str(e)[:100]}. Defaulting to newsletter category.",
            'key_signals': ['llm_error'],
            'llm_provider_used': 'error',
            'llm_response_time_ms': response_time_ms,
        }


# ============================================================================
# AGENT CREATION (Agent SDK Integration)
# ============================================================================

AGENT_INSTRUCTIONS_10CAT = """You are an intelligent email classification agent using 10 fine-grained categories.

Your job is to classify emails into:
- PRIMARY category (exactly ONE)
- SECONDARY categories (0-3 additional tags)

**10 Categories:**
1. wichtig_todo - Action required, decisions, tasks
2. termine - Calendar events, appointments
3. finanzen - Invoices, payments, financial
4. bestellungen - Orders, shipping, tracking
5. job_projekte - Business, projects, customers
6. vertraege - Contracts, authorities, formal
7. persoenlich - Family, friends, personal
8. newsletter - Regular updates, content
9. werbung - Marketing, promotions, sales
10. spam - Spam, phishing, junk

**Classification Process:**
1. Call classify_email_with_llm_10cat with email data
2. Consider context from Rule Layer and History Layer
3. Return structured result with primary + secondary categories
4. Set appropriate importance score based on category
5. Provide reasoning for the classification

**Importance Guidelines:**
- wichtig_todo, termine, vertraege: HIGH (0.85-0.95)
- finanzen, job_projekte: MEDIUM-HIGH (0.75-0.85)
- bestellungen, persoenlich: MEDIUM (0.65-0.75)
- newsletter: LOW (0.30-0.50)
- werbung: VERY LOW (0.15-0.30)
- spam: MINIMAL (0.00-0.10)

**Use secondary categories when:**
- Email fits multiple categories
- Example: Meeting invitation that needs response → primary=wichtig_todo, secondary=[termine]
- Example: Order confirmation with invoice → primary=bestellungen, secondary=[finanzen]
"""


def create_llm_agent_10cat() -> Agent:
    """
    Create LLM classification agent for 10 categories with Agent SDK.

    Returns:
        Agent instance configured for 10-category classification
    """
    agent = Agent(
        name="LLMClassifier10Cat",
        instructions=AGENT_INSTRUCTIONS_10CAT,
        tools=[classify_email_with_llm_10cat],
        model="gpt-4o-mini"  # Fast model for orchestration
    )

    return agent


# ============================================================================
# TEST FUNCTION
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_llm_10cat():
        """Test 10-category LLM classification"""

        test_emails = [
            {
                'id': '1',
                'subject': 'Rechnung für Ihre Bestellung #12345',
                'body': 'Vielen Dank für Ihre Bestellung. Betrag: 49,99€. Rechnungsnummer: INV-2025-001. Bitte überweisen Sie bis zum 15.12.2025.',
                'sender': 'billing@shop.de',
            },
            {
                'id': '2',
                'subject': 'Meeting morgen 10 Uhr - Bitte bestätigen',
                'body': 'Hallo, können wir uns morgen um 10 Uhr zu einem Projekt-Meeting treffen? Bitte bestätige kurz. Zoom Link: https://zoom.us/...',
                'sender': 'colleague@company.com',
            },
            {
                'id': '3',
                'subject': '50% RABATT - Nur heute!!!',
                'body': 'Super Angebot! Nur heute 50% Rabatt auf alles. Jetzt zuschlagen und sparen! Limited Time Offer!',
                'sender': 'marketing@shop.com',
            },
        ]

        print("=" * 80)
        print("10-CATEGORY LLM CLASSIFIER TEST")
        print("=" * 80)

        for email in test_emails:
            print(f"\n📧 Email {email['id']}: {email['subject']}")
            print("-" * 80)

            result = await classify_email_with_llm_10cat(
                email_id=email['id'],
                subject=email['subject'],
                body=email['body'],
                sender=email['sender'],
            )

            print(f"Primary: {result['primary_category']} (confidence: {result['confidence']:.2f})")
            print(f"Importance: {result['importance_score']:.2f}")
            if result['secondary_categories']:
                print(f"Secondary: {', '.join(result['secondary_categories'])}")
            print(f"Reasoning: {result['reasoning']}")
            print(f"Provider: {result['llm_provider_used']} ({result['llm_response_time_ms']:.0f}ms)")

    asyncio.run(test_llm_10cat())
