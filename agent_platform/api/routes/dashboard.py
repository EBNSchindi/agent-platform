"""
Dashboard API Routes
Aggregated statistics and overview data for the cockpit.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from collections import defaultdict

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import (
    Task,
    Decision,
    Question,
    ProcessedEmail,
    EmailAccount,
)
from agent_platform.events import get_events, EventType


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TasksStats(BaseModel):
    """Task statistics."""
    pending: int
    in_progress: int
    completed_today: int
    overdue: int


class DecisionsStats(BaseModel):
    """Decision statistics."""
    pending: int
    decided_today: int


class QuestionsStats(BaseModel):
    """Question statistics."""
    pending: int
    answered_today: int


class EmailsStats(BaseModel):
    """Email processing statistics."""
    processed_today: int
    by_category: Dict[str, int]
    high_confidence: int
    medium_confidence: int
    low_confidence: int


class AccountInfo(BaseModel):
    """Account information."""
    account_id: str
    email_address: str
    active: bool


class DashboardOverview(BaseModel):
    """Dashboard overview response."""
    tasks: TasksStats
    decisions: DecisionsStats
    questions: QuestionsStats
    emails: EmailsStats
    accounts: List[AccountInfo]
    needs_human_count: int


class TopSender(BaseModel):
    """Top sender info."""
    sender: str
    count: int


class TodaySummary(BaseModel):
    """Today's summary response."""
    date: str
    emails_processed: int
    tasks_created: int
    tasks_completed: int
    decisions_made: int
    questions_answered: int
    top_senders: List[TopSender]


class ActivityItem(BaseModel):
    """Activity feed item."""
    activity_id: str
    timestamp: str
    event_type: str
    description: str
    icon_type: str  # email, task, decision, question, user, system
    account_id: Optional[str]
    email_id: Optional[str]
    metadata: Dict[str, Any]


class ActivityFeedResponse(BaseModel):
    """Activity feed response."""
    items: List[ActivityItem]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_dashboard_overview(db: Session = Depends(get_db_session)):
    """
    Get dashboard overview with key statistics.

    Returns aggregated stats for:
    - Tasks (pending, in_progress, completed_today, overdue)
    - Decisions (pending, decided_today)
    - Questions (pending, answered_today)
    - Emails (processed_today, by_category, confidence breakdown)
    - Accounts (configured accounts)
    - Needs human count (medium/low confidence items)
    """
    # Calculate time boundaries
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.utcnow()

    # Tasks stats
    tasks_pending = db.query(Task).filter(Task.status == 'pending').count()
    tasks_in_progress = db.query(Task).filter(Task.status == 'in_progress').count()
    tasks_completed_today = db.query(Task).filter(
        Task.status == 'completed',
        Task.completed_at >= today_start
    ).count()
    tasks_overdue = db.query(Task).filter(
        Task.status.in_(['pending', 'in_progress']),
        Task.deadline < now
    ).count()

    # Decisions stats
    decisions_pending = db.query(Decision).filter(Decision.status == 'pending').count()
    decisions_decided_today = db.query(Decision).filter(
        Decision.status == 'decided',
        Decision.decided_at >= today_start
    ).count()

    # Questions stats
    questions_pending = db.query(Question).filter(Question.status == 'pending').count()
    questions_answered_today = db.query(Question).filter(
        Question.status == 'answered',
        Question.answered_at >= today_start
    ).count()

    # Emails stats
    emails_today = db.query(ProcessedEmail).filter(
        ProcessedEmail.processed_at >= today_start
    ).all()

    emails_processed_today = len(emails_today)

    # Category breakdown
    by_category = defaultdict(int)
    high_conf = 0
    medium_conf = 0
    low_conf = 0

    for email in emails_today:
        if email.category:
            by_category[email.category] += 1

        if email.confidence:
            if email.confidence >= 0.90:
                high_conf += 1
            elif email.confidence >= 0.65:
                medium_conf += 1
            else:
                low_conf += 1

    # Needs human count (medium/low confidence)
    needs_human_count = medium_conf + low_conf

    # Accounts (from config, not DB for now)
    from agent_platform.core.config import Config
    accounts = []
    for account_id, account_data in Config.GMAIL_ACCOUNTS.items():
        if account_data.get('email'):
            accounts.append(AccountInfo(
                account_id=account_id,
                email_address=account_data['email'],
                active=True
            ))

    return DashboardOverview(
        tasks=TasksStats(
            pending=tasks_pending,
            in_progress=tasks_in_progress,
            completed_today=tasks_completed_today,
            overdue=tasks_overdue
        ),
        decisions=DecisionsStats(
            pending=decisions_pending,
            decided_today=decisions_decided_today
        ),
        questions=QuestionsStats(
            pending=questions_pending,
            answered_today=questions_answered_today
        ),
        emails=EmailsStats(
            processed_today=emails_processed_today,
            by_category=dict(by_category),
            high_confidence=high_conf,
            medium_confidence=medium_conf,
            low_confidence=low_conf
        ),
        accounts=accounts,
        needs_human_count=needs_human_count
    )


