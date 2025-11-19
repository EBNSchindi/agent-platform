"""
LLM-Based Importance Classification Layer

Deep semantic analysis using Large Language Models with automatic fallback:
- Primary: Ollama (local gptoss20b) - fast, free, private
- Fallback: OpenAI (cloud gpt-4o) - reliable, high quality

This layer handles emails that couldn't be classified with high confidence
by the Rule Layer or History Layer. Uses structured outputs (Pydantic) for
type-safe LLM responses.

Ollama-First Strategy:
1. Try Ollama (gptoss20b) via localhost:11434
2. On any error → Automatic fallback to OpenAI (gpt-4o)
3. Return classification + metadata (which provider was used)
"""

import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agent_platform.classification.models import (
    EmailToClassify,
    LLMLayerResult,
    ImportanceCategory,
    RuleLayerResult,
    HistoryLayerResult,
)
from agent_platform.llm.providers import get_llm_provider


# ============================================================================
# PYDANTIC MODEL FOR STRUCTURED LLM OUTPUT
# ============================================================================

class LLMClassificationOutput(BaseModel):
    """
    Structured output from LLM classification.

    This model is passed to the LLM via response_format to ensure
    type-safe, validated responses.
    """
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
# LLM CLASSIFIER
# ============================================================================

class LLMLayer:
    """
    LLM-based classification layer with Ollama-first + OpenAI fallback.

    Uses the UnifiedLLMProvider from Phase 1 to automatically handle
    Ollama → OpenAI fallback on any error.
    """

    def __init__(self):
        """Initialize LLM layer with provider."""
        self.provider = get_llm_provider()

    # ========================================================================
    # MAIN CLASSIFICATION METHOD
    # ========================================================================

    async def classify(
        self,
        email: EmailToClassify,
        rule_result: Optional[RuleLayerResult] = None,
        history_result: Optional[HistoryLayerResult] = None,
    ) -> LLMLayerResult:
        """
        Classify email using LLM with Ollama-first + OpenAI fallback.

        Args:
            email: Email to classify
            rule_result: Optional result from Rule Layer (for context)
            history_result: Optional result from History Layer (for context)

        Returns:
            LLMLayerResult with classification and provider metadata
        """
        start_time = time.time()

        # Build prompt with context from previous layers
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(email, rule_result, history_result)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call LLM with structured output (Ollama-first with automatic fallback)
        try:
            response, provider_used = await self.provider.complete(
                messages=messages,
                response_format=LLMClassificationOutput,
            )

            # Extract structured output
            classification = response.choices[0].message.parsed

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Determine model used
            if provider_used == "ollama":
                model_used = self.provider.ollama_model
            else:  # openai_fallback or openai
                model_used = self.provider.openai_model

            # Build result
            return LLMLayerResult(
                importance=classification.importance_score,
                confidence=classification.confidence,
                category=classification.category,
                reasoning=classification.reasoning,
                llm_provider_used=provider_used if provider_used != "openai" else "openai_fallback",
                llm_model_used=model_used,
                llm_response_time_ms=processing_time_ms,
                subject_analyzed=True,
                body_analyzed=True,
                sender_context_used=history_result is not None,
            )

        except Exception as e:
            # Both providers failed - return error result
            processing_time_ms = (time.time() - start_time) * 1000

            raise RuntimeError(
                f"LLM classification failed after trying both providers: {e}"
            )

    # ========================================================================
    # PROMPT BUILDING
    # ========================================================================

    def _build_system_prompt(self) -> str:
        """
        Build system prompt for LLM classification.

        Defines the task, categories, and output format.
        """
        return """Du bist ein intelligenter Email-Klassifizierungs-Assistent.

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

    def _build_user_prompt(
        self,
        email: EmailToClassify,
        rule_result: Optional[RuleLayerResult],
        history_result: Optional[HistoryLayerResult],
    ) -> str:
        """
        Build user prompt with email content and context.

        Includes results from previous layers to improve accuracy.
        """
        prompt_parts = []

        # Email content
        prompt_parts.append("EMAIL ZU KLASSIFIZIEREN:")
        prompt_parts.append(f"Von: {email.sender}")
        prompt_parts.append(f"Betreff: {email.subject}")
        prompt_parts.append(f"\nNachricht:\n{email.body[:1000]}")  # Limit body length

        # Context from Rule Layer
        if rule_result:
            prompt_parts.append("\n--- KONTEXT AUS REGEL-ANALYSE ---")
            prompt_parts.append(f"Erkannte Muster: {', '.join(rule_result.matched_rules)}")

            if rule_result.spam_signals:
                prompt_parts.append(f"Spam-Signale: {', '.join(rule_result.spam_signals[:3])}")

            if rule_result.newsletter_signals:
                prompt_parts.append(f"Newsletter-Signale: {', '.join(rule_result.newsletter_signals[:3])}")

            if rule_result.confidence >= 0.5:
                prompt_parts.append(f"Regel-Vorschlag: {rule_result.category} (Confidence: {rule_result.confidence:.2f})")

        # Context from History Layer
        if history_result and history_result.sender_preference_found:
            prompt_parts.append("\n--- KONTEXT AUS SENDER-HISTORIE ---")
            prompt_parts.append(f"Sender: {history_result.sender_email}")
            prompt_parts.append(f"Historische Emails: {history_result.total_historical_emails}")

            if history_result.historical_reply_rate is not None:
                prompt_parts.append(f"Antwort-Rate: {history_result.historical_reply_rate:.0%}")

            if history_result.confidence >= 0.5:
                prompt_parts.append(f"Historie-Vorschlag: {history_result.category} (Confidence: {history_result.confidence:.2f})")

        elif history_result and history_result.domain_preference_found:
            prompt_parts.append("\n--- KONTEXT AUS DOMAIN-HISTORIE ---")
            prompt_parts.append(f"Domain: {history_result.sender_domain}")
            prompt_parts.append(f"Historische Emails von dieser Domain: {history_result.total_historical_emails}")

            if history_result.historical_reply_rate is not None:
                prompt_parts.append(f"Antwort-Rate: {history_result.historical_reply_rate:.0%}")

        # Instructions
        prompt_parts.append("\n--- AUFGABE ---")
        prompt_parts.append("Klassifiziere diese Email basierend auf dem Inhalt und den bereitgestellten Kontext-Informationen.")
        prompt_parts.append("Gib eine strukturierte Antwort mit Kategorie, Wichtigkeit, Confidence und Begründung zurück.")

        return "\n".join(prompt_parts)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics from the LLM provider."""
        return self.provider.get_stats()

    def print_provider_stats(self):
        """Print LLM provider statistics."""
        self.provider.print_stats()
