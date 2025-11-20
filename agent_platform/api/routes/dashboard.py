"""
Dashboard API Routes
Aggregated statistics and overview data for the cockpit.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
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
