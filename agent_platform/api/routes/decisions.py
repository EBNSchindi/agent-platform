"""
Decisions API Routes
CRUD operations for Decision memory-objects.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import Decision
from agent_platform.memory import get_decision, get_pending_decisions, make_decision


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class DecisionResponse(BaseModel):
    """Decision response model."""
    decision_id: str
    question: str
    context: Optional[str]
    options: List[str]
    recommendation: Optional[str]
    urgency: str
    status: str
    requires_my_input: bool
    chosen_option: Optional[str]
    decision_notes: Optional[str]
    decided_at: Optional[datetime]
    email_subject: Optional[str]
    email_sender: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MakeDecisionRequest(BaseModel):
    """Request to make a decision."""
    chosen_option: str
    decision_notes: Optional[str] = None


class DecisionsListResponse(BaseModel):
    """Paginated decisions list."""
    items: List[DecisionResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/decisions", response_model=DecisionsListResponse)
def list_decisions(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """
    List decisions with optional filtering.

    Query Parameters:
        - limit: Max results (default: 20)
        - offset: Pagination offset
        - account_id: Filter by account
        - status: Filter by status (pending/decided/delegated/cancelled)
        - urgency: Filter by urgency (low/medium/high/urgent)
    """
    query = db.query(Decision)

    # Apply filters
    if account_id:
        query = query.filter(Decision.account_id == account_id)
    if status:
        query = query.filter(Decision.status == status)
    if urgency:
        query = query.filter(Decision.urgency == urgency)

    # Get total count
    total = query.count()

    # Get items
    items = query.order_by(Decision.created_at.desc()).limit(limit).offset(offset).all()

    return DecisionsListResponse(
        items=[DecisionResponse.from_orm(item) for item in items],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/decisions/{decision_id}", response_model=DecisionResponse)
def get_decision_detail(decision_id: str, db: Session = Depends(get_db_session)):
    """Get single decision by ID."""
    decision = get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionResponse.from_orm(decision)


@router.post("/decisions/{decision_id}/decide")
def make_decision_endpoint(
    decision_id: str,
    request: MakeDecisionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Make a decision (choose an option).

    Args:
        decision_id: Decision ID
        request: Chosen option and optional notes
    """
    decision = get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Make decision
    make_decision(
        decision_id=decision_id,
        chosen_option=request.chosen_option,
        decision_notes=request.decision_notes
    )

    return {
        "success": True,
        "message": "Decision made",
        "decision_id": decision_id,
        "chosen_option": request.chosen_option
    }
