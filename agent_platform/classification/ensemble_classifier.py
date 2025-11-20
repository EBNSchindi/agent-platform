"""
Ensemble Email Importance Classifier

3-Layer Ensemble System where ALL layers run in parallel and results are
combined via weighted scoring. Maximum accuracy and confidence through
multi-layer consensus.

Architecture Shift from Early-Stopping to Ensemble Scoring:

BEFORE (Early-Stopping):
    Email → Rule Layer (0.65) → STOP if confident
    Email → History Layer (0.80) → STOP if confident
    Email → LLM Layer (0.92) → Final result

AFTER (Ensemble Scoring):
    Email → All 3 Layers Parallel (asyncio.gather)
           ├─ Rule Layer → Score
           ├─ History Layer → Score
           └─ LLM Layer → Score
                 ↓
           Weighted Combination
                 ↓
           Final Classification

Key Features:
- Parallel layer execution for maximum information
- Configurable weights (HITL adjustable)
- Agreement-based confidence boosting
- Disagreement detection and logging
- Bootstrap mode support (different weights for learning phase)
- Optional Smart LLM skip for performance optimization

Usage:
    classifier = EnsembleClassifier()
    result = await classifier.classify(email)
"""

import time
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from agent_platform.classification.models import (
    EmailToClassify,
    EnsembleClassification,
    LayerScore,
    ScoringWeights,
    DisagreementInfo,
    ImportanceCategory,
)
from agent_platform.classification.importance_rules import RuleLayer
from agent_platform.classification.importance_history import HistoryLayer
from agent_platform.classification.importance_llm import LLMLayer
from agent_platform.core.config import Config
from agent_platform.db.database import get_db
from agent_platform.events import log_event, EventType
from agent_platform.monitoring import SystemLogger


