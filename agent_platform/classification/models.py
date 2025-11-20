"""
Pydantic Models for Email Importance Classification

These models define the structure of classification results at each layer
and provide type safety for the three-layer classification system.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# IMPORTANCE CATEGORIES
# ============================================================================

ImportanceCategory = Literal[
    "wichtig",              # Important - requires attention
    "action_required",      # Action required - needs response/action
    "nice_to_know",         # Nice to know - informational
    "newsletter",           # Newsletter/marketing
    "system_notifications", # Automated system notifications
    "spam"                  # Spam/unwanted
]


# ============================================================================
# BASE MODELS
# ============================================================================

class ImportanceScore(BaseModel):
    """
    Importance score with confidence.

    - importance: 0.0 (low priority) to 1.0 (high priority)
    - confidence: 0.0 (uncertain) to 1.0 (certain)
    """
    importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score from 0.0 (low) to 1.0 (high)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this classification from 0.0 to 1.0"
    )

    category: ImportanceCategory = Field(
        ...,
        description="Classified importance category"
    )

    reasoning: str = Field(
        ...,
        description="Human-readable explanation of the classification"
    )


class ClassificationResult(BaseModel):
    """
    Complete classification result from any layer.

    Contains the importance score, category, confidence, and metadata
    about which layer/provider was used.
    """
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: ImportanceCategory
    reasoning: str

    # Metadata
    layer_used: Literal["rules", "history", "llm"] = Field(
        ...,
        description="Which classification layer produced this result"
    )

    llm_provider_used: Optional[Literal["ollama", "openai_fallback", "rules_only", "history_only"]] = Field(
        None,
        description="Which LLM provider was used (if any)"
    )

    processing_time_ms: float = Field(
        ...,
        description="Time taken to classify (milliseconds)"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this classification was made"
    )


# ============================================================================
# LAYER-SPECIFIC RESULTS
# ============================================================================

class RuleLayerResult(BaseModel):
    """
    Result from rule-based classification layer.

    Fast pattern matching using keywords, sender patterns, and heuristics.
    High confidence when clear patterns are detected (e.g., spam keywords).
    """
    matched_rules: List[str] = Field(
        default_factory=list,
        description="List of rule names that matched"
    )

    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: ImportanceCategory
    reasoning: str

    # Signals for debugging
    spam_signals: List[str] = Field(
        default_factory=list,
        description="Spam indicators found (if any)"
    )

    auto_reply_signals: List[str] = Field(
        default_factory=list,
        description="Auto-reply indicators found (if any)"
    )

    newsletter_signals: List[str] = Field(
        default_factory=list,
        description="Newsletter indicators found (if any)"
    )


class HistoryLayerResult(BaseModel):
    """
    Result from history-based classification layer.

    Uses learned user behavior patterns from sender/domain preferences.
    High confidence when sufficient historical data exists.
    """
    sender_email: str = Field(..., description="Email sender address")
    sender_domain: str = Field(..., description="Sender domain")

    # Historical data used
    sender_preference_found: bool = Field(
        False,
        description="Whether sender-specific preferences exist"
    )

    domain_preference_found: bool = Field(
        False,
        description="Whether domain-level preferences exist"
    )

    historical_reply_rate: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Historical reply rate for this sender/domain"
    )

    historical_archive_rate: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Historical archive rate for this sender/domain"
    )

    total_historical_emails: int = Field(
        0,
        description="Number of historical emails from this sender/domain"
    )

    # Classification result
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: ImportanceCategory
    reasoning: str

    # Data source
    data_source: Literal["sender", "domain", "default"] = Field(
        ...,
        description="Whether using sender-level, domain-level, or default data"
    )


class LLMLayerResult(BaseModel):
    """
    Result from LLM-based classification layer.

    Deep semantic analysis using Ollama (primary) or OpenAI (fallback).
    Highest accuracy but slowest and most expensive.
    """
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: ImportanceCategory
    reasoning: str

    # LLM metadata
    llm_provider_used: Literal["ollama", "openai_fallback"] = Field(
        ...,
        description="Which LLM provider was used"
    )

    llm_model_used: str = Field(
        ...,
        description="Specific model name used (e.g., gptoss20b, gpt-4o)"
    )

    llm_response_time_ms: float = Field(
        ...,
        description="LLM API response time in milliseconds"
    )

    # Context used
    subject_analyzed: bool = Field(
        True,
        description="Whether email subject was analyzed"
    )

    body_analyzed: bool = Field(
        True,
        description="Whether email body was analyzed"
    )

    sender_context_used: bool = Field(
        False,
        description="Whether sender history context was provided to LLM"
    )


# ============================================================================
# EMAIL DATA MODEL (Input to Classification)
# ============================================================================

class EmailToClassify(BaseModel):
    """
    Email data structure for classification.

    Contains all information needed for the three-layer classification system.
    """
    # Required fields
    email_id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Sender email address")
    body: str = Field(..., description="Email body content (plain text)")

    # Optional context
    received_at: Optional[datetime] = Field(
        None,
        description="When the email was received"
    )

    has_attachments: bool = Field(
        False,
        description="Whether email has attachments"
    )

    is_reply: bool = Field(
        False,
        description="Whether this is a reply to a previous email"
    )

    thread_id: Optional[str] = Field(
        None,
        description="Email thread identifier (if part of conversation)"
    )

    # Account info
    account_id: str = Field(
        ...,
        description="Account ID this email belongs to (e.g., gmail_1)"
    )


# ============================================================================
# THRESHOLDS CONFIGURATION
# ============================================================================

class ClassificationThresholds(BaseModel):
    """
    Configurable thresholds for the classification system.

    Controls when to skip to next layer and what actions to take
    based on confidence levels.
    """
    # Confidence thresholds (adjusted for learning-first approach)
    high_confidence_threshold: float = Field(
        0.90,  # ❗ RAISED from 0.85 → fewer early stops, more learning
        ge=0.0,
        le=1.0,
        description="Skip to action if confidence >= this (default: 0.90, was 0.85)"
    )

    medium_confidence_threshold: float = Field(
        0.65,  # ❗ RAISED from 0.60 → better separation
        ge=0.0,
        le=1.0,
        description="Add to review queue if confidence >= this (default: 0.6)"
    )

    # Importance score thresholds
    low_importance_threshold: float = Field(
        0.4,
        ge=0.0,
        le=1.0,
        description="Move to Low-Priority if importance < this (default: 0.4)"
    )

    high_importance_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Eligible for auto-reply if importance > this (default: 0.7)"
    )

    # History layer requirements
    min_historical_emails_for_high_confidence: int = Field(
        5,
        ge=1,
        description="Minimum emails needed for high-confidence history classification"
    )

    history_confidence_boost: float = Field(
        0.1,
        ge=0.0,
        le=0.3,
        description="Confidence boost when using sender-specific data vs domain"
    )


# ============================================================================
# ENSEMBLE SYSTEM MODELS (Phase 2)
# ============================================================================

class LayerScore(BaseModel):
    """
    Classification result from a single layer (Rule/History/LLM).

    Used in ensemble system where all layers run and results are combined.
    """
    layer_name: Literal["rules", "history", "llm"] = Field(
        ...,
        description="Which layer produced this score"
    )

    category: ImportanceCategory = Field(
        ...,
        description="Classified category"
    )

    importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0=low, 1.0=high)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this classification"
    )

    reasoning: str = Field(
        ...,
        description="Why this layer classified this way"
    )

    processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Processing time for this layer"
    )

    # Optional: Provider info for LLM layer
    llm_provider: Optional[Literal["ollama", "openai"]] = Field(
        None,
        description="LLM provider used (if layer=llm)"
    )


class ScoringWeights(BaseModel):
    """
    Weights for combining layer scores in ensemble system.

    Weights must sum to 1.0. User can adjust via HITL.
    """
    rule_weight: float = Field(
        0.20,
        ge=0.0,
        le=1.0,
        description="Weight for rule layer (default: 20%)"
    )

    history_weight: float = Field(
        0.30,
        ge=0.0,
        le=1.0,
        description="Weight for history layer (default: 30%)"
    )

    llm_weight: float = Field(
        0.50,
        ge=0.0,
        le=1.0,
        description="Weight for LLM layer (default: 50%)"
    )

    # Adaptive mode settings
    adaptive_mode: bool = Field(
        False,
        description="If True, weights adapt based on layer performance"
    )

    # Optional: Different weights for bootstrap phase
    bootstrap_rule_weight: Optional[float] = Field(
        0.30,
        ge=0.0,
        le=1.0,
        description="Rule weight during bootstrap (first 2 weeks)"
    )

    bootstrap_history_weight: Optional[float] = Field(
        0.10,
        ge=0.0,
        le=1.0,
        description="History weight during bootstrap (first 2 weeks)"
    )

    bootstrap_llm_weight: Optional[float] = Field(
        0.60,
        ge=0.0,
        le=1.0,
        description="LLM weight during bootstrap (first 2 weeks)"
    )

    def validate_weights(self) -> bool:
        """Check if weights sum to 1.0 (with small tolerance)."""
        total = self.rule_weight + self.history_weight + self.llm_weight
        return abs(total - 1.0) < 0.01

    def get_weights(self, is_bootstrap: bool = False) -> tuple[float, float, float]:
        """Get weights as tuple (rule, history, llm)."""
        if is_bootstrap and self.bootstrap_rule_weight is not None:
            return (
                self.bootstrap_rule_weight,
                self.bootstrap_history_weight,
                self.bootstrap_llm_weight
            )
        return (self.rule_weight, self.history_weight, self.llm_weight)


class DisagreementInfo(BaseModel):
    """
    Information about layer disagreement.

    Logged when layers produce different categories.
    """
    email_id: str
    account_id: str

    rule_category: ImportanceCategory
    history_category: ImportanceCategory
    llm_category: ImportanceCategory

    final_category: ImportanceCategory

    # Agreement metrics
    layers_agree: bool = Field(
        ...,
        description="True if all 3 layers agree on category"
    )

    partial_agreement: bool = Field(
        ...,
        description="True if at least 2 layers agree"
    )

    agreement_count: int = Field(
        ...,
        ge=0,
        le=3,
        description="Number of layers that agree with final decision"
    )

    # Confidence spread
    confidence_variance: float = Field(
        ...,
        ge=0.0,
        description="Variance in confidence scores (indicates uncertainty)"
    )

    needs_user_review: bool = Field(
        False,
        description="True if disagreement significant enough for HITL review"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )


class EnsembleClassification(BaseModel):
    """
    Combined classification result from ensemble of all 3 layers.

    Contains individual layer scores + weighted combination + agreement metrics.
    """
    # Individual layer scores
    rule_score: LayerScore = Field(
        ...,
        description="Score from rule layer"
    )

    history_score: LayerScore = Field(
        ...,
        description="Score from history layer"
    )

    llm_score: Optional[LayerScore] = Field(
        None,
        description="Score from LLM layer (optional if skipped for performance)"
    )

    # Final combined result
    final_category: ImportanceCategory = Field(
        ...,
        description="Final category after ensemble combination"
    )

    final_importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final importance score (weighted average)"
    )

    final_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final confidence (weighted average + agreement boost/penalty)"
    )

    # Weights used
    rule_weight: float = Field(..., ge=0.0, le=1.0)
    history_weight: float = Field(..., ge=0.0, le=1.0)
    llm_weight: float = Field(..., ge=0.0, le=1.0)

    # Agreement metrics
    layers_agree: bool = Field(
        ...,
        description="True if all layers produced same category"
    )

    agreement_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0.0=complete disagreement, 1.0=perfect agreement"
    )

    confidence_boost: float = Field(
        0.0,
        description="Confidence boost/penalty applied due to agreement (+0.2 to -0.2)"
    )

    # Reasoning
    combined_reasoning: str = Field(
        ...,
        description="Combined explanation from all layers"
    )

    # Metadata
    llm_was_used: bool = Field(
        True,
        description="True if LLM layer was called (False if skipped for performance)"
    )

    total_processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Total processing time across all layers"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )

    # Optional: Disagreement info (if significant)
    disagreement: Optional[DisagreementInfo] = Field(
        None,
        description="Disagreement details if layers didn't agree"
    )
