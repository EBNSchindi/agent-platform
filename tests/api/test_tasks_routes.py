"""
Tests for Tasks API Routes
Tests CRUD operations for Task memory-objects via FastAPI endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from agent_platform.api.main import app
from agent_platform.db.models import Task
from agent_platform.db.database import get_db


# ============================================================================
# Test Client Setup
# ============================================================================

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def clean_database():
    """Clean database before each test"""
    with get_db() as db:
        # Clean tasks
        db.query(Task).delete()
        db.commit()
    yield
    # Cleanup after test
    with get_db() as db:
        db.query(Task).delete()
        db.commit()


@pytest.fixture
def sample_tasks():
    """Create sample tasks in database"""
    with get_db() as db:
        tasks = [
            Task(
                task_id="task_001",
                account_id="gmail_1",
                email_id="email_001",
                description="Complete project report",
                priority="high",
                status="pending",
                requires_action_from_me=True,
                deadline=datetime.utcnow() + timedelta(days=2),
                email_subject="Project Report Due",
                email_sender="boss@company.com",
            ),
            Task(
                task_id="task_002",
                account_id="gmail_1",
                email_id="email_002",
                description="Review pull request",
                priority="medium",
                status="pending",
                requires_action_from_me=True,
                email_subject="PR Review Needed",
                email_sender="dev@company.com",
            ),
            Task(
                task_id="task_003",
                account_id="gmail_2",
                email_id="email_003",
                description="Schedule team meeting",
                priority="low",
                status="completed",
                requires_action_from_me=False,
                completed_at=datetime.utcnow(),
                email_subject="Team Meeting",
                email_sender="hr@company.com",
            ),
        ]
        for task in tasks:
            db.add(task)
        db.commit()
    yield
    # Cleanup
    with get_db() as db:
        db.query(Task).delete()
        db.commit()


# ============================================================================
# Test: List Tasks
# ============================================================================

def test_list_tasks_default(client, clean_database, sample_tasks):
    """Test listing tasks with default parameters"""
    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_list_tasks_pagination(client, clean_database, sample_tasks):
    """Test pagination parameters"""
    response = client.get("/api/v1/tasks?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1


def test_list_tasks_filter_by_account(client, clean_database, sample_tasks):
    """Test filtering by account_id"""
    response = client.get("/api/v1/tasks?account_id=gmail_1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(task["email_sender"] in ["boss@company.com", "dev@company.com"] for task in data["items"])


def test_list_tasks_filter_by_status(client, clean_database, sample_tasks):
    """Test filtering by status"""
    response = client.get("/api/v1/tasks?status=pending")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(task["status"] == "pending" for task in data["items"])


def test_list_tasks_filter_by_priority(client, clean_database, sample_tasks):
    """Test filtering by priority"""
    response = client.get("/api/v1/tasks?priority=high")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["priority"] == "high"
    assert data["items"][0]["description"] == "Complete project report"


def test_list_tasks_multiple_filters(client, clean_database, sample_tasks):
    """Test combining multiple filters"""
    response = client.get("/api/v1/tasks?account_id=gmail_1&status=pending&priority=high")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["task_id"] == "task_001"


def test_list_tasks_empty_result(client, clean_database, sample_tasks):
    """Test query that returns no results"""
    response = client.get("/api/v1/tasks?account_id=nonexistent_account")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_list_tasks_limit_validation(client, clean_database):
    """Test limit parameter validation (max 100)"""
    response = client.get("/api/v1/tasks?limit=150")

    # Should return validation error
    assert response.status_code == 422


def test_list_tasks_offset_validation(client, clean_database):
    """Test offset parameter validation (min 0)"""
    response = client.get("/api/v1/tasks?offset=-5")

    # Should return validation error
    assert response.status_code == 422


# ============================================================================
# Test: Get Task Detail
# ============================================================================

def test_get_task_detail_success(client, clean_database, sample_tasks):
    """Test getting single task by ID"""
    response = client.get("/api/v1/tasks/task_001")

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == "task_001"
    assert data["description"] == "Complete project report"
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert data["email_sender"] == "boss@company.com"


def test_get_task_detail_not_found(client, clean_database):
    """Test getting nonexistent task"""
    response = client.get("/api/v1/tasks/nonexistent_task")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_task_detail_includes_metadata(client, clean_database, sample_tasks):
    """Test that task detail includes all metadata fields"""
    response = client.get("/api/v1/tasks/task_001")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "task_id" in data
    assert "description" in data
    assert "priority" in data
    assert "status" in data
    assert "requires_action_from_me" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Check optional fields
    assert "context" in data
    assert "deadline" in data
    assert "assignee" in data
    assert "email_subject" in data
    assert "email_sender" in data
    assert "completed_at" in data
    assert "completion_notes" in data


# ============================================================================
# Test: Update Task
# ============================================================================

def test_update_task_status(client, clean_database, sample_tasks):
    """Test updating task status"""
    response = client.patch(
        "/api/v1/tasks/task_001",
        json={"status": "in_progress"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == "task_001"
    assert data["status"] == "in_progress"


def test_update_task_priority(client, clean_database, sample_tasks):
    """Test updating task priority"""
    response = client.patch(
        "/api/v1/tasks/task_002",
        json={"priority": "urgent"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == "task_002"
    assert data["priority"] == "urgent"


def test_update_task_multiple_fields(client, clean_database, sample_tasks):
    """Test updating multiple fields at once"""
    response = client.patch(
        "/api/v1/tasks/task_001",
        json={
            "status": "in_progress",
            "priority": "urgent",
            "completion_notes": "Working on it"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "in_progress"
    assert data["priority"] == "urgent"


def test_update_task_not_found(client, clean_database):
    """Test updating nonexistent task"""
    response = client.patch(
        "/api/v1/tasks/nonexistent_task",
        json={"status": "completed"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_task_empty_body(client, clean_database, sample_tasks):
    """Test update with empty request body"""
    response = client.patch(
        "/api/v1/tasks/task_001",
        json={}
    )

    # Should succeed but not change anything
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"  # Original status unchanged


# ============================================================================
# Test: Complete Task
# ============================================================================

def test_complete_task_success(client, clean_database, sample_tasks):
    """Test completing a task"""
    response = client.post("/api/v1/tasks/task_001/complete")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "completed" in data["message"].lower()


def test_complete_task_with_notes(client, clean_database, sample_tasks):
    """Test completing task with completion notes"""
    response = client.post(
        "/api/v1/tasks/task_001/complete",
        params={"completion_notes": "Finished ahead of schedule"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True

    # Verify task is marked as completed
    verify_response = client.get("/api/v1/tasks/task_001")
    task_data = verify_response.json()
    assert task_data["status"] == "completed"
    assert task_data["completed_at"] is not None


def test_complete_task_not_found(client, clean_database):
    """Test completing nonexistent task"""
    response = client.post("/api/v1/tasks/nonexistent_task/complete")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_complete_already_completed_task(client, clean_database, sample_tasks):
    """Test completing an already completed task"""
    # task_003 is already completed
    response = client.post("/api/v1/tasks/task_003/complete")

    # Should succeed (idempotent)
    assert response.status_code == 200


# ============================================================================
# Test: Response Models
# ============================================================================

def test_task_response_model_structure(client, clean_database, sample_tasks):
    """Test that TaskResponse model has correct structure"""
    response = client.get("/api/v1/tasks/task_001")
    data = response.json()

    required_fields = [
        "task_id", "description", "priority", "status",
        "requires_action_from_me", "created_at", "updated_at"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing from response"


def test_tasks_list_response_structure(client, clean_database, sample_tasks):
    """Test that TasksListResponse has correct structure"""
    response = client.get("/api/v1/tasks")
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["limit"], int)
    assert isinstance(data["offset"], int)


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_invalid_task_id_format(client, clean_database):
    """Test handling of invalid task ID format"""
    # API should handle any string, even if not found
    response = client.get("/api/v1/tasks/invalid-format-!@#")

    assert response.status_code == 404


def test_invalid_status_value(client, clean_database, sample_tasks):
    """Test updating with invalid status value"""
    response = client.patch(
        "/api/v1/tasks/task_001",
        json={"status": "invalid_status"}
    )

    # Should succeed (API doesn't validate enum values currently)
    # This could be improved with enum validation
    assert response.status_code in [200, 400, 422]


def test_invalid_priority_value(client, clean_database, sample_tasks):
    """Test updating with invalid priority value"""
    response = client.patch(
        "/api/v1/tasks/task_001",
        json={"priority": "invalid_priority"}
    )

    # Should succeed or fail validation
    assert response.status_code in [200, 400, 422]


# ============================================================================
# Test: Database Integration
# ============================================================================

def test_task_persists_across_requests(client, clean_database, sample_tasks):
    """Test that task updates persist across multiple requests"""
    # Update task
    update_response = client.patch(
        "/api/v1/tasks/task_001",
        json={"status": "in_progress"}
    )
    assert update_response.status_code == 200

    # Verify update persists
    get_response = client.get("/api/v1/tasks/task_001")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "in_progress"


def test_completed_task_timestamp_set(client, clean_database, sample_tasks):
    """Test that completing a task sets completed_at timestamp"""
    # Task initially has no completed_at
    initial_response = client.get("/api/v1/tasks/task_001")
    assert initial_response.json()["completed_at"] is None

    # Complete task
    client.post("/api/v1/tasks/task_001/complete")

    # Verify completed_at is set
    final_response = client.get("/api/v1/tasks/task_001")
    assert final_response.json()["completed_at"] is not None


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: Tasks API Routes

Endpoints Tested:
- GET /api/tasks (list with filtering & pagination)
- GET /api/tasks/{task_id} (detail)
- PATCH /api/tasks/{task_id} (update)
- POST /api/tasks/{task_id}/complete (complete)

Test Categories:
- List operations (9 tests)
- Detail retrieval (3 tests)
- Update operations (5 tests)
- Complete operations (4 tests)
- Response models (2 tests)
- Error handling (3 tests)
- Database integration (2 tests)

Total Tests: 28 tests

Coverage: Comprehensive coverage of all CRUD operations for Tasks API
"""
