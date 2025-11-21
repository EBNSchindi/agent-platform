"""
NLP Intent Agent (Phase 5) - Agent SDK Integration

Parses natural language preference input into structured rules using OpenAI Agents SDK.

Examples:
- "Alle Werbemails von Zalando in Werbung verschieben"
- "Amazon auf die Whitelist setzen"
- "Newsletter von LinkedIn muten"
- "Keine Marketing-Emails von booking.com mehr"

Architecture:
- Agent SDK pattern (consistent with LLM Classification Agent)
- Ollama-first + OpenAI fallback
- Pydantic models for structured outputs
"""

import time
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from agents import Agent

from agent_platform.llm.providers import get_llm_provider


# ============================================================================
# PYDANTIC MODELS (Structured Output)
# ============================================================================

class ParsedIntent(BaseModel):
    """
    Structured intent parsed from natural language input.
    """
    intent_type: Literal[
        'whitelist_sender',
        'blacklist_sender',
        'set_trust_level',
        'mute_categories',
        'allow_only_categories',
        'remove_from_whitelist',
        'remove_from_blacklist',
        'unknown'
    ] = Field(description="Type of intent detected")

    sender_email: Optional[str] = Field(
        None,
        description="Sender email address (if specific email mentioned, e.g., 'info@zalando.de')"
    )

    sender_domain: Optional[str] = Field(
        None,
        description="Sender domain (if domain mentioned, e.g., 'zalando.de' when user says 'Emails von Zalando')"
    )

    sender_name: Optional[str] = Field(
        None,
        description="Sender name (if name mentioned without specific email, e.g., 'Amazon', 'LinkedIn')"
    )

    trust_level: Optional[Literal['trusted', 'neutral', 'suspicious', 'blocked']] = Field(
        None,
        description="Trust level to set (for set_trust_level intent)"
    )

    categories: List[str] = Field(
        default_factory=list,
        description="Categories to mute or allow (e.g., ['werbung', 'newsletter'])"
    )

    preferred_primary_category: Optional[str] = Field(
        None,
        description="Preferred primary category for this sender (e.g., 'wichtig_todo')"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence of the parser in this interpretation (0.0-1.0)"
    )

    reasoning: str = Field(
        description="Explanation of how the intent was parsed (2-3 sentences in German)"
    )

    key_signals: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Key signals that led to this interpretation (max 5)"
    )

    original_text: str = Field(
        default="",
        description="Original user input text"
    )


# ============================================================================
# AGENT PROMPTS
# ============================================================================