class EnsembleClassifier:
    """
    Ensemble classifier that runs all 3 layers in parallel and combines results.

    Uses weighted scoring to combine Rule, History, and LLM layer outputs.
    Automatically detects agreement/disagreement and adjusts confidence accordingly.
    """

    # Bootstrap phase duration (2 weeks)
    BOOTSTRAP_DURATION_DAYS = 14

    def __init__(
        self,
        db: Optional[Session] = None,
        weights: Optional[ScoringWeights] = None,
        smart_llm_skip: bool = False,
    ):
        """
        Initialize ensemble classifier.

        Args:
            db: Optional database session (will create one if not provided)
            weights: Optional custom weights (uses defaults if not provided)
            smart_llm_skip: If True, skip LLM when Rule+History agree with high confidence
        """
        # Database session
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        # Scoring weights
        self.weights = weights or ScoringWeights()

        # Smart LLM skip optimization
        self.smart_llm_skip = smart_llm_skip

        # Initialize layers
        self.rule_layer = RuleLayer()
        self.history_layer = HistoryLayer(db=self.db)
        self.llm_layer = LLMLayer()

        # Statistics
        self.stats = {
            'total_classifications': 0,
            'all_layers_agree': 0,
            'partial_agreement': 0,
            'no_agreement': 0,
            'llm_skipped': 0,
            'llm_used': 0,
            'bootstrap_mode_count': 0,
            'production_mode_count': 0,
        }

        # Logger
        self.logger = SystemLogger(component="ensemble_classifier")

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
    ) -> EnsembleClassification:
        """
        Classify email using ensemble of all 3 layers.

        All layers run in parallel (or Rule+History run first for smart LLM skip).
        Results are combined via weighted scoring with agreement-based confidence
        adjustment.

        Args:
            email: Email to classify
            force_llm: If True, always use LLM (ignore smart_llm_skip)

        Returns:
            EnsembleClassification with combined results from all layers
        """
        start_time = time.time()
        self.stats['total_classifications'] += 1

        # Check if we're in bootstrap mode
        is_bootstrap = self._is_bootstrap_phase(email.account_id)

        if is_bootstrap:
            self.stats['bootstrap_mode_count'] += 1
            self.logger.info(f"Bootstrap mode active for account {email.account_id}")
        else:
            self.stats['production_mode_count'] += 1

        # Get appropriate weights
        rule_weight, history_weight, llm_weight = self.weights.get_weights(is_bootstrap)

        # ====================================================================
        # STEP 1: RUN LAYERS (Parallel or Sequential based on smart_llm_skip)
        # ====================================================================

        llm_was_used = True  # Track if LLM was actually called

        if self.smart_llm_skip and not force_llm:
            # Smart LLM Skip: Run Rule + History first, then decide on LLM
            rule_score, history_score = await self._run_rule_and_history_layers(email)

            # Check if we should skip LLM
            if self._should_skip_llm(rule_score, history_score):
                llm_score = None
                llm_was_used = False
                self.stats['llm_skipped'] += 1
                self.logger.info(f"LLM skipped - Rule+History agree with high confidence")
            else:
                llm_score = await self._run_llm_layer(email)
                self.stats['llm_used'] += 1

        else:
            # Default: Run all 3 layers in parallel
            rule_score, history_score, llm_score = await self._run_all_layers_parallel(email)
            self.stats['llm_used'] += 1

        # ====================================================================
        # STEP 2: WEIGHTED COMBINATION
        # ====================================================================

        # Calculate weighted importance
        if llm_was_used and llm_score:
            final_importance = (
                rule_score.importance * rule_weight +
                history_score.importance * history_weight +
                llm_score.importance * llm_weight
            )

            # Calculate weighted confidence (before agreement adjustment)
            base_confidence = (
                rule_score.confidence * rule_weight +
                history_score.confidence * history_weight +
                llm_score.confidence * llm_weight
            )
        else:
            # LLM was skipped - only use Rule + History
            # Renormalize weights (Rule + History sum to 1.0)
            total_weight = rule_weight + history_weight
            normalized_rule = rule_weight / total_weight
            normalized_history = history_weight / total_weight

            final_importance = (
                rule_score.importance * normalized_rule +
                history_score.importance * normalized_history
            )

            base_confidence = (
                rule_score.confidence * normalized_rule +
                history_score.confidence * normalized_history
            )

        # ====================================================================
        # STEP 3: AGREEMENT DETECTION & CONFIDENCE ADJUSTMENT
        # ====================================================================

        agreement_result = self._check_agreement(rule_score, history_score, llm_score)

        layers_agree = agreement_result['all_agree']
        partial_agreement = agreement_result['partial_agree']
        agreement_score = agreement_result['agreement_score']
        agreement_count = agreement_result['agreement_count']

        # Confidence boost/penalty based on agreement
        if layers_agree:
            confidence_boost = 0.20  # +20% for complete agreement
            self.stats['all_layers_agree'] += 1
        elif partial_agreement:
            confidence_boost = 0.10  # +10% for partial agreement
            self.stats['partial_agreement'] += 1
        else:
            confidence_boost = -0.20  # -20% penalty for disagreement
            self.stats['no_agreement'] += 1

        # Apply boost and clamp to [0.0, 1.0]
        final_confidence = max(0.0, min(1.0, base_confidence + confidence_boost))

        # ====================================================================
        # STEP 4: FINAL CATEGORY SELECTION
        # ====================================================================

        # Use majority vote or weighted preference
        final_category = self._select_final_category(
            rule_score,
            history_score,
            llm_score,
            rule_weight,
            history_weight,
            llm_weight
        )

        # ====================================================================
        # STEP 5: DISAGREEMENT DETECTION & LOGGING
        # ====================================================================

        disagreement = None

        if not layers_agree and llm_was_used and llm_score:
            # Calculate confidence variance (measure of uncertainty)
            confidences = [rule_score.confidence, history_score.confidence, llm_score.confidence]
            mean_conf = sum(confidences) / len(confidences)
            variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)

            # Create disagreement info
            disagreement = DisagreementInfo(
                email_id=email.email_id,
                account_id=email.account_id,
                rule_category=rule_score.category,
                history_category=history_score.category,
                llm_category=llm_score.category,
                final_category=final_category,
                layers_agree=layers_agree,
                partial_agreement=partial_agreement,
                agreement_count=agreement_count,
                confidence_variance=variance,
                needs_user_review=(not partial_agreement and variance > 0.1),  # High variance
            )

            # Log disagreement event
            if disagreement.needs_user_review:
                self._log_disagreement_event(email, disagreement)

        # ====================================================================
        # STEP 6: BUILD COMBINED REASONING
        # ====================================================================

        reasoning_parts = []

        # Add layer reasoning
        reasoning_parts.append(f"[Rule Layer] {rule_score.reasoning}")
        reasoning_parts.append(f"[History Layer] {history_score.reasoning}")

        if llm_score:
            reasoning_parts.append(f"[LLM Layer] {llm_score.reasoning}")

        # Add agreement info
        if layers_agree:
            reasoning_parts.append("✅ All layers agree - high confidence")
        elif partial_agreement:
            reasoning_parts.append("⚠️ Partial agreement - medium confidence")
        else:
            reasoning_parts.append("❌ Layers disagree - needs review")

        combined_reasoning = " | ".join(reasoning_parts)

        # ====================================================================
        # STEP 7: BUILD FINAL RESULT
        # ====================================================================

        total_processing_time_ms = (time.time() - start_time) * 1000

        result = EnsembleClassification(
            # Individual layer scores
            rule_score=rule_score,
            history_score=history_score,
            llm_score=llm_score,

            # Final combined result
            final_category=final_category,
            final_importance=final_importance,
            final_confidence=final_confidence,

            # Weights used
            rule_weight=rule_weight,
            history_weight=history_weight,
            llm_weight=llm_weight,

            # Agreement metrics
            layers_agree=layers_agree,
            agreement_score=agreement_score,
            confidence_boost=confidence_boost,

            # Reasoning
            combined_reasoning=combined_reasoning,

            # Metadata
            llm_was_used=llm_was_used,
            total_processing_time_ms=total_processing_time_ms,
            timestamp=datetime.utcnow(),

            # Optional disagreement
            disagreement=disagreement,
        )

        # ====================================================================
        # STEP 8: LOG EVENT
        # ====================================================================

        self._log_classification_event(email, result)

        return result

    # ========================================================================
    # LAYER EXECUTION METHODS
    # ========================================================================

    async def _run_all_layers_parallel(
        self,
        email: EmailToClassify
    ) -> tuple[LayerScore, LayerScore, LayerScore]:
        """
        Run all 3 layers in parallel using asyncio.gather.

        Returns:
            (rule_score, history_score, llm_score)
        """
        # Run all layers concurrently
        rule_task = self._run_rule_layer(email)
        history_task = self._run_history_layer(email)
        llm_task = self._run_llm_layer(email)

        rule_score, history_score, llm_score = await asyncio.gather(
            rule_task,
            history_task,
            llm_task
        )

        return rule_score, history_score, llm_score

    async def _run_rule_and_history_layers(
        self,
        email: EmailToClassify
    ) -> tuple[LayerScore, LayerScore]:
        """
        Run Rule and History layers in parallel.

        Used for smart LLM skip optimization.

        Returns:
            (rule_score, history_score)
        """
        rule_task = self._run_rule_layer(email)
        history_task = self._run_history_layer(email)

        rule_score, history_score = await asyncio.gather(rule_task, history_task)

        return rule_score, history_score

    async def _run_rule_layer(self, email: EmailToClassify) -> LayerScore:
        """Run Rule Layer and convert to LayerScore."""
        start_time = time.time()

        # Run synchronous rule layer (no await needed)
        rule_result = self.rule_layer.classify(email)

        processing_time_ms = (time.time() - start_time) * 1000

        return LayerScore(
            layer_name="rules",
            category=rule_result.category,
            importance=rule_result.importance,
            confidence=rule_result.confidence,
            reasoning=rule_result.reasoning,
            processing_time_ms=processing_time_ms,
        )

    async def _run_history_layer(self, email: EmailToClassify) -> LayerScore:
        """Run History Layer and convert to LayerScore."""
        start_time = time.time()

        # Run synchronous history layer (no await needed)
        history_result = self.history_layer.classify(email)

        processing_time_ms = (time.time() - start_time) * 1000

        return LayerScore(
            layer_name="history",
            category=history_result.category,
            importance=history_result.importance,
            confidence=history_result.confidence,
            reasoning=history_result.reasoning,
            processing_time_ms=processing_time_ms,
        )

    async def _run_llm_layer(self, email: EmailToClassify) -> LayerScore:
        """Run LLM Layer and convert to LayerScore."""
        start_time = time.time()

        # Run async LLM layer
        llm_result = await self.llm_layer.classify(email)

        processing_time_ms = (time.time() - start_time) * 1000

        return LayerScore(
            layer_name="llm",
            category=llm_result.category,
            importance=llm_result.importance,
            confidence=llm_result.confidence,
            reasoning=llm_result.reasoning,
            processing_time_ms=processing_time_ms,
            llm_provider=llm_result.llm_provider_used,
        )

    # ========================================================================
    # SMART LLM SKIP LOGIC
    # ========================================================================

    def _should_skip_llm(
        self,
        rule_score: LayerScore,
        history_score: LayerScore
    ) -> bool:
        """
        Determine if LLM can be skipped based on Rule+History agreement.

        Skip LLM when:
        - Rule and History agree on category
        - Both have confidence >= 0.70
        - Average confidence >= 0.75

        Returns:
            True if LLM can be skipped, False otherwise
        """
        # Check agreement
        if rule_score.category != history_score.category:
            return False  # Disagreement → need LLM

        # Check individual confidence
        if rule_score.confidence < 0.70 or history_score.confidence < 0.70:
            return False  # Low confidence → need LLM

        # Check average confidence
        avg_confidence = (rule_score.confidence + history_score.confidence) / 2
        if avg_confidence < 0.75:
            return False  # Average too low → need LLM

        # Check importance (don't skip for important emails)
        avg_importance = (rule_score.importance + history_score.importance) / 2
        if avg_importance > 0.80:
            return False  # High importance → LLM should verify

        # All checks passed - safe to skip LLM
        return True

    # ========================================================================
    # AGREEMENT DETECTION
    # ========================================================================

    def _check_agreement(
        self,
        rule_score: LayerScore,
        history_score: LayerScore,
        llm_score: Optional[LayerScore]
    ) -> dict:
        """
        Check agreement between layers.

        Returns:
            dict with keys:
                - all_agree: bool (all layers same category)
                - partial_agree: bool (at least 2 layers agree)
                - agreement_score: float (0.0-1.0)
                - agreement_count: int (how many agree with majority)
        """
        if llm_score is None:
            # Only Rule + History
            all_agree = rule_score.category == history_score.category
            partial_agree = all_agree
            agreement_score = 1.0 if all_agree else 0.5
            agreement_count = 2 if all_agree else 1

        else:
            # All 3 layers
            categories = [rule_score.category, history_score.category, llm_score.category]

            # Check if all agree
            all_agree = len(set(categories)) == 1

            # Check if at least 2 agree
            partial_agree = any(
                categories.count(cat) >= 2 for cat in set(categories)
            )

            # Calculate agreement score
            if all_agree:
                agreement_score = 1.0
                agreement_count = 3
            elif partial_agree:
                # Find majority category
                majority_cat = max(set(categories), key=categories.count)
                agreement_count = categories.count(majority_cat)
                agreement_score = agreement_count / 3
            else:
                agreement_score = 0.0
                agreement_count = 1

        return {
            'all_agree': all_agree,
            'partial_agree': partial_agree,
            'agreement_score': agreement_score,
            'agreement_count': agreement_count,
        }

    # ========================================================================
    # CATEGORY SELECTION
    # ========================================================================

    def _select_final_category(
        self,
        rule_score: LayerScore,
        history_score: LayerScore,
        llm_score: Optional[LayerScore],
        rule_weight: float,
        history_weight: float,
        llm_weight: float
    ) -> ImportanceCategory:
        """
        Select final category using weighted voting.

        If all agree → use that category
        If majority agrees → use majority
        If no agreement → use category from highest-weighted layer

        Returns:
            Final ImportanceCategory
        """
        if llm_score is None:
            # Only Rule + History
            if rule_score.category == history_score.category:
                return rule_score.category
            else:
                # Use category from higher-weighted layer
                return rule_score.category if rule_weight > history_weight else history_score.category

        # All 3 layers
        categories = [rule_score.category, history_score.category, llm_score.category]

        # Check if all agree
        if len(set(categories)) == 1:
            return rule_score.category

        # Check for majority (2 out of 3)
        for cat in set(categories):
            if categories.count(cat) >= 2:
                return cat

        # No agreement - use highest-weighted layer
        weights = {
            rule_score.category: rule_weight,
            history_score.category: history_weight,
            llm_score.category: llm_weight,
        }

        # Find category with highest weight
        return max(weights, key=weights.get)

    # ========================================================================
    # BOOTSTRAP MODE DETECTION
    # ========================================================================

    def _is_bootstrap_phase(self, account_id: str) -> bool:
        """
        Check if account is in bootstrap phase (first 2 weeks).

        Returns:
            True if account is less than 14 days old
        """
        # TODO: Query account creation date from database
        # For now, return False (production mode)
        # This will be implemented when account management is added

        return False

    # ========================================================================
    # EVENT LOGGING
    # ========================================================================

    def _log_classification_event(
        self,
        email: EmailToClassify,
        result: EnsembleClassification
    ):
        """Log ensemble classification event."""
        log_event(
            event_type=EventType.EMAIL_CLASSIFIED,
            account_id=email.account_id,
            email_id=email.email_id,
            payload={
                'final_category': result.final_category,
                'final_importance': result.final_importance,
                'final_confidence': result.final_confidence,
                'layers_agree': result.layers_agree,
                'agreement_score': result.agreement_score,
                'confidence_boost': result.confidence_boost,
                'llm_was_used': result.llm_was_used,

                # Individual layer results
                'rule_category': result.rule_score.category,
                'rule_confidence': result.rule_score.confidence,
                'history_category': result.history_score.category,
                'history_confidence': result.history_score.confidence,
                'llm_category': result.llm_score.category if result.llm_score else None,
                'llm_confidence': result.llm_score.confidence if result.llm_score else None,

                # Weights used
                'rule_weight': result.rule_weight,
                'history_weight': result.history_weight,
                'llm_weight': result.llm_weight,
            },
            extra_metadata={
                'llm_provider': result.llm_score.llm_provider if result.llm_score else None,
                'has_disagreement': result.disagreement is not None,
                'needs_review': result.disagreement.needs_user_review if result.disagreement else False,
            },
            processing_time_ms=result.total_processing_time_ms
        )

    def _log_disagreement_event(
        self,
        email: EmailToClassify,
        disagreement: DisagreementInfo
    ):
        """Log layer disagreement event for HITL review."""
        log_event(
            event_type=EventType.USER_FEEDBACK,  # Repurpose for disagreement tracking
            account_id=email.account_id,
            email_id=email.email_id,
            payload={
                'event_subtype': 'layer_disagreement',
                'rule_category': disagreement.rule_category,
                'history_category': disagreement.history_category,
                'llm_category': disagreement.llm_category,
                'final_category': disagreement.final_category,
                'agreement_count': disagreement.agreement_count,
                'confidence_variance': disagreement.confidence_variance,
                'needs_user_review': disagreement.needs_user_review,
            },
            extra_metadata={
                'email_subject': email.subject,
                'email_sender': email.sender,
            }
        )

        # Also log to system logger
        self.logger.warning(
            f"Layer disagreement detected for email {email.email_id} "
            f"(Rule={disagreement.rule_category}, "
            f"History={disagreement.history_category}, "
            f"LLM={disagreement.llm_category}) → needs review"
        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self) -> dict:
        """Get ensemble classification statistics."""
        total = self.stats['total_classifications']

        if total == 0:
            return {**self.stats}

        return {
            **self.stats,
            'agreement_percentage': self.stats['all_layers_agree'] / total * 100,
            'partial_agreement_percentage': self.stats['partial_agreement'] / total * 100,
            'disagreement_percentage': self.stats['no_agreement'] / total * 100,
            'llm_skip_rate': self.stats['llm_skipped'] / total * 100 if self.smart_llm_skip else 0.0,
        }

    def print_stats(self):
        """Print ensemble classification statistics."""
        stats = self.get_stats()

        print("\n" + "=" * 70)
        print("ENSEMBLE CLASSIFIER STATISTICS")
        print("=" * 70)
        print(f"Total Classifications: {stats['total_classifications']}")

        print(f"\nAgreement Distribution:")
        print(f"  All layers agree:     {stats['all_layers_agree']:>3} ({stats.get('agreement_percentage', 0):>5.1f}%)")
        print(f"  Partial agreement:    {stats['partial_agreement']:>3} ({stats.get('partial_agreement_percentage', 0):>5.1f}%)")
        print(f"  No agreement:         {stats['no_agreement']:>3} ({stats.get('disagreement_percentage', 0):>5.1f}%)")

        print(f"\nMode Distribution:")
        print(f"  Bootstrap mode:       {stats['bootstrap_mode_count']:>3}")
        print(f"  Production mode:      {stats['production_mode_count']:>3}")

        if self.smart_llm_skip:
            print(f"\nLLM Optimization:")
            print(f"  LLM used:             {stats['llm_used']:>3}")
            print(f"  LLM skipped:          {stats['llm_skipped']:>3} ({stats.get('llm_skip_rate', 0):>5.1f}%)")

        print("=" * 70 + "\n")
