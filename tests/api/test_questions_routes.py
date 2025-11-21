"""
Tests for Questions API Routes
Tests CRUD operations for Question memory-objects via FastAPI endpoints.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from agent_platform.api.main import app
from agent_platform.db.models import Question
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
        db.query(Question).delete()
        db.commit()
    yield
    with get_db() as db:
        db.query(Question).delete()
        db.commit()


@pytest.fixture
def sample_questions():
    """Create sample questions in database"""
    with get_db() as db:
        questions = [
            Question(
                question_id="question_001",
                account_id="gmail_1",
                email_id="email_001",
                question="What is the deadline for the project?",
                context="Project planning discussion",
                question_type="clarification",
                requires_response=True,
                urgency="high",
                status="pending",
                email_subject="Project Timeline",
                email_sender="pm@company.com",
            ),
            Question(
                question_id="question_002",
                account_id="gmail_1",
                email_id="email_002",
                question="Can you review the attached document?",
                context="Document review request",
                question_type="action",
                requires_response=True,
                urgency="medium",
                status="pending",
                email_subject="Document Review",
                email_sender="colleague@company.com",
            ),
            Question(
                question_id="question_003",
                account_id="gmail_2",
                email_id="email_003",
                question="What do you think about the proposal?",
                context="Opinion request",
                question_type="opinion",
                requires_response=False,
                urgency="low",
                status="answered",
                answer="I think it looks good",
                answered_at=datetime.utcnow(),
                email_subject="Proposal Feedback",
                email_sender="partner@company.com",
            ),
        ]
        for question in questions:
            db.add(question)
        db.commit()
    yield
    with get_db() as db:
        db.query(Question).delete()
        db.commit()


# ============================================================================
# Test: List Questions
# ============================================================================

def test_list_questions_default(client, clean_database, sample_questions):
    """Test listing questions with default parameters"""
    response = client.get("/api/v1/questions")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_questions_pagination(client, clean_database, sample_questions):
    """Test pagination parameters"""
    response = client.get("/api/v1/questions?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2


def test_list_questions_filter_by_account(client, clean_database, sample_questions):
    """Test filtering by account_id"""
    response = client.get("/api/v1/questions?account_id=gmail_1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert all(q["email_sender"] in ["pm@company.com", "colleague@company.com"] for q in data["items"])


def test_list_questions_filter_by_status(client, clean_database, sample_questions):
    """Test filtering by status"""
    response = client.get("/api/v1/questions?status=pending")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert all(q["status"] == "pending" for q in data["items"])


def test_list_questions_filter_by_requires_response(client, clean_database, sample_questions):
    """Test filtering by requires_response flag"""
    response = client.get("/api/v1/questions?requires_response=true")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert all(q["requires_response"] is True for q in data["items"])


def test_list_questions_multiple_filters(client, clean_database, sample_questions):
    """Test combining multiple filters"""
    response = client.get("/api/v1/questions?account_id=gmail_1&status=pending&requires_response=true")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2


def test_list_questions_empty_result(client, clean_database, sample_questions):
    """Test query that returns no results"""
    response = client.get("/api/v1/questions?account_id=nonexistent_account")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_list_questions_limit_validation(client, clean_database):
    """Test limit parameter validation (max 100)"""
    response = client.get("/api/v1/questions?limit=150")

    assert response.status_code == 422


def test_list_questions_offset_validation(client, clean_database):
    """Test offset parameter validation (min 0)"""
    response = client.get("/api/v1/questions?offset=-5")

    assert response.status_code == 422


# ============================================================================
# Test: Get Question Detail
# ============================================================================

def test_get_question_detail_success(client, clean_database, sample_questions):
    """Test getting single question by ID"""
    response = client.get("/api/v1/questions/question_001")

    assert response.status_code == 200
    data = response.json()

    assert data["question_id"] == "question_001"
    assert data["question"] == "What is the deadline for the project?"
    assert data["question_type"] == "clarification"
    assert data["urgency"] == "high"
    assert data["status"] == "pending"
    assert data["email_sender"] == "pm@company.com"


def test_get_question_detail_not_found(client, clean_database):
    """Test getting nonexistent question"""
    response = client.get("/api/v1/questions/nonexistent_question")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_question_detail_includes_metadata(client, clean_database, sample_questions):
    """Test that question detail includes all metadata fields"""
    response = client.get("/api/v1/questions/question_001")

    assert response.status_code == 200
    data = response.json()

    required_fields = [
        "question_id", "question", "question_type", "requires_response",
        "urgency", "status", "created_at", "updated_at"
    ]
    for field in required_fields:
        assert field in data

    # Check optional fields
    assert "context" in data
    assert "answer" in data
    assert "answered_at" in data
    assert "email_subject" in data
    assert "email_sender" in data


# ============================================================================
# Test: Answer Question
# ============================================================================

def test_answer_question_success(client, clean_database, sample_questions):
    """Test answering a question"""
    response = client.post(
        "/api/v1/questions/question_001/answer",
        json={"answer": "The deadline is next Friday"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "answered" in data["message"].lower()
    assert data["question_id"] == "question_001"


def test_answer_question_not_found(client, clean_database):
    """Test answering nonexistent question"""
    response = client.post(
        "/api/v1/questions/nonexistent_question/answer",
        json={"answer": "Some answer"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_answer_question_updates_status(client, clean_database, sample_questions):
    """Test that answering question updates status to 'answered'"""
    # Answer question
    client.post(
        "/api/v1/questions/question_001/answer",
        json={"answer": "Next Friday"}
    )

    # Verify status updated
    response = client.get("/api/v1/questions/question_001")
    data = response.json()

    assert data["status"] == "answered"
    assert data["answer"] == "Next Friday"
    assert data["answered_at"] is not None


def test_answer_already_answered_question(client, clean_database, sample_questions):
    """Test answering already answered question (idempotent)"""
    # question_003 is already answered
    response = client.post(
        "/api/v1/questions/question_003/answer",
        json={"answer": "Updated answer"}
    )

    # Should succeed (idempotent)
    assert response.status_code == 200


# ============================================================================
# Test: Response Models
# ============================================================================

def test_question_response_model_structure(client, clean_database, sample_questions):
    """Test that QuestionResponse model has correct structure"""
    response = client.get("/api/v1/questions/question_001")
    data = response.json()

    required_fields = [
        "question_id", "question", "question_type", "requires_response",
        "urgency", "status", "created_at", "updated_at"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing from response"


def test_questions_list_response_structure(client, clean_database, sample_questions):
    """Test that QuestionsListResponse has correct structure"""
    response = client.get("/api/v1/questions")
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_invalid_question_id_format(client, clean_database):
    """Test handling of invalid question ID format"""
    response = client.get("/api/v1/questions/invalid-format-!@#")

    assert response.status_code == 404


def test_answer_question_missing_answer(client, clean_database, sample_questions):
    """Test answering without required answer field"""
    response = client.post(
        "/api/v1/questions/question_001/answer",
        json={}  # Missing answer
    )

    assert response.status_code == 422  # Validation error


def test_answer_question_invalid_json(client, clean_database, sample_questions):
    """Test answering with invalid JSON"""
    response = client.post(
        "/api/v1/questions/question_001/answer",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


# ============================================================================
# Test: Database Integration
# ============================================================================

def test_question_persists_across_requests(client, clean_database, sample_questions):
    """Test that question persists across multiple requests"""
    # Answer question
    answer_response = client.post(
        "/api/v1/questions/question_001/answer",
        json={"answer": "Next Friday"}
    )
    assert answer_response.status_code == 200

    # Verify persistence
    get_response = client.get("/api/v1/questions/question_001")
    assert get_response.status_code == 200
    assert get_response.json()["answer"] == "Next Friday"
    assert get_response.json()["status"] == "answered"


def test_answered_at_timestamp_set(client, clean_database, sample_questions):
    """Test that answering sets answered_at timestamp"""
    # Question initially has no answered_at
    initial_response = client.get("/api/v1/questions/question_001")
    assert initial_response.json()["answered_at"] is None

    # Answer question
    client.post(
        "/api/v1/questions/question_001/answer",
        json={"answer": "Next Friday"}
    )

    # Verify answered_at is set
    final_response = client.get("/api/v1/questions/question_001")
    assert final_response.json()["answered_at"] is not None
    assert final_response.json()["status"] == "answered"


# ============================================================================
# Test: Business Logic
# ============================================================================

def test_pending_questions_excludes_answered(client, clean_database, sample_questions):
    """Test that filtering by status=pending excludes answered questions"""
    response = client.get("/api/v1/questions?status=pending")

    assert response.status_code == 200
    data = response.json()

    # Should only return question_001 and question_002
    assert data["total"] == 2
    question_ids = [q["question_id"] for q in data["items"]]
    assert "question_001" in question_ids
    assert "question_002" in question_ids
    assert "question_003" not in question_ids  # Answered, should be excluded


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: Questions API Routes

Endpoints Tested:
- GET /api/v1/questions (list with filtering & pagination)
- GET /api/v1/questions/{question_id} (detail)
- POST /api/v1/questions/{question_id}/answer (answer question)

Test Categories:
- List operations (9 tests)
- Detail retrieval (3 tests)
- Answer operations (4 tests)
- Response models (2 tests)
- Error handling (3 tests)
- Database integration (2 tests)
- Business logic (1 test)

Total Tests: 24 tests

Coverage: Comprehensive coverage of all CRUD operations for Questions API
"""
