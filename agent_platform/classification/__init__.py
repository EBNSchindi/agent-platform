"""
Email Importance Classification Module

Three-layer classification system:
1. Rule Layer: Fast pattern matching (spam keywords, automated emails, etc.)
2. History Layer: Learning from user behavior (sender/domain preferences)
3. LLM Layer: Deep semantic analysis with Ollama-first + OpenAI fallback

Each layer returns confidence + importance scores. High-confidence results
skip subsequent layers for efficiency.
"""

from agent_platform.classification.models import (
    ImportanceScore,
    ClassificationResult,
    RuleLayerResult,
    HistoryLayerResult,
    LLMLayerResult,
    EmailToClassify,
    ClassificationThresholds,
)

from agent_platform.classification.importance_rules import RuleLayer
from agent_platform.classification.importance_history import HistoryLayer
from agent_platform.classification.importance_llm import LLMLayer
from agent_platform.classification.unified_classifier import UnifiedClassifier

__all__ = [
    # Models
    'ImportanceScore',
    'ClassificationResult',
    'RuleLayerResult',
    'HistoryLayerResult',
    'LLMLayerResult',
    'EmailToClassify',
    'ClassificationThresholds',
    # Layers
    'RuleLayer',
    'HistoryLayer',
    'LLMLayer',
    # Unified Classifier
    'UnifiedClassifier',
]
