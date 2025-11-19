"""
Event Types for Digital Twin Platform

Defines all event types that can be logged in the system.
Events follow a hierarchical naming convention: ENTITY_ACTION

Phase 1 Events (E-Mail Processing):
- EMAIL_* - Email-related events
- USER_* - User interaction events
- JOURNAL_* - Journal generation events

Future Events (Phase 2+):
- TASK_*, DECISION_*, QUESTION_* - Memory object events
- PATTERN_*, INSIGHT_* - Analysis events
- TWIN_* - Twin growth events
"""

from enum import Enum


class EventType(str, Enum):
    """
    Event types for the Digital Twin system.

    All events are APPEND-ONLY (immutable).
    """

    # ========================================================================
    # EMAIL EVENTS (Phase 1)
    # ========================================================================

    # Email Intake
    EMAIL_RECEIVED = "EMAIL_RECEIVED"
    """Email was fetched from inbox"""

    EMAIL_ANALYZED = "EMAIL_ANALYZED"
    """Email was analyzed (classification + extraction)"""

    EMAIL_CLASSIFIED = "EMAIL_CLASSIFIED"
    """Email was classified into a category"""

    EMAIL_SUMMARIZED = "EMAIL_SUMMARIZED"
    """Email summary was generated"""

    # Extraction Events
    TASK_EXTRACTED = "TASK_EXTRACTED"
    """Task was extracted from email"""

    DECISION_EXTRACTED = "DECISION_EXTRACTED"
    """Decision was extracted from email"""

    QUESTION_EXTRACTED = "QUESTION_EXTRACTED"
    """Question was extracted from email"""

    # ========================================================================
    # USER INTERACTION EVENTS (Phase 1 - HITL)
    # ========================================================================

    USER_FEEDBACK = "USER_FEEDBACK"
    """User provided feedback (reply/archive/delete/star)"""

    USER_CORRECTION = "USER_CORRECTION"
    """User corrected a classification or extraction"""

    USER_CONFIRMATION = "USER_CONFIRMATION"
    """User confirmed a system action"""

    USER_REJECTION = "USER_REJECTION"
    """User rejected a system suggestion"""

    # ========================================================================
    # JOURNAL EVENTS (Phase 1)
    # ========================================================================

    JOURNAL_GENERATED = "JOURNAL_GENERATED"
    """Daily/weekly journal was generated"""

    JOURNAL_REVIEWED = "JOURNAL_REVIEWED"
    """User reviewed a journal entry"""

    # ========================================================================
    # MEMORY OBJECT EVENTS (Future - Phase 1+)
    # ========================================================================

    TASK_CREATED = "TASK_CREATED"
    """Task memory object was created"""

    TASK_UPDATED = "TASK_UPDATED"
    """Task was updated (status change, etc.)"""

    TASK_COMPLETED = "TASK_COMPLETED"
    """Task was marked as completed"""

    DECISION_CREATED = "DECISION_CREATED"
    """Decision memory object was created"""

    DECISION_MADE = "DECISION_MADE"
    """Decision was made by user"""

    QUESTION_CREATED = "QUESTION_CREATED"
    """Question memory object was created"""

    QUESTION_ANSWERED = "QUESTION_ANSWERED"
    """Question was answered"""

    # ========================================================================
    # LEARNING & ANALYSIS EVENTS (Future - Phase 2+)
    # ========================================================================

    PATTERN_DETECTED = "PATTERN_DETECTED"
    """Behavioral pattern was detected"""

    INSIGHT_GENERATED = "INSIGHT_GENERATED"
    """Twin generated an insight"""

    PREFERENCE_LEARNED = "PREFERENCE_LEARNED"
    """User preference was learned (EMA update)"""

    # ========================================================================
    # TWIN GROWTH EVENTS (Future - Phase 3+)
    # ========================================================================

    TWIN_MILESTONE = "TWIN_MILESTONE"
    """Twin reached a growth milestone"""

    TWIN_IMPROVEMENT = "TWIN_IMPROVEMENT"
    """Twin improved a capability"""

    # ========================================================================
    # SYSTEM EVENTS
    # ========================================================================

    SYSTEM_ERROR = "SYSTEM_ERROR"
    """System error occurred"""

    SYSTEM_WARNING = "SYSTEM_WARNING"
    """System warning was logged"""


# Convenience groupings for querying events

EMAIL_EVENTS = {
    EventType.EMAIL_RECEIVED,
    EventType.EMAIL_ANALYZED,
    EventType.EMAIL_CLASSIFIED,
    EventType.EMAIL_SUMMARIZED,
}

EXTRACTION_EVENTS = {
    EventType.TASK_EXTRACTED,
    EventType.DECISION_EXTRACTED,
    EventType.QUESTION_EXTRACTED,
}

USER_INTERACTION_EVENTS = {
    EventType.USER_FEEDBACK,
    EventType.USER_CORRECTION,
    EventType.USER_CONFIRMATION,
    EventType.USER_REJECTION,
}

MEMORY_EVENTS = {
    EventType.TASK_CREATED,
    EventType.TASK_UPDATED,
    EventType.TASK_COMPLETED,
    EventType.DECISION_CREATED,
    EventType.DECISION_MADE,
    EventType.QUESTION_CREATED,
    EventType.QUESTION_ANSWERED,
}

LEARNING_EVENTS = {
    EventType.PATTERN_DETECTED,
    EventType.INSIGHT_GENERATED,
    EventType.PREFERENCE_LEARNED,
}

TWIN_GROWTH_EVENTS = {
    EventType.TWIN_MILESTONE,
    EventType.TWIN_IMPROVEMENT,
}

SYSTEM_EVENTS = {
    EventType.SYSTEM_ERROR,
    EventType.SYSTEM_WARNING,
}

# Phase 1 Events (currently implemented)
PHASE_1_EVENTS = (
    EMAIL_EVENTS
    | EXTRACTION_EVENTS
    | USER_INTERACTION_EVENTS
    | {EventType.JOURNAL_GENERATED, EventType.JOURNAL_REVIEWED}
)
