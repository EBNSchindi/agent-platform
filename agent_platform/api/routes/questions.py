"""
Questions API Routes
CRUD operations for Question memory-objects.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import Question
from agent_platform.memory import get_question, get_pending_questions, answer_question


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class QuestionResponse(BaseModel):
    """Question response model."""
    question_id: str
    question: str
    context: Optional[str]
    question_type: str
    requires_response: bool
    urgency: str
    status: str
    answer: Optional[str]
    answered_at: Optional[datetime]
    email_subject: Optional[str]
    email_sender: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnswerQuestionRequest(BaseModel):
    """Request to answer a question."""
    answer: str


class QuestionsListResponse(BaseModel):
    """Paginated questions list."""
    items: List[QuestionResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/questions", response_model=QuestionsListResponse)
def list_questions(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    requires_response: Optional[bool] = Query(None),
    db: Session = Depends(get_db_session),
):
    """
    List questions with optional filtering.

    Query Parameters:
        - limit: Max results (default: 20)
        - offset: Pagination offset
        - account_id: Filter by account
        - status: Filter by status (pending/answered/delegated/not_applicable)
        - requires_response: Filter by requires_response flag
    """
    query = db.query(Question)

    # Apply filters
    if account_id:
        query = query.filter(Question.account_id == account_id)
    if status:
        query = query.filter(Question.status == status)
    if requires_response is not None:
        query = query.filter(Question.requires_response == requires_response)

    # Get total count
    total = query.count()

    # Get items
    items = query.order_by(Question.created_at.desc()).limit(limit).offset(offset).all()

    return QuestionsListResponse(
        items=[QuestionResponse.from_orm(item) for item in items],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/questions/{question_id}", response_model=QuestionResponse)
def get_question_detail(question_id: str, db: Session = Depends(get_db_session)):
    """Get single question by ID."""
    question = get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse.from_orm(question)


@router.post("/questions/{question_id}/answer")
def answer_question_endpoint(
    question_id: str,
    request: AnswerQuestionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Answer a question.

    Args:
        question_id: Question ID
        request: Answer text
    """
    question = get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Answer question
    answer_question(question_id=question_id, answer=request.answer)

    return {
        "success": True,
        "message": "Question answered",
        "question_id": question_id
    }
