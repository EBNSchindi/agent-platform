"""
LLM-Based Classification Agent (OpenAI Agents SDK)

PRESERVATION PRINCIPLE:
This agent WRAPS the existing llm_layer.py logic WITHOUT changing it.
Ollama-first + OpenAI fallback strategy and prompt structure are IDENTICAL.

Extract → Wrap → Orchestrate pattern:
1. EXTRACTED functions from importance_llm.py (AS-IS, no changes)
2. WRAPPED as Agent with structured output
3. Uses SAME prompt templates and provider fallback logic

LLM Strategy:
- Primary: Ollama (local) ← SAME as original
- Fallback: OpenAI (cloud) ← SAME fallback logic
- Structured outputs: Pydantic models ← SAME as original
- Context integration: Rule + History results ← SAME context passing
"""

import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from agents import Agent

from agent_platform.classification.models import (
    EmailToClassify,
    LLMLayerResult,
    ImportanceCategory,
)
from agent_platform.llm.providers import get_llm_provider


# ============================================================================
# STRUCTURED OUTPUT MODEL (From importance_llm.py - UNCHANGED)
# ============================================================================

class LLMClassificationOutput(BaseModel):
    """
    EXTRACTED FROM: importance_llm.py

    PRESERVATION: Field definitions are IDENTICAL to original.

    Structured output from LLM classification.

    This model is used for type-safe, validated LLM responses.
    """
    # ← SAME fields as importance_llm.py
    category: ImportanceCategory = Field(
        ...,
        description="The importance category for this email"
    )

    importance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (low priority) to 1.0 (high priority)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this classification from 0.0 (uncertain) to 1.0 (certain)"
    )

    reasoning: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Brief explanation (1-2 sentences) of why this classification was chosen"
    )

    key_signals: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Key signals that influenced the classification (max 5)"
    )


# ============================================================================
# EXTRACTED PROMPTS (From importance_llm.py - UNCHANGED)
# ============================================================================

# ← SAME system prompt as importance_llm.py
SYSTEM_PROMPT = """Du bist ein intelligenter Email-Klassifizierungs-Assistent.

Deine Aufgabe ist es, Emails in Wichtigkeits-Kategorien einzuordnen basierend auf:
- Inhalt der Email (Subject + Body)
- Kontext aus vorherigen Analysen
- Sender-Historie (falls verfügbar)

KATEGORIEN:
1. wichtig - Wichtige Emails die Aufmerksamkeit erfordern
2. action_required - Emails die eine Antwort/Aktion benötigen
3. nice_to_know - Informative Emails ohne direkte Handlungsaufforderung
4. newsletter - Newsletter, Marketing-Emails
5. system_notifications - Automatische System-Benachrichtigungen
6. spam - Unerwünschte/Spam-Emails

WICHTIGKEIT (0.0 - 1.0):
- 0.9-1.0: Sehr wichtig, dringend
- 0.7-0.9: Wichtig
- 0.5-0.7: Mittlere Priorität
- 0.3-0.5: Niedrige Priorität
- 0.0-0.3: Sehr niedrige Priorität

CONFIDENCE (0.0 - 1.0):
- 0.9-1.0: Sehr sicher
- 0.7-0.9: Sicher
- 0.5-0.7: Mittlere Sicherheit
- 0.3-0.5: Unsicher
- 0.0-0.3: Sehr unsicher

Analysiere die Email sorgfältig und gib eine präzise Klassifizierung zurück."""


# ============================================================================
# EXTRACTED FUNCTIONS (From importance_llm.py - LOGIC UNCHANGED)
# ============================================================================