@router.get("/dashboard/today", response_model=TodaySummary)
def get_today_summary(db: Session = Depends(get_db_session)):
    """
    Get summary for today.

    Returns:
        - Date
        - Emails processed
        - Tasks created/completed
        - Decisions made
        - Questions answered
        - Top senders
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get today's data
    tasks_created = db.query(Task).filter(Task.created_at >= today_start).count()
    tasks_completed = db.query(Task).filter(
        Task.status == 'completed',
        Task.completed_at >= today_start
    ).count()
    decisions_made = db.query(Decision).filter(
        Decision.status == 'decided',
        Decision.decided_at >= today_start
    ).count()
    questions_answered = db.query(Question).filter(
        Question.status == 'answered',
        Question.answered_at >= today_start
    ).count()

    # Emails processed
    emails_today = db.query(ProcessedEmail).filter(
        ProcessedEmail.processed_at >= today_start
    ).all()

    # Top senders
    sender_counts = defaultdict(int)
    for email in emails_today:
        if email.sender:
            sender_counts[email.sender] += 1

    top_senders = [
        TopSender(sender=sender, count=count)
        for sender, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return TodaySummary(
        date=today_start.strftime('%Y-%m-%d'),
        emails_processed=len(emails_today),
        tasks_created=tasks_created,
        tasks_completed=tasks_completed,
        decisions_made=decisions_made,
        questions_answered=questions_answered,
        top_senders=top_senders
    )


@router.get("/dashboard/activity", response_model=ActivityFeedResponse)
def get_activity_feed(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
):
    """
    Get recent activity feed (event-based timeline).

    Returns recent events across all systems:
    - Email classifications
    - Task extractions/completions
    - Decision extractions/resolutions
    - Question extractions/answers
    - User interactions
    - Journal generation

    Query Parameters:
        - limit: Max results (default: 20, max: 100)
        - offset: Pagination offset
    """
    # Get recent events (last 24 hours, most recent first)
    yesterday = datetime.utcnow() - timedelta(days=1)

    # Get events from event log
    events = get_events(
        start_time=yesterday,
        limit=limit + offset  # Fetch more to account for offset
    )

    # Transform events into activity items
    activities = []
    for event in events:
        activity = _event_to_activity_item(event)
        if activity:
            activities.append(activity)

    # Apply offset and limit
    paginated_activities = activities[offset:offset + limit]

    return ActivityFeedResponse(
        items=paginated_activities,
        total=len(activities),
        limit=limit,
        offset=offset
    )


def _event_to_activity_item(event) -> Optional[ActivityItem]:
    """Convert event to activity item with human-readable description."""

    # Map event types to descriptions and icons
    event_mappings = {
        'EMAIL_CLASSIFIED': {
            'icon': 'email',
            'template': 'Email classified as {category} ({confidence:.0%} confidence)'
        },
        'EMAIL_RECEIVED': {
            'icon': 'email',
            'template': 'New email received'
        },
        'TASK_EXTRACTED': {
            'icon': 'task',
            'template': 'Task extracted from email'
        },
        'TASK_COMPLETED': {
            'icon': 'task',
            'template': 'Task completed'
        },
        'DECISION_EXTRACTED': {
            'icon': 'decision',
            'template': 'Decision extracted from email'
        },
        'QUESTION_EXTRACTED': {
            'icon': 'question',
            'template': 'Question extracted from email'
        },
        'USER_CONFIRMATION': {
            'icon': 'user',
            'template': 'User confirmed classification'
        },
        'USER_CORRECTION': {
            'icon': 'user',
            'template': 'User corrected classification'
        },
        'USER_FEEDBACK': {
            'icon': 'user',
            'template': 'User provided feedback'
        },
        'JOURNAL_GENERATED': {
            'icon': 'system',
            'template': 'Daily journal generated'
        },
    }

    event_type_str = event.event_type if isinstance(event.event_type, str) else event.event_type.value
    mapping = event_mappings.get(event_type_str)

    if not mapping:
        # Default fallback for unmapped event types
        mapping = {
            'icon': 'system',
            'template': event_type_str.replace('_', ' ').title()
        }

    # Build description from template and payload
    try:
        payload = event.payload or {}
        description = mapping['template'].format(**payload)
    except (KeyError, ValueError, AttributeError):
        # Fallback if template formatting fails
        description = mapping['template']

    return ActivityItem(
        activity_id=event.event_id,
        timestamp=event.timestamp.isoformat(),
        event_type=event_type_str,
        description=description,
        icon_type=mapping['icon'],
        account_id=event.account_id,
        email_id=event.email_id,
        metadata=event.payload or {}
    )
