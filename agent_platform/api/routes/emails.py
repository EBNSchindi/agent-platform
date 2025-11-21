"""
Email API Routes

Endpoints for fetching and managing emails with full body content.
Designed for inbox views and email reading functionality.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import ProcessedEmail, Task, Decision, Question


router = APIRouter()


# Pydantic Models

class EmailListItem(BaseModel):
    """Email list item (summary view for inbox)."""
    id: int
    email_id: str
    account_id: str
    sender: Optional[str]
    subject: Optional[str]
    received_at: Optional[datetime]
    category: Optional[str]
    confidence: Optional[float]
    importance_score: Optional[float]
    has_attachments: bool
    thread_id: Optional[str]
    processed_at: datetime

    class Config:
        from_attributes = True


class EmailDetail(BaseModel):
    """Full email details including body content."""
    id: int
    email_id: str
    account_id: str
    sender: Optional[str]
    subject: Optional[str]
    received_at: Optional[datetime]
    body_text: Optional[str] = Field(None, description="Plain text email body")
    body_html: Optional[str] = Field(None, description="HTML email body")
    category: Optional[str]
    confidence: Optional[float]
    importance_score: Optional[float]
    has_attachments: bool
    attachments_metadata: Optional[dict]
    thread_id: Optional[str]
    in_reply_to: Optional[str]
    references: Optional[List[str]]
    labels: Optional[List[str]]
    processed_at: datetime
    tasks: List[dict] = Field(default_factory=list, description="Extracted tasks")
    decisions: List[dict] = Field(default_factory=list, description="Extracted decisions")
    questions: List[dict] = Field(default_factory=list, description="Extracted questions")

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Paginated email list response."""
    emails: List[EmailListItem]
    total: int
    limit: int
    offset: int
    account_id: Optional[str] = None


# API Endpoints

@router.get("/emails", response_model=EmailListResponse)
def list_emails(
    account_id: Optional[str] = Query(None, description="Filter by account ID (e.g., 'gmail_1', 'ionos')"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., 'wichtig', 'nice_to_know')"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of emails to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db_session)
):
    """
    List emails with filtering and pagination.

    Designed for inbox views - returns email metadata without body content
    for efficient list rendering. Use GET /emails/{email_id} to fetch full body.

    **Query Parameters:**
    - `account_id`: Filter by specific account (e.g., 'gmail_1', 'gmail_2', 'ionos')
    - `category`: Filter by classification category
    - `limit`: Number of emails per page (default: 20, max: 100)
    - `offset`: Pagination offset (default: 0)

    **Example Requests:**
    ```
    GET /api/v1/emails?limit=20
    GET /api/v1/emails?account_id=gmail_1&limit=10
    GET /api/v1/emails?account_id=gmail_2&category=wichtig&limit=50
    GET /api/v1/emails?offset=20&limit=20  # Page 2
    ```

    **Example Response:**
    ```json
    {
      "emails": [
        {
          "id": 1523,
          "email_id": "msg_abc123",
          "account_id": "gmail_1",
          "sender": "boss@company.com",
          "subject": "Q4 Report Review Required",
          "received_at": "2025-11-21T10:30:00",
          "category": "wichtig",
          "confidence": 0.92,
          "importance_score": 0.85,
          "has_attachments": true,
          "thread_id": "thread_xyz",
          "processed_at": "2025-11-21T10:31:00"
        }
      ],
      "total": 1523,
      "limit": 20,
      "offset": 0,
      "account_id": "gmail_1"
    }
    ```

    **Use Cases:**
    - Inbox list view (paginated)
    - Account-specific inbox (filter by account_id)
    - Category-filtered views (filter by category)
    - Infinite scroll pagination (use offset)

    **Performance:**
    - Results ordered by received_at DESC (newest first)
    - Body content excluded for faster queries
    - Indexed on account_id, category, received_at
    """
    try:
        # Build query
        query = select(ProcessedEmail)

        # Apply filters
        if account_id:
            query = query.where(ProcessedEmail.account_id == account_id)

        if category:
            query = query.where(ProcessedEmail.category == category)

        # Order by received_at DESC (newest first)
        query = query.order_by(desc(ProcessedEmail.received_at))

        # Count total (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        results = db.execute(query).scalars().all()

        # Convert to list items (exclude body content)
        emails = [
            EmailListItem(
                id=email.id,
                email_id=email.email_id,
                account_id=str(email.account_id),  # Convert to string
                sender=email.sender,
                subject=email.subject,
                received_at=email.received_at,
                category=email.category,
                confidence=email.confidence,
                importance_score=email.importance_score,
                has_attachments=bool(email.attachments_metadata),
                thread_id=email.thread_id,
                processed_at=email.processed_at
            )
            for email in results
        ]

        return EmailListResponse(
            emails=emails,
            total=total or 0,
            limit=limit,
            offset=offset,
            account_id=account_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch emails: {str(e)}"
        )


