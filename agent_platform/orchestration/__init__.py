"""
Orchestration Module (Phase 2: Ensemble System)

Coordinates the email classification workflow, integrating all
components:
- EnsembleClassifier (Phase 2 - all layers parallel)
- ReviewQueueManager
- ExtractionAgent

Legacy support for LegacyClassifier (early-stopping) available.
"""

from agent_platform.orchestration.classification_orchestrator import (
    ClassificationOrchestrator,
    process_account_emails,
)

__all__ = [
    'ClassificationOrchestrator',
    'process_account_emails',
]
