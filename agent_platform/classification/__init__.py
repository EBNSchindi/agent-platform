"""
Email Importance Classification Module

Ensemble classification system (Phase 2):
- EnsembleClassifier: All 3 layers run in parallel, weighted combination
- Maximum accuracy through multi-layer consensus
- Configurable weights with HITL support
- Agreement-based confidence boosting

Three layers:
1. Rule Layer: Fast pattern matching (spam keywords, automated emails, etc.)
2. History Layer: Learning from user behavior (sender/domain preferences)
3. LLM Layer: Deep semantic analysis with Ollama-first + OpenAI fallback

Legacy (Phase 1):
- LegacyClassifier: Early-stopping architecture (deprecated)
"""

from agent_platform.classification.models import (
    ImportanceScore,
    ClassificationResult,
    RuleLayerResult,
    HistoryLayerResult,
    LLMLayerResult,
    EmailToClassify,
    ClassificationThresholds,
    # Ensemble models (Phase 2)
    LayerScore,
    ScoringWeights,
    DisagreementInfo,
    EnsembleClassification,
)

from agent_platform.classification.importance_rules import RuleLayer
from agent_platform.classification.importance_history import HistoryLayer
from agent_platform.classification.importance_llm import LLMLayer

# Phase 2: Ensemble Classifier (NEW - default)
from agent_platform.classification.ensemble_classifier import EnsembleClassifier

# Phase 1: Legacy Classifier (deprecated, for backwards compatibility)
from agent_platform.classification.legacy_classifier import LegacyClassifier

# Backwards compatibility alias
UnifiedClassifier = LegacyClassifier  # Deprecated - use EnsembleClassifier

__all__ = [
    # Models
    'ImportanceScore',
    'ClassificationResult',
    'RuleLayerResult',
    'HistoryLayerResult',
    'LLMLayerResult',
    'EmailToClassify',
    'ClassificationThresholds',
    # Ensemble models (Phase 2)
    'LayerScore',
    'ScoringWeights',
    'DisagreementInfo',
    'EnsembleClassification',
    # Layers
    'RuleLayer',
    'HistoryLayer',
    'LLMLayer',
    # Classifiers
    'EnsembleClassifier',  # NEW - default
    'LegacyClassifier',    # Deprecated
    'UnifiedClassifier',   # Alias for backwards compatibility (→ LegacyClassifier)
]