SYSTEM_PROMPT_NLP_INTENT = """Du bist ein intelligenter Email-Präferenz-Parser.

Deine Aufgabe ist es, natürliche Sprache in strukturierte Präferenz-Regeln zu übersetzen.

**Verfügbare Intent-Typen:**

1. **whitelist_sender** - Sender auf die Whitelist setzen
   - Beispiele: "Amazon auf die Whitelist", "Zalando vertrauen", "boss@company.com als vertrauenswürdig markieren"
   - Signale: "whitelist", "vertrauen", "vertrauenswürdig", "als wichtig markieren"

2. **blacklist_sender** - Sender blockieren/auf Blacklist setzen
   - Beispiele: "booking.com blockieren", "Spam von XYZ", "newsletter@promo.com sperren"
   - Signale: "blockieren", "sperren", "blacklist", "nicht mehr", "spam"

3. **set_trust_level** - Vertrauensstufe setzen
   - Werte: trusted, neutral, suspicious, blocked
   - Beispiele: "LinkedIn als vertrauenswürdig markieren", "Amazon als neutral setzen"
   - Signale: "vertrauenswürdig", "verdächtig", "neutral", "blocked"

4. **mute_categories** - Kategorien von Sender muten
   - Beispiele: "Werbung von Zalando muten", "Keine Newsletter von Amazon", "Marketing von LinkedIn ignorieren"
   - Signale: "muten", "ignorieren", "keine", "nicht mehr", "ausblenden"

5. **allow_only_categories** - Nur bestimmte Kategorien erlauben
   - Beispiele: "Nur Bestellungen von Amazon zeigen", "Von Zalando nur Rechnungen"
   - Signale: "nur", "ausschließlich", "lediglich"

6. **remove_from_whitelist** - Von Whitelist entfernen
   - Beispiele: "Amazon von Whitelist entfernen", "XYZ nicht mehr vertrauen"
   - Signale: "von whitelist entfernen", "nicht mehr vertrauen", "whitelist löschen"

7. **remove_from_blacklist** - Von Blacklist entfernen
   - Beispiele: "booking.com entsperren", "XYZ wieder zulassen"
   - Signale: "entsperren", "wieder zulassen", "von blacklist entfernen"

8. **unknown** - Intent nicht erkannt
   - Wenn Eingabe unklar oder nicht passend

**Verfügbare Email-Kategorien:**
- wichtig_todo (Wichtig & ToDo - Action Items, Aufgaben)
- termine (Termine & Einladungen - Kalender, Events)
- finanzen (Finanzen & Rechnungen - Rechnungen, Zahlungen)
- bestellungen (Bestellungen & Versand - Orders, Tracking)
- job_projekte (Job & Projekte - Business, Kunden)
- vertraege (Verträge & Behörden - Verträge, Offiziell)
- persoenlich (Persönliche Kommunikation - Familie, Freunde)
- newsletter (Newsletter & Infos - Updates, Content)
- werbung (Werbung & Promo - Marketing, Rabatte)
- spam (Spam - Phishing, Junk)

**Sender-Identifikation:**
- sender_email: Wenn spezifische Email-Adresse genannt (z.B. "info@zalando.de")
- sender_domain: Wenn Domain genannt (z.B. "zalando.de" bei "Emails von Zalando")
- sender_name: Wenn nur Name genannt (z.B. "Amazon" bei "Werbung von Amazon")

**Wichtige Parsing-Regeln:**
1. Erkenne Synonyme:
   - "Marketing", "Werbung", "Promo" → werbung
   - "Rechnungen", "Invoices", "Finanzen" → finanzen
   - "Bestellungen", "Orders", "Lieferungen" → bestellungen
   - "Newsletter", "Updates", "Digest" → newsletter

2. Erkenne Negationen:
   - "Keine Newsletter" → intent_type: mute_categories, categories: [newsletter]
   - "Nicht mehr" → meist mute_categories oder blacklist_sender

3. Erkenne Domains aus Namen:
   - "Amazon" → sender_domain: "amazon.de" oder sender_name: "Amazon"
   - "Zalando" → sender_domain: "zalando.de" oder sender_name: "Zalando"
   - "LinkedIn" → sender_domain: "linkedin.com" oder sender_name: "LinkedIn"

4. Confidence Levels:
   - 0.9-1.0: Sehr eindeutig (klare Aktion + klarer Sender)
   - 0.75-0.9: Eindeutig (Aktion klar, Sender identifizierbar)
   - 0.5-0.75: Wahrscheinlich (Aktion erkennbar, Sender unklar)
   - 0.3-0.5: Unsicher (Aktion unklar oder Sender fehlt)
   - 0.0-0.3: Sehr unsicher (zu vage, zu viele Unklarheiten)

5. Key Signals:
   - Liste die 3-5 wichtigsten Wörter/Phrasen, die zur Entscheidung führten
   - Beispiel: ["Werbung", "muten", "Zalando"]

**Ausgabe:**
- Gib immer ein vollständiges ParsedIntent-Objekt zurück
- reasoning muss auf Deutsch sein (2-3 Sätze)
- Bei Unsicherheit (confidence < 0.75): Detaillierte Begründung warum unsicher
"""


def build_user_prompt_nlp_intent(
    text: str,
    account_id: str
) -> str:
    """
    Build user prompt for NLP intent parsing.

    Args:
        text: User's natural language input
        account_id: Account ID (for context)

    Returns:
        Formatted user prompt
    """
    prompt_parts = []

    prompt_parts.append("=== EMAIL-PRÄFERENZ PARSING ===")
    prompt_parts.append(f"\n**Account:** {account_id}")
    prompt_parts.append(f"**User Input:** \"{text}\"")
    prompt_parts.append("\n--- 🎯 AUFGABE ---")
    prompt_parts.append("Analysiere den Text und identifiziere:")
    prompt_parts.append("1. Intent-Typ (whitelist, blacklist, mute, allow_only, etc.)")
    prompt_parts.append("2. Sender (Email, Domain oder Name)")
    prompt_parts.append("3. Kategorien (falls relevant)")
    prompt_parts.append("4. Vertrauensstufe (falls relevant)")
    prompt_parts.append("5. Confidence (0.0-1.0 - wie sicher bist du?)")
    prompt_parts.append("6. Reasoning (2-3 Sätze auf Deutsch)")
    prompt_parts.append("7. Key Signals (3-5 wichtigste Wörter/Phrasen)")
    prompt_parts.append("\nGib das Ergebnis als strukturiertes ParsedIntent-Objekt zurück.")

    return "\n".join(prompt_parts)