@router.get("/emails/{email_id}", response_model=EmailDetail)
def get_email(
    email_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get full email details including body content.

    Returns complete email data including:
    - Plain text body (body_text)
    - HTML body (body_html)
    - Extracted tasks, decisions, questions
    - Attachments metadata
    - Thread information

    **Example Request:**
    ```
    GET /api/v1/emails/msg_abc123
    ```

    **Example Response:**
    ```json
    {
      "id": 1523,
      "email_id": "msg_abc123",
      "account_id": "gmail_1",
      "sender": "boss@company.com",
      "subject": "Q4 Report Review Required",
      "received_at": "2025-11-21T10:30:00",
      "body_text": "Hi Team,\n\nPlease review the attached Q4 report by Friday...",
      "body_html": "<html><body><p>Hi Team,...</p></body></html>",
      "category": "wichtig",
      "confidence": 0.92,
      "importance_score": 0.85,
      "has_attachments": true,
      "attachments_metadata": {
        "count": 1,
        "files": ["Q4_Report.pdf"]
      },
      "thread_id": "thread_xyz",
      "tasks": [
        {
          "description": "Review Q4 report",
          "deadline": "2025-11-25",
          "priority": "high"
        }
      ],
      "decisions": [],
      "questions": [],
      "processed_at": "2025-11-21T10:31:00"
    }
    ```

    **Use Cases:**
    - Email detail view / reading pane
    - Display full email body (text or HTML)
    - Show extracted memory objects (tasks, decisions, questions)
    - View attachments metadata
    - Thread navigation

    **Error Responses:**
    - 404: Email not found
    - 500: Server error
    """
    try:
        # Fetch email from database
        query = select(ProcessedEmail).where(ProcessedEmail.email_id == email_id)
        result = db.execute(query).scalar_one_or_none()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Email '{email_id}' not found"
            )

        # Fetch related memory objects
        tasks = []
        decisions = []
        questions = []

        # Fetch tasks
        tasks_query = select(Task).where(Task.email_id == email_id)
        task_results = db.execute(tasks_query).scalars().all()
        tasks = [
            {
                "id": task.id,
                "description": task.description,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "priority": task.priority,
                "status": task.status,
                "assignee": task.assignee
            }
            for task in task_results
        ]

        # Fetch decisions
        decisions_query = select(Decision).where(Decision.email_id == email_id)
        decision_results = db.execute(decisions_query).scalars().all()
        decisions = [
            {
                "id": dec.id,
                "question": dec.question,
                "options": dec.options,
                "recommendation": dec.recommendation,
                "urgency": dec.urgency,
                "status": dec.status
            }
            for dec in decision_results
        ]

        # Fetch questions
        questions_query = select(Question).where(Question.email_id == email_id)
        question_results = db.execute(questions_query).scalars().all()
        questions = [
            {
                "id": q.id,
                "question": q.question,
                "question_type": q.question_type,
                "urgency": q.urgency,
                "status": q.status
            }
            for q in question_results
        ]

        # Build response (use getattr for optional fields to handle schema variations)
        attachments_meta = getattr(result, 'attachments_metadata', None)
        # Handle case where attachments_metadata is a list instead of dict
        if isinstance(attachments_meta, list):
            attachments_meta = None if not attachments_meta else {"files": attachments_meta}

        return EmailDetail(
            id=result.id,
            email_id=result.email_id,
            account_id=str(result.account_id),  # Convert to string
            sender=result.sender,
            subject=result.subject,
            received_at=result.received_at,
            body_text=result.body_text or "",
            body_html=result.body_html or "",
            category=result.category,
            confidence=result.confidence,
            importance_score=result.importance_score,
            has_attachments=bool(attachments_meta),
            attachments_metadata=attachments_meta,
            thread_id=getattr(result, 'thread_id', None),
            in_reply_to=getattr(result, 'in_reply_to', None),
            references=getattr(result, 'email_references', None),
            labels=getattr(result, 'labels', None),
            processed_at=result.processed_at,
            tasks=tasks,
            decisions=decisions,
            questions=questions
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch email details: {str(e)}"
        )
