"""
Unified Three-Layer Email Importance Classifier

Orchestrates the three-layer classification system:
1. Rule Layer: Fast pattern matching (no LLM)
2. History Layer: User behavior learning (no LLM)
3. LLM Layer: Deep semantic analysis (Ollama-first + OpenAI fallback)

High-confidence results from earlier layers skip subsequent layers for
efficiency. Only emails that can't be classified with high confidence
by rules or history proceed to the LLM layer.

Usage:
    classifier = UnifiedClassifier()
    result = await classifier.classify(email)
"""

import time
from typing import Optional
from sqlalchemy.orm import Session

from agent_platform.classification.models import (
    EmailToClassify,
    ClassificationResult,
    ClassificationThresholds,
)
from agent_platform.classification.importance_rules import RuleLayer
from agent_platform.classification.importance_history import HistoryLayer
from agent_platform.classification.importance_llm import LLMLayer
from agent_platform.core.config import Config
from agent_platform.db.database import get_db


class UnifiedClassifier:
    """
    Unified three-layer email importance classifier.

    Orchestrates Rule → History → LLM layers with automatic
    short-circuiting on high-confidence results.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        thresholds: Optional[ClassificationThresholds] = None
    ):
        """
        Initialize unified classifier.

        Args:
            db: Optional database session (will create one if not provided)
            thresholds: Optional custom thresholds (uses config defaults if not provided)
        """
        # Database session
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        # Thresholds
        self.thresholds = thresholds or ClassificationThresholds(
            high_confidence_threshold=Config.IMPORTANCE_CONFIDENCE_HIGH_THRESHOLD,
            medium_confidence_threshold=Config.IMPORTANCE_CONFIDENCE_MEDIUM_THRESHOLD,
            low_importance_threshold=Config.IMPORTANCE_SCORE_LOW_THRESHOLD,
            high_importance_threshold=Config.IMPORTANCE_SCORE_HIGH_THRESHOLD,
        )

        # Initialize layers
        self.rule_layer = RuleLayer()
        self.history_layer = HistoryLayer(db=self.db)
        self.llm_layer = LLMLayer()

        # Statistics
        self.stats = {
            'total_classifications': 0,
            'rule_layer_sufficient': 0,
            'history_layer_sufficient': 0,
            'llm_layer_required': 0,
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0,
        }

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN CLASSIFICATION METHOD
    # ========================================================================

    async def classify(
        self,
        email: EmailToClassify,
        force_llm: bool = False
    ) -> ClassificationResult:
        """
        Classify email using three-layer system.

        Layers are executed in sequence with early stopping:
        1. Rule Layer (fast, no LLM)
        2. History Layer (fast, no LLM)
        3. LLM Layer (slow, Ollama-first + OpenAI fallback)

        Args:
            email: Email to classify
            force_llm: If True, skip Rule and History layers and go straight to LLM

        Returns:
            ClassificationResult with final classification and metadata
        """
        start_time = time.time()
        self.stats['total_classifications'] += 1

        # ====================================================================
        # LAYER 1: RULE LAYER (Pattern Matching)
        # ====================================================================

        if not force_llm:
            rule_result = self.rule_layer.classify(email)

            # Check if Rule Layer has high confidence
            if rule_result.confidence >= self.thresholds.high_confidence_threshold:
                # High confidence from rules - we're done!
                self.stats['rule_layer_sufficient'] += 1
                self.stats['high_confidence_count'] += 1

                processing_time_ms = (time.time() - start_time) * 1000

                return ClassificationResult(
                    importance=rule_result.importance,
                    confidence=rule_result.confidence,
                    category=rule_result.category,
                    reasoning=f"[Rule Layer] {rule_result.reasoning}",
                    layer_used="rules",
                    llm_provider_used="rules_only",
                    processing_time_ms=processing_time_ms,
                )

            # Medium/low confidence from rules - proceed to History Layer
            print(f"  ⏭️  Rule Layer confidence {rule_result.confidence:.2f} < {self.thresholds.high_confidence_threshold:.2f} → History Layer")

        else:
            rule_result = None
            print(f"  ⚡ Forcing LLM Layer (skipping Rule + History)")

        # ====================================================================
        # LAYER 2: HISTORY LAYER (User Behavior Learning)
        # ====================================================================

        if not force_llm:
            history_result = self.history_layer.classify(email)

            # Check if History Layer has high confidence
            if history_result.confidence >= self.thresholds.high_confidence_threshold:
                # High confidence from history - we're done!
                self.stats['history_layer_sufficient'] += 1
                self.stats['high_confidence_count'] += 1

                processing_time_ms = (time.time() - start_time) * 1000

                return ClassificationResult(
                    importance=history_result.importance,
                    confidence=history_result.confidence,
                    category=history_result.category,
                    reasoning=f"[History Layer] {history_result.reasoning}",
                    layer_used="history",
                    llm_provider_used="history_only",
                    processing_time_ms=processing_time_ms,
                )

            # Medium/low confidence from history - proceed to LLM Layer
            print(f"  ⏭️  History Layer confidence {history_result.confidence:.2f} < {self.thresholds.high_confidence_threshold:.2f} → LLM Layer")

        else:
            history_result = None

        # ====================================================================
        # LAYER 3: LLM LAYER (Deep Semantic Analysis)
        # ====================================================================

        print(f"  🤖 Calling LLM Layer (Ollama-first + OpenAI fallback)...")

        # Call LLM with context from previous layers
        llm_result = await self.llm_layer.classify(
            email=email,
            rule_result=rule_result,
            history_result=history_result,
        )

        self.stats['llm_layer_required'] += 1

        # Update confidence statistics
        if llm_result.confidence >= self.thresholds.high_confidence_threshold:
            self.stats['high_confidence_count'] += 1
        elif llm_result.confidence >= self.thresholds.medium_confidence_threshold:
            self.stats['medium_confidence_count'] += 1
        else:
            self.stats['low_confidence_count'] += 1

        processing_time_ms = (time.time() - start_time) * 1000

        # Build final result
        reasoning_parts = [f"[LLM Layer - {llm_result.llm_provider_used}]"]

        # Add context from previous layers if available
        if rule_result and rule_result.matched_rules:
            reasoning_parts.append(f"Rules matched: {', '.join(rule_result.matched_rules[:2])}")

        if history_result and history_result.sender_preference_found:
            reasoning_parts.append(f"Sender history: {history_result.total_historical_emails} emails")

        reasoning_parts.append(llm_result.reasoning)

        return ClassificationResult(
            importance=llm_result.importance,
            confidence=llm_result.confidence,
            category=llm_result.category,
            reasoning=" | ".join(reasoning_parts),
            layer_used="llm",
            llm_provider_used=llm_result.llm_provider_used,
            processing_time_ms=processing_time_ms,
        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self) -> dict:
        """Get classification statistics."""
        total = self.stats['total_classifications']

        if total == 0:
            return {**self.stats, 'rule_layer_percentage': 0.0, 'history_layer_percentage': 0.0, 'llm_layer_percentage': 0.0}

        return {
            **self.stats,
            'rule_layer_percentage': self.stats['rule_layer_sufficient'] / total * 100,
            'history_layer_percentage': self.stats['history_layer_sufficient'] / total * 100,
            'llm_layer_percentage': self.stats['llm_layer_required'] / total * 100,
        }

    def print_stats(self):
        """Print classification statistics."""
        stats = self.get_stats()

        print("\n" + "=" * 70)
        print("UNIFIED CLASSIFIER STATISTICS")
        print("=" * 70)
        print(f"Total Classifications: {stats['total_classifications']}")
        print(f"\nLayer Distribution:")
        print(f"  Rule Layer (fast):    {stats['rule_layer_sufficient']:>3} ({stats['rule_layer_percentage']:>5.1f}%)")
        print(f"  History Layer (fast): {stats['history_layer_sufficient']:>3} ({stats['history_layer_percentage']:>5.1f}%)")
        print(f"  LLM Layer (slow):     {stats['llm_layer_required']:>3} ({stats['llm_layer_percentage']:>5.1f}%)")
        print(f"\nConfidence Distribution:")
        print(f"  High (≥{self.thresholds.high_confidence_threshold:.2f}):   {stats['high_confidence_count']}")
        print(f"  Medium (≥{self.thresholds.medium_confidence_threshold:.2f}): {stats['medium_confidence_count']}")
        print(f"  Low (<{self.thresholds.medium_confidence_threshold:.2f}):    {stats['low_confidence_count']}")
        print("=" * 70 + "\n")

        # Also print LLM provider stats if LLM was used
        if stats['llm_layer_required'] > 0:
            print("\nLLM Provider Statistics:")
            self.llm_layer.print_provider_stats()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_classifications': 0,
            'rule_layer_sufficient': 0,
            'history_layer_sufficient': 0,
            'llm_layer_required': 0,
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0,
        }

    # ========================================================================
    # DECISION HELPERS
    # ========================================================================

    def should_auto_action(self, result: ClassificationResult) -> bool:
        """
        Determine if this classification is confident enough for automatic action.

        Returns True if:
        - Confidence >= high_confidence_threshold (e.g., 0.85)
        """
        return result.confidence >= self.thresholds.high_confidence_threshold

    def should_add_to_review_queue(self, result: ClassificationResult) -> bool:
        """
        Determine if this classification should be added to review queue.

        Returns True if:
        - Confidence >= medium_confidence_threshold (e.g., 0.6)
        - Confidence < high_confidence_threshold (e.g., 0.85)
        """
        return (
            result.confidence >= self.thresholds.medium_confidence_threshold
            and result.confidence < self.thresholds.high_confidence_threshold
        )

    def should_move_to_low_priority(self, result: ClassificationResult) -> bool:
        """
        Determine if email should be moved to Low-Priority folder.

        Returns True if:
        - High confidence (>= 0.85)
        - Low importance (< 0.4)
        """
        return (
            result.confidence >= self.thresholds.high_confidence_threshold
            and result.importance < self.thresholds.low_importance_threshold
        )

    def is_auto_reply_eligible(self, result: ClassificationResult) -> bool:
        """
        Determine if email is eligible for auto-reply.

        Returns True if:
        - High confidence (>= 0.85)
        - High importance (> 0.7)
        - Category is "action_required" or "wichtig"
        """
        return (
            result.confidence >= self.thresholds.high_confidence_threshold
            and result.importance > self.thresholds.high_importance_threshold
            and result.category in ["action_required", "wichtig"]
        )