def build_user_prompt(
    email_id: str,
    subject: str,
    body: str,
    sender: str,
    rule_context: Optional[Dict[str, Any]] = None,
    history_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    EXTRACTED FROM: importance_llm.py LLMLayer._build_user_prompt()

    PRESERVATION: Prompt structure and context integration are IDENTICAL to original.

    Build user prompt with email content and context from previous layers.

    Args:
        email_id: Email ID
        subject: Email subject
        body: Email body
        sender: Sender email address
        rule_context: Optional context from Rule Layer
        history_context: Optional context from History Layer

    Returns:
        Formatted user prompt string
    """
    # ← SAME prompt structure as importance_llm.py
    prompt_parts = []

    # Email content
    prompt_parts.append("EMAIL ZU KLASSIFIZIEREN:")
    prompt_parts.append(f"Von: {sender}")
    prompt_parts.append(f"Betreff: {subject}")
    prompt_parts.append(f"\nNachricht:\n{body[:1000]}")  # ← SAME body limit (1000 chars)

    # Context from Rule Layer
    if rule_context:
        prompt_parts.append("\n--- KONTEXT AUS REGEL-ANALYSE ---")
        if rule_context.get('matched_rules'):
            prompt_parts.append(f"Erkannte Muster: {', '.join(rule_context['matched_rules'])}")

        if rule_context.get('spam_signals'):
            prompt_parts.append(f"Spam-Signale: {', '.join(rule_context['spam_signals'][:3])}")

        if rule_context.get('newsletter_signals'):
            prompt_parts.append(f"Newsletter-Signale: {', '.join(rule_context['newsletter_signals'][:3])}")

        if rule_context.get('confidence', 0) >= 0.5:
            prompt_parts.append(f"Regel-Vorschlag: {rule_context['category']} (Confidence: {rule_context['confidence']:.2f})")

    # Context from History Layer
    if history_context:
        if history_context.get('sender_preference_found'):
            prompt_parts.append("\n--- KONTEXT AUS SENDER-HISTORIE ---")
            prompt_parts.append(f"Sender: {history_context['sender_email']}")
            prompt_parts.append(f"Historische Emails: {history_context['total_historical_emails']}")

            if history_context.get('historical_reply_rate') is not None:
                reply_rate = history_context['historical_reply_rate']
                prompt_parts.append(f"Antwort-Rate: {reply_rate:.0%}")

            if history_context.get('confidence', 0) >= 0.5:
                prompt_parts.append(f"Historie-Vorschlag: {history_context['category']} (Confidence: {history_context['confidence']:.2f})")

        elif history_context.get('domain_preference_found'):
            prompt_parts.append("\n--- KONTEXT AUS DOMAIN-HISTORIE ---")
            prompt_parts.append(f"Domain: {history_context['sender_domain']}")
            prompt_parts.append(f"Historische Emails von dieser Domain: {history_context['total_historical_emails']}")

            if history_context.get('historical_reply_rate') is not None:
                reply_rate = history_context['historical_reply_rate']
                prompt_parts.append(f"Antwort-Rate: {reply_rate:.0%}")

    # Instructions
    prompt_parts.append("\n--- AUFGABE ---")
    prompt_parts.append("Klassifiziere diese Email basierend auf dem Inhalt und den bereitgestellten Kontext-Informationen.")
    prompt_parts.append("Gib eine strukturierte Antwort mit Kategorie, Wichtigkeit, Confidence und Begründung zurück.")

    return "\n".join(prompt_parts)


async def classify_email_with_llm(
    email_id: str,
    subject: str,
    body: str,
    sender: str,
    rule_context: Optional[Dict[str, Any]] = None,
    history_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    WRAPPER FUNCTION: Classify email using LLM with Ollama-first + OpenAI fallback.

    PRESERVATION: Provider fallback strategy is IDENTICAL to importance_llm.py.
    - Primary: Try Ollama first
    - Fallback: Use OpenAI on any error
    - Structured output: Use Pydantic model for type safety

    Args:
        email_id: Email ID
        subject: Email subject
        body: Email body
        sender: Sender email address
        rule_context: Optional context from Rule Layer
        history_context: Optional context from History Layer

    Returns:
        Dictionary with LLMLayerResult fields
    """
    start_time = time.time()

    # Build prompts (← SAME as importance_llm.py)
    system_prompt = SYSTEM_PROMPT
    user_prompt = build_user_prompt(
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

    # Get LLM provider (← SAME provider as importance_llm.py)
    provider = get_llm_provider()

    try:
        # Call LLM with structured output (← SAME fallback logic as original)
        # This automatically tries Ollama first, then falls back to OpenAI
        response, provider_used = await provider.complete(
            messages=messages,
            response_format=LLMClassificationOutput,
        )

        # Extract structured output
        classification = response.choices[0].message.parsed

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Determine model used
        if provider_used == "ollama":
            model_used = provider.ollama_model
        else:  # openai_fallback or openai
            model_used = provider.openai_model

        # Build result (← SAME format as importance_llm.py)
        return {
            'importance': classification.importance_score,
            'confidence': classification.confidence,
            'category': classification.category,
            'reasoning': classification.reasoning,
            'llm_provider_used': provider_used if provider_used != "openai" else "openai_fallback",
            'llm_model_used': model_used,
            'llm_response_time_ms': processing_time_ms,
            'subject_analyzed': True,
            'body_analyzed': True,
            'sender_context_used': history_context is not None,
        }

    except Exception as e:
        # Both providers failed - return error
        processing_time_ms = (time.time() - start_time) * 1000

        raise RuntimeError(
            f"LLM classification failed after trying both providers: {e}"
        )


# ============================================================================
# AGENT INSTRUCTIONS
# ============================================================================

LLM_AGENT_INSTRUCTIONS = """You are a deep semantic email classification expert using Large Language Models.

Your job is to analyze emails that couldn't be classified with high confidence by Rule or History layers.

**Tools Available:**
- classify_email_with_llm: Deep semantic analysis using Ollama (primary) or OpenAI (fallback)

**Classification Process:**
1. Call classify_email_with_llm with email data and context
2. The tool will:
   - Try Ollama (local, fast, free) first
   - Automatically fall back to OpenAI (cloud, reliable) on any error
   - Return structured classification result
3. Return the result (contains category, confidence, importance, reasoning)

**Context Integration:**
- You receive context from Rule Layer (pattern matches, signals)
- You receive context from History Layer (sender/domain behavior patterns)
- Use this context to improve classification accuracy

**Confidence Levels:**
- 0.85+: High confidence (clear semantic indicators)
- 0.6-0.85: Medium confidence (some uncertainty)
- <0.6: Low confidence (ambiguous content)

**Provider Strategy:**
- Ollama: Local model (gptoss20b), fast, free, private
- OpenAI: Cloud model (gpt-4o), fallback on Ollama errors

**Important:**
- This is the FINAL classification layer
- You provide semantic understanding beyond pattern matching
- Your confidence determines if email goes to review queue or gets auto-actioned
"""


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_llm_agent() -> Agent:
    """
    Create LLM-based classification agent with OpenAI Agents SDK.

    PRESERVATION: This agent wraps the SAME logic from importance_llm.py
    with the Agent SDK interface. Ollama-first + OpenAI fallback strategy,
    prompt templates, and structured outputs are IDENTICAL to the original.

    Returns:
        Agent instance configured for LLM-based classification
    """
    # Note: We use gpt-4o for the agent orchestration layer
    # The actual classification LLM (Ollama/OpenAI) is called via tools
    agent = Agent(
        name="LLMClassifier",
        instructions=LLM_AGENT_INSTRUCTIONS,
        tools=[classify_email_with_llm],
        model="gpt-4o"  # Agent orchestration (tool calling)
    )

    return agent
