"""
Review Queue API Routes

CRUD operations for Review Queue - User review of medium-confidence email classifications.
Integrates with ReviewQueueManager and ReviewHandler for approve/reject/modify actions.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import ReviewQueueItem
from agent_platform.review import ReviewQueueManager, ReviewHandler


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ReviewQueueItemResponse(BaseModel):
    """Review queue item response model."""
    id: int
    account_id: str
    email_id: str
    processed_email_id: Optional[int]
    subject: Optional[str]
    sender: Optional[str]
    snippet: Optional[str]
    suggested_category: str
    importance_score: float
    confidence: float
    reasoning: Optional[str]
    status: str
    user_approved: Optional[bool]
    user_corrected_category: Optional[str]
    user_feedback: Optional[str]
    added_to_queue_at: datetime
    reviewed_at: Optional[datetime]
    extra_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class ReviewQueueListResponse(BaseModel):
    """Paginated review queue list."""
    items: List[ReviewQueueItemResponse]
    total: int
    pending_count: int
    limit: int
    offset: int


class ReviewQueueStatsResponse(BaseModel):
    """Review queue statistics."""
    total_items: int
    pending_count: int
    approved_count: int
    rejected_count: int
    modified_count: int
    by_category: Dict[str, int]
    avg_age_hours: float


class ApproveRequest(BaseModel):
    """Request to approve classification."""
    user_feedback: Optional[str] = Field(None, description="Optional user feedback text")
    apply_action: bool = Field(False, description="Whether to apply Gmail actions (label, archive, etc.)")


class RejectRequest(BaseModel):
    """Request to reject classification."""
    corrected_category: Optional[str] = Field(None, description="Optional corrected category")
    user_feedback: Optional[str] = Field(None, description="Optional user feedback text")
    apply_action: bool = Field(False, description="Whether to apply Gmail actions")


class ModifyRequest(BaseModel):
    """Request to modify classification with corrected category."""
    corrected_category: str = Field(..., description="Corrected email category")
    user_feedback: Optional[str] = Field(None, description="Optional user feedback text")
    apply_action: bool = Field(True, description="Whether to apply Gmail actions")


class ActionResponse(BaseModel):
    """Response for approve/reject/modify actions."""
    success: bool
    message: str
    item: Optional[ReviewQueueItemResponse]
    action_applied: Optional[Dict[str, Any]]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/review-queue", response_model=ReviewQueueListResponse)
def list_review_queue_items(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    status: str = Query("pending", description="Filter by status (pending/approved/rejected/modified)"),
    limit: int = Query(50, le=100, description="Max results (default: 50, max: 100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db_session),
):
    """
    List review queue items with filtering and pagination.

    Returns medium-confidence emails that need human review (confidence: 0.65-0.90).

    Query Parameters:
        - account_id: Filter by account (gmail_1, gmail_2, etc.)
        - status: Filter by status (pending, approved, rejected, modified)
        - limit: Max results (default: 50, max: 100)
        - offset: Pagination offset
    """
    queue_manager = ReviewQueueManager(db=db)

    # Build query
    query = db.query(ReviewQueueItem)

    # Apply filters
    if account_id:
        query = query.filter(ReviewQueueItem.account_id == account_id)
    if status:
        query = query.filter(ReviewQueueItem.status == status)

    # Get total count
    total = query.count()

    # Get pending count (for stats)
    pending_count = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.status == "pending"
    ).count()

    # Order by importance (descending) and then by time added
    query = query.order_by(
        ReviewQueueItem.importance_score.desc(),
        ReviewQueueItem.added_to_queue_at.asc()
    )

    # Paginate
    items = query.offset(offset).limit(limit).all()

    return ReviewQueueListResponse(
        items=[ReviewQueueItemResponse.model_validate(item) for item in items],
        total=total,
        pending_count=pending_count,
        limit=limit,
        offset=offset,
    )


@router.get("/review-queue/{item_id}", response_model=ReviewQueueItemResponse)
def get_review_queue_item(
    item_id: int,
    db: Session = Depends(get_db_session),
):
    """
    Get specific review queue item by ID.

    Returns detailed information about a single review item.
    """
    queue_manager = ReviewQueueManager(db=db)

    item = queue_manager.get_item_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")

    return ReviewQueueItemResponse.model_validate(item)


@router.post("/review-queue/{item_id}/approve", response_model=ActionResponse)
def approve_review_item(
    item_id: int,
    request: ApproveRequest,
    db: Session = Depends(get_db_session),
):
    """
    Approve the suggested classification.

    This indicates the user agrees with the system's classification.
    The system will learn from this approval and update sender preferences (EMA).

    Actions:
        1. Mark item as approved in review queue
        2. Log USER_CONFIRMATION event
        3. Update sender preferences via EMA
        4. Optionally apply Gmail actions (label, archive)

    Request Body:
        - user_feedback: Optional user comment
        - apply_action: Whether to apply Gmail actions
    """
    handler = ReviewHandler(db=db)

    result = handler.approve_classification(
        item_id=item_id,
        user_feedback=request.user_feedback,
        apply_action=request.apply_action,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to approve item"))

    item = result.get("item")
    return ActionResponse(
        success=True,
        message="Classification approved successfully",
        item=ReviewQueueItemResponse.model_validate(item) if item else None,
        action_applied=result.get("action_applied"),
    )


@router.post("/review-queue/{item_id}/reject", response_model=ActionResponse)
def reject_review_item(
    item_id: int,
    request: RejectRequest,
    db: Session = Depends(get_db_session),
):
    """
    Reject the suggested classification.

    This indicates the user disagrees with the system's classification.
    The system will learn from this rejection and update sender preferences (EMA).

    Actions:
        1. Mark item as rejected in review queue
        2. Log USER_REJECTION event
        3. Update sender preferences via EMA (negative feedback)
        4. Optionally provide corrected category
        5. Optionally apply Gmail actions

    Request Body:
        - corrected_category: Optional corrected category
        - user_feedback: Optional user comment
        - apply_action: Whether to apply Gmail actions
    """
    handler = ReviewHandler(db=db)

    result = handler.reject_classification(
        item_id=item_id,
        corrected_category=request.corrected_category,
        user_feedback=request.user_feedback,
        apply_action=request.apply_action,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to reject item"))

    item = result.get("item")
    return ActionResponse(
        success=True,
        message="Classification rejected successfully",
        item=ReviewQueueItemResponse.model_validate(item) if item else None,
        action_applied=result.get("action_applied"),
    )


@router.post("/review-queue/{item_id}/modify", response_model=ActionResponse)
def modify_review_item(
    item_id: int,
    request: ModifyRequest,
    db: Session = Depends(get_db_session),
):
    """
    Modify classification with corrected category.

    This indicates the user wants to reclassify the email.
    The system will learn from this correction and update sender preferences (EMA).

    Actions:
        1. Mark item as modified in review queue
        2. Save corrected category
        3. Log USER_CORRECTION event
        4. Update sender preferences via EMA (strong correction signal)
        5. Apply Gmail actions with corrected category

    Request Body:
        - corrected_category: New category (required)
        - user_feedback: Optional user comment
        - apply_action: Whether to apply Gmail actions (default: true)
    """
    handler = ReviewHandler(db=db)

    # Process as modification with corrected category
    result = handler.modify_classification(
        item_id=item_id,
        corrected_category=request.corrected_category,
        user_feedback=request.user_feedback,
        apply_action=request.apply_action,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to modify item"))

    item = result.get("item")
    return ActionResponse(
        success=True,
        message=f"Classification modified to '{request.corrected_category}' successfully",
        item=ReviewQueueItemResponse.model_validate(item) if item else None,
        action_applied=result.get("action_applied"),
    )


@router.get("/review-queue/stats", response_model=ReviewQueueStatsResponse)
def get_review_queue_stats(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    db: Session = Depends(get_db_session),
):
    """
    Get review queue statistics.

    Returns aggregate statistics about the review queue:
    - Total items
    - Pending count
    - Approved/Rejected/Modified counts
    - Average importance and confidence scores

    Query Parameters:
        - account_id: Filter by account (optional)
    """
    queue_manager = ReviewQueueManager(db=db)

    stats = queue_manager.get_queue_statistics(account_id=account_id)

    return ReviewQueueStatsResponse(
        total_items=stats.get("total_items", 0),
        pending_count=stats.get("pending", 0),
        approved_count=stats.get("approved", 0),
        rejected_count=stats.get("rejected", 0),
        modified_count=stats.get("modified", 0),
        by_category=stats.get("by_category", {}),
        avg_age_hours=stats.get("avg_age_hours", 0.0),
    )


@router.delete("/review-queue/{item_id}")
def delete_review_item(
    item_id: int,
    db: Session = Depends(get_db_session),
):
    """
    Delete a review queue item.

    This is typically used for cleanup of old reviewed items.
    Generally, items should be marked as reviewed rather than deleted to maintain audit trail.
    """
    queue_manager = ReviewQueueManager(db=db)

    item = queue_manager.get_item_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Review item {item_id} not found")

    db.delete(item)
    db.commit()

    return {"success": True, "message": f"Review item {item_id} deleted"}
