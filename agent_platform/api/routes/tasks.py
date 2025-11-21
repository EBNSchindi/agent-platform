"""
Tasks API Routes
CRUD operations for Task memory-objects.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent_platform.api.dependencies import get_db_session
from agent_platform.db.models import Task
from agent_platform.memory import (
    get_task,
    get_pending_tasks,
    update_task_status,
    complete_task,
)


router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    description: str
    context: Optional[str]
    deadline: Optional[datetime]
    priority: str
    status: str
    assignee: Optional[str]
    requires_action_from_me: bool
    email_subject: Optional[str]
    email_sender: Optional[str]
    email_received_at: Optional[datetime]
    completed_at: Optional[datetime]
    completion_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskUpdateRequest(BaseModel):
    """Request to update task."""
    status: Optional[str] = None
    priority: Optional[str] = None
    completion_notes: Optional[str] = None


class TasksListResponse(BaseModel):
    """Paginated tasks list."""
    items: List[TaskResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/tasks", response_model=TasksListResponse)
def list_tasks(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """
    List tasks with optional filtering.

    Query Parameters:
        - limit: Max results (default: 20)
        - offset: Pagination offset
        - account_id: Filter by account
        - status: Filter by status (pending/in_progress/completed/cancelled/waiting)
        - priority: Filter by priority (low/medium/high/urgent)
    """
    query = db.query(Task)

    # Apply filters
    if account_id:
        query = query.filter(Task.account_id == account_id)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)

    # Get total count
    total = query.count()

    # Get items
    items = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()

    return TasksListResponse(
        items=[TaskResponse.from_orm(task) for task in items],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_detail(task_id: str, db: Session = Depends(get_db_session)):
    """Get single task by ID."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task_endpoint(
    task_id: str,
    request: TaskUpdateRequest,
    db: Session = Depends(get_db_session),
):
    """
    Update task status, priority, or other fields.

    Args:
        task_id: Task ID
        request: Fields to update (status, priority, completion_notes)
    """
    from agent_platform.memory import update_task

    # Check if task exists
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task with all provided fields
    updated_task = update_task(
        task_id=task_id,
        status=request.status,
        priority=request.priority,
        completion_notes=request.completion_notes
    )

    return TaskResponse.from_orm(updated_task)


@router.post("/tasks/{task_id}/complete")
def complete_task_endpoint(
    task_id: str,
    completion_notes: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    Mark task as completed.

    Args:
        task_id: Task ID
        completion_notes: Optional notes about completion
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    complete_task(task_id, completion_notes=completion_notes)

    return {
        "success": True,
        "message": "Task completed",
        "task_id": task_id
    }
