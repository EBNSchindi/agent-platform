"""
Orchestration Module

Coordinates the email classification workflow, integrating all
components: UnifiedClassifier, ReviewQueueManager, FeedbackTracker.
"""

from agent_platform.orchestration.classification_orchestrator import (
    ClassificationOrchestrator,
    process_account_emails,
)

__all__ = [
    'ClassificationOrchestrator',
    'process_account_emails',
]