# ============================================================================
# INTENT PARSING FUNCTION (Tool for Agent)
# ============================================================================

async def parse_intent_with_llm(
    text: str,
    account_id: str
) -> Dict[str, Any]:
    """
    Parse natural language text into structured intent using LLM.

    Strategy:
    - Primary: Try Ollama first (local, free)
    - Fallback: Use OpenAI on any error (cloud, paid)
    - Structured output: Use Pydantic model for type safety

    Args:
        text: User's natural language input
        account_id: Account ID (for context)

    Returns:
        Dictionary with parsed intent:
        - intent_type: str
        - sender_email: Optional[str]
        - sender_domain: Optional[str]
        - sender_name: Optional[str]
        - trust_level: Optional[str]
        - categories: List[str]
        - preferred_primary_category: Optional[str]
        - confidence: float
        - reasoning: str
        - key_signals: List[str]
        - llm_provider_used: str (ollama or openai)
        - llm_response_time_ms: float
    """
    start_time = time.time()

    # Build prompts
    system_prompt = SYSTEM_PROMPT_NLP_INTENT
    user_prompt = build_user_prompt_nlp_intent(
        text=text,
        account_id=account_id
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Get LLM provider (Ollama-first + OpenAI fallback)
    provider = get_llm_provider()

    # Try parsing with structured output
    try:
        # Call LLM with Pydantic model for structured output
        response, provider_used = await provider.complete(
            messages=messages,
            response_format=ParsedIntent,
            temperature=0.1,  # Low temperature for consistent parsing
        )

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Extract parsed model from response
        # OpenAI returns ParsedChatCompletion[T], parsed model is in choices[0].message.parsed
        if hasattr(response, 'choices') and len(response.choices) > 0:
            parsed_model = response.choices[0].message.parsed
        else:
            # Fallback for direct Pydantic model (if provider changed)
            parsed_model = response

        # Convert Pydantic model to dict
        result = {
            'intent_type': parsed_model.intent_type,
            'sender_email': parsed_model.sender_email,
            'sender_domain': parsed_model.sender_domain,
            'sender_name': parsed_model.sender_name,
            'trust_level': parsed_model.trust_level,
            'categories': parsed_model.categories,
            'preferred_primary_category': parsed_model.preferred_primary_category,
            'confidence': parsed_model.confidence,
            'reasoning': parsed_model.reasoning,
            'key_signals': parsed_model.key_signals,
            'llm_provider_used': provider_used,  # ollama or openai
            'llm_response_time_ms': response_time_ms,
        }

        return result

    except Exception as e:
        # Fallback: Return unknown intent with low confidence
        response_time_ms = (time.time() - start_time) * 1000

        return {
            'intent_type': 'unknown',
            'sender_email': None,
            'sender_domain': None,
            'sender_name': None,
            'trust_level': None,
            'categories': [],
            'preferred_primary_category': None,
            'confidence': 0.10,
            'reasoning': f"NLP parsing failed: {str(e)[:100]}. Could not interpret user input.",
            'key_signals': ['parsing_error'],
            'llm_provider_used': 'error',
            'llm_response_time_ms': response_time_ms,
        }


# ============================================================================
# AGENT CREATION (Agent SDK Integration)
# ============================================================================

AGENT_INSTRUCTIONS_NLP_INTENT = """You are an intelligent NLP intent parser for email preference management.

Your job is to parse natural language input (in German) into structured preference rules.

**Intent Types:**
1. whitelist_sender - Add sender to whitelist (trusted)
2. blacklist_sender - Block sender (spam)
3. set_trust_level - Set trust level (trusted, neutral, suspicious, blocked)
4. mute_categories - Mute specific categories from sender
5. allow_only_categories - Allow only specific categories from sender
6. remove_from_whitelist - Remove from whitelist
7. remove_from_blacklist - Remove from blacklist
8. unknown - Intent not recognized

**Process:**
1. Call parse_intent_with_llm with user input text and account ID
2. LLM will parse the German text into structured ParsedIntent
3. Return the structured result with high confidence
4. Provide clear reasoning in German

**Examples:**
- Input: "Alle Werbemails von Zalando muten"
  → intent_type: mute_categories, sender_name: "Zalando", categories: ["werbung"]

- Input: "Amazon auf die Whitelist"
  → intent_type: whitelist_sender, sender_name: "Amazon", trust_level: "trusted"

- Input: "Keine Newsletter von LinkedIn"
  → intent_type: mute_categories, sender_name: "LinkedIn", categories: ["newsletter"]
"""


def create_nlp_intent_agent() -> Agent:
    """
    Create NLP intent parsing agent with Agent SDK.

    Returns:
        Agent instance configured for NLP intent parsing
    """
    agent = Agent(
        name="NLPIntentParser",
        instructions=AGENT_INSTRUCTIONS_NLP_INTENT,
        tools=[parse_intent_with_llm],
        model="gpt-4o-mini"  # Fast model for orchestration
    )

    return agent


# ============================================================================
# HIGH-LEVEL INTERFACE (Convenience)
# ============================================================================

class IntentParserResult(BaseModel):
    """
    Result of parsing an intent with suggested actions.
    """
    parsed_intent: ParsedIntent
    suggested_actions: List[str] = Field(
        description="Human-readable list of actions that will be performed"
    )
    requires_confirmation: bool = Field(
        description="Whether this intent requires user confirmation before executing"
    )


async def parse_nlp_intent(
    text: str,
    account_id: str
) -> IntentParserResult:
    """
    High-level interface for parsing NLP intent.

    Args:
        text: User's natural language input (German)
        account_id: Account ID

    Returns:
        IntentParserResult with parsed intent and suggested actions
    """
    # Parse with LLM
    result_dict = await parse_intent_with_llm(text, account_id)

    # Create ParsedIntent from dict
    parsed_intent = ParsedIntent(
        intent_type=result_dict['intent_type'],
        sender_email=result_dict['sender_email'],
        sender_domain=result_dict['sender_domain'],
        sender_name=result_dict['sender_name'],
        trust_level=result_dict['trust_level'],
        categories=result_dict['categories'],
        preferred_primary_category=result_dict['preferred_primary_category'],
        confidence=result_dict['confidence'],
        reasoning=result_dict['reasoning'],
        key_signals=result_dict['key_signals'],
        original_text=text  # Set original user input
    )

    # Generate suggested actions
    suggested_actions = _generate_suggested_actions(parsed_intent)

    # Determine if confirmation required
    requires_confirmation = _requires_confirmation(parsed_intent)

    return IntentParserResult(
        parsed_intent=parsed_intent,
        suggested_actions=suggested_actions,
        requires_confirmation=requires_confirmation
    )


def _generate_suggested_actions(intent: ParsedIntent) -> List[str]:
    """Generate human-readable list of actions from parsed intent."""
    actions = []

    # Identify sender
    sender = intent.sender_email or intent.sender_domain or intent.sender_name or "Sender"

    if intent.intent_type == 'whitelist_sender':
        actions.append(f"✅ {sender} auf die Whitelist setzen (Vertrauensstufe: trusted)")
        if intent.categories:
            actions.append(f"   → Nur Kategorien erlauben: {', '.join(intent.categories)}")

    elif intent.intent_type == 'blacklist_sender':
        actions.append(f"🚫 {sender} auf die Blacklist setzen (alle Emails → Spam)")

    elif intent.intent_type == 'set_trust_level':
        trust_emoji = {'trusted': '✅', 'neutral': '➖', 'suspicious': '⚠️', 'blocked': '🚫'}.get(intent.trust_level, '❓')
        actions.append(f"{trust_emoji} {sender} Vertrauensstufe: {intent.trust_level}")

    elif intent.intent_type == 'mute_categories':
        actions.append(f"🔇 Kategorien muten für {sender}: {', '.join(intent.categories)}")

    elif intent.intent_type == 'allow_only_categories':
        actions.append(f"✓ Nur Kategorien erlauben für {sender}: {', '.join(intent.categories)}")

    elif intent.intent_type == 'remove_from_whitelist':
        actions.append(f"↩️ {sender} von Whitelist entfernen (Vertrauensstufe → neutral)")

    elif intent.intent_type == 'remove_from_blacklist':
        actions.append(f"↩️ {sender} von Blacklist entfernen (entsperren)")

    else:
        actions.append(f"❓ Intent nicht erkannt")

    return actions


def _requires_confirmation(intent: ParsedIntent) -> bool:
    """Determine if intent requires user confirmation."""
    # Blacklist always requires confirmation
    if intent.intent_type == 'blacklist_sender':
        return True

    # Low confidence requires confirmation
    if intent.confidence < 0.75:
        return True

    # Unknown intents require confirmation
    if intent.intent_type == 'unknown':
        return True

    return False
