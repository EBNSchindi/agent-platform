"""
Email-Agent API Routes
Endpoints specific to Email-Agent monitoring and HITL actions.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import ProcessedEmail, Task, Decision, Question
from agent_platform.events import log_event, EventType, get_events
from agent_platform.memory import (
    get_task,
    update_task_status,
    get_decision,
    make_decision,
    get_question,
    answer_question,
)


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EmailAgentStatus(BaseModel):
    """Email-Agent status response."""
    active: bool
    emails_processed_today: int
    pending_runs: int
    last_run: Optional[datetime] = None


class RunListItem(BaseModel):
    """Run list item (summary)."""
    run_id: str  # Using email_id as run_id for now
    email_id: str
    email_subject: Optional[str]
    email_sender: Optional[str]
    email_received_at: Optional[datetime]
    category: Optional[str]
    confidence: Optional[float]
    needs_human: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RunDetail(BaseModel):
    """Full run details."""
    run_id: str
    email_id: str
    email_subject: Optional[str]
    email_sender: Optional[str]
    email_received_at: Optional[datetime]
    category: Optional[str]
    confidence: Optional[float]
    importance_score: Optional[float]
    draft_reply: Optional[str]
    needs_human: bool
    status: str
    tasks: List[dict]
    decisions: List[dict]
    questions: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class RunActionRequest(BaseModel):
    """Request body for run actions."""
    feedback: Optional[str] = None


class RunEditRequest(BaseModel):
    """Request body for editing run."""
    updated_draft: str
    feedback: str


class RunsListResponse(BaseModel):
    """Paginated runs list response."""
    items: List[RunListItem]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/email-agent/status", response_model=EmailAgentStatus)
def get_email_agent_status(db: Session = Depends(get_db_session)):
    """
    Get Email-Agent status.

    Returns:
        - active: Whether agent is active (always True for now)
        - emails_processed_today: Count of emails processed today
        - pending_runs: Count of emails needing human review
        - last_run: Timestamp of last email processing
    """
    # Count emails processed today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    emails_today = db.query(ProcessedEmail).filter(
        ProcessedEmail.processed_at >= today_start
    ).count()

    # Count pending runs (medium/low confidence)
    pending = db.query(ProcessedEmail).filter(
        ProcessedEmail.confidence < 0.90,  # High confidence threshold
        ProcessedEmail.processed_at >= today_start
    ).count()

    # Get last run
    last_email = db.query(ProcessedEmail).order_by(
        ProcessedEmail.processed_at.desc()
    ).first()

    return EmailAgentStatus(
        active=True,  # Always active for now
        emails_processed_today=emails_today,
        pending_runs=pending,
        last_run=last_email.processed_at if last_email else None
    )


@router.get("/email-agent/runs", response_model=RunsListResponse)
def list_email_agent_runs(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = Query(None),
    needs_human: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """
    List Email-Agent runs (processed emails).

    Query Parameters:
        - limit: Max results (default: 20, max: 100)
        - offset: Pagination offset
        - account_id: Filter by account (e.g., gmail_1)
        - needs_human: Filter by needs_human flag
        - status: Filter by status (pending/accepted/rejected)

    Returns:
        Paginated list of runs
    """
    query = db.query(ProcessedEmail)

    # Apply filters
    if account_id:
        query = query.filter(ProcessedEmail.account_id == account_id)

    if needs_human is not None:
        if needs_human:
            # Medium/low confidence = needs human
            query = query.filter(ProcessedEmail.confidence < 0.90)
        else:
            # High confidence = doesn't need human
            query = query.filter(ProcessedEmail.confidence >= 0.90)

    # Note: status filtering would require new column in ProcessedEmail
    # For now, we infer status from confidence

    # Get total count
    total = query.count()

    # Get items
    items = query.order_by(
        ProcessedEmail.processed_at.desc()
    ).limit(limit).offset(offset).all()

    # Convert to response model
    run_items = []
    for email in items:
        run_items.append(RunListItem(
            run_id=email.email_id,
            email_id=email.email_id,
            email_subject=email.subject,
            email_sender=email.sender,
            email_received_at=email.received_at,
            category=email.category,
            confidence=email.confidence,
            needs_human=email.confidence < 0.90 if email.confidence else True,
            status="pending" if email.confidence and email.confidence < 0.90 else "accepted",
            created_at=email.processed_at,
        ))

    return RunsListResponse(
        items=run_items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/email-agent/runs/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str, db: Session = Depends(get_db_session)):
    """
    Get detailed information about a specific run.

    Args:
        run_id: Run ID (email_id)

    Returns:
        Full run details including extracted memory-objects
    """
    # Get email
    email = db.query(ProcessedEmail).filter(
        ProcessedEmail.email_id == run_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get associated memory-objects
    tasks = db.query(Task).filter(Task.email_id == run_id).all()
    decisions = db.query(Decision).filter(Decision.email_id == run_id).all()
    questions = db.query(Question).filter(Question.email_id == run_id).all()

    # Convert to dicts
    tasks_data = [task.to_dict() for task in tasks]
    decisions_data = [decision.to_dict() for decision in decisions]
    questions_data = [question.to_dict() for question in questions]

    return RunDetail(
        run_id=email.email_id,
        email_id=email.email_id,
        email_subject=email.subject,
        email_sender=email.sender,
        email_received_at=email.received_at,
        category=email.category,
        confidence=email.confidence,
        importance_score=email.importance_score,
        draft_reply=None,  # TODO: Add draft storage
        needs_human=email.confidence < 0.90 if email.confidence else True,
        status="pending" if email.confidence and email.confidence < 0.90 else "accepted",
        tasks=tasks_data,
        decisions=decisions_data,
        questions=questions_data,
        created_at=email.processed_at,
    )


@router.post("/email-agent/runs/{run_id}/accept")
def accept_run(
    run_id: str,
    request: RunActionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Accept a run (user confirms the classification/extraction).

    Args:
        run_id: Run ID (email_id)
        request: Optional feedback

    Actions:
        - Log USER_CONFIRMATION event
        - Update status (future: add status column)
    """
    # Verify email exists
    email = db.query(ProcessedEmail).filter(
        ProcessedEmail.email_id == run_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Run not found")

    # Log event
    log_event(
        event_type=EventType.USER_CONFIRMATION,
        account_id=email.account_id,
        email_id=run_id,
        payload={
            "action": "accept",
            "category": email.category,
            "confidence": email.confidence,
            "feedback": request.feedback,
        }
    )

    return {
        "success": True,
        "message": "Run accepted",
        "run_id": run_id
    }


@router.post("/email-agent/runs/{run_id}/reject")
def reject_run(
    run_id: str,
    request: RunActionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Reject a run (user disagrees with classification).

    Args:
        run_id: Run ID (email_id)
        request: Reason for rejection

    Actions:
        - Log USER_CORRECTION event
        - Trigger learning (future)
    """
    # Verify email exists
    email = db.query(ProcessedEmail).filter(
        ProcessedEmail.email_id == run_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Run not found")

    # Log event
    log_event(
        event_type=EventType.USER_CORRECTION,
        account_id=email.account_id,
        email_id=run_id,
        payload={
            "action": "reject",
            "original_category": email.category,
            "original_confidence": email.confidence,
            "reason": request.feedback,
        }
    )

    return {
        "success": True,
        "message": "Run rejected",
        "run_id": run_id
    }


@router.post("/email-agent/runs/{run_id}/edit")
def edit_run(
    run_id: str,
    request: RunEditRequest,
    db: Session = Depends(get_db_session),
):
    """
    Edit a run (user modifies the draft or classification).

    Args:
        run_id: Run ID (email_id)
        request: Updated draft and feedback

    Actions:
        - Log USER_CORRECTION event
        - Store updated draft (future)
    """
    # Verify email exists
    email = db.query(ProcessedEmail).filter(
        ProcessedEmail.email_id == run_id
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Run not found")

    # Log event
    log_event(
        event_type=EventType.USER_CORRECTION,
        account_id=email.account_id,
        email_id=run_id,
        payload={
            "action": "edit",
            "original_category": email.category,
            "updated_draft": request.updated_draft,
            "feedback": request.feedback,
        }
    )

    return {
        "success": True,
        "message": "Run updated",
        "run_id": run_id
    }


@router.post("/email-agent/trigger-test")
def trigger_test_run(db: Session = Depends(get_db_session)):
    """
    Trigger a test run of the Email-Agent.

    Future: Fetch a test email or process a specific email_id.

    Returns:
        Status of test run
    """
    # TODO: Implement test run logic
    # For now, just return mock response

    return {
        "success": True,
        "message": "Test run triggered",
        "note": "Implementation pending"
    }
