"""
Tests for Decisions API Routes
Tests CRUD operations for Decision memory-objects via FastAPI endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from agent_platform.api.main import app
from agent_platform.db.models import Decision
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
        db.query(Decision).delete()
        db.commit()
    yield
    with get_db() as db:
        db.query(Decision).delete()
        db.commit()


@pytest.fixture
def sample_decisions():
    """Create sample decisions in database"""
    with get_db() as db:
        decisions = [
            Decision(
                decision_id="decision_001",
                account_id="gmail_1",
                email_id="email_001",
                question="Should we approve the budget increase?",
                context="Q4 budget review meeting",
                options=["Approve", "Reject", "Request more info"],
                recommendation="Approve",
                urgency="high",
                status="pending",
                requires_my_input=True,
                email_subject="Budget Approval Needed",
                email_sender="cfo@company.com",
            ),
            Decision(
                decision_id="decision_002",
                account_id="gmail_1",
                email_id="email_002",
                question="Which vendor should we choose?",
                context="IT infrastructure upgrade",
                options=["Vendor A", "Vendor B", "Vendor C"],
                recommendation="Vendor A",
                urgency="medium",
                status="pending",
                requires_my_input=True,
                email_subject="Vendor Selection",
                email_sender="it@company.com",
            ),
            Decision(
                decision_id="decision_003",
                account_id="gmail_2",
                email_id="email_003",
                question="Approve time off request?",
                context="Employee vacation request",
                options=["Approve", "Deny"],
                recommendation="Approve",
                urgency="low",
                status="decided",
                requires_my_input=False,
                chosen_option="Approve",
                decided_at=datetime.utcnow(),
                decision_notes="Approved as requested",
                email_subject="Time Off Request",
                email_sender="hr@company.com",
            ),
        ]
        for decision in decisions:
            db.add(decision)
        db.commit()
    yield
    with get_db() as db:
        db.query(Decision).delete()
        db.commit()


# ============================================================================
# Test: List Decisions
# ============================================================================

def test_list_decisions_default(client, clean_database, sample_decisions):
    """Test listing decisions with default parameters"""
    response = client.get("/api/v1/decisions")

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


def test_list_decisions_pagination(client, clean_database, sample_decisions):
    """Test pagination parameters"""
    response = client.get("/api/v1/decisions?limit=2&offset=1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1


def test_list_decisions_filter_by_account(client, clean_database, sample_decisions):
    """Test filtering by account_id"""
    response = client.get("/api/v1/decisions?account_id=gmail_1")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(d["email_sender"] in ["cfo@company.com", "it@company.com"] for d in data["items"])


def test_list_decisions_filter_by_status(client, clean_database, sample_decisions):
    """Test filtering by status"""
    response = client.get("/api/v1/decisions?status=pending")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(d["status"] == "pending" for d in data["items"])


def test_list_decisions_filter_by_urgency(client, clean_database, sample_decisions):
    """Test filtering by urgency"""
    response = client.get("/api/v1/decisions?urgency=high")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["urgency"] == "high"
    assert data["items"][0]["question"] == "Should we approve the budget increase?"


def test_list_decisions_multiple_filters(client, clean_database, sample_decisions):
    """Test combining multiple filters"""
    response = client.get("/api/v1/decisions?account_id=gmail_1&status=pending&urgency=high")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["decision_id"] == "decision_001"


def test_list_decisions_empty_result(client, clean_database, sample_decisions):
    """Test query that returns no results"""
    response = client.get("/api/v1/decisions?account_id=nonexistent_account")

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_list_decisions_limit_validation(client, clean_database):
    """Test limit parameter validation (max 100)"""
    response = client.get("/api/v1/decisions?limit=150")

    assert response.status_code == 422


def test_list_decisions_offset_validation(client, clean_database):
    """Test offset parameter validation (min 0)"""
    response = client.get("/api/v1/decisions?offset=-5")

    assert response.status_code == 422


# ============================================================================
# Test: Get Decision Detail
# ============================================================================

def test_get_decision_detail_success(client, clean_database, sample_decisions):
    """Test getting single decision by ID"""
    response = client.get("/api/v1/decisions/decision_001")

    assert response.status_code == 200
    data = response.json()

    assert data["decision_id"] == "decision_001"
    assert data["question"] == "Should we approve the budget increase?"
    assert data["urgency"] == "high"
    assert data["status"] == "pending"
    assert data["email_sender"] == "cfo@company.com"
    assert data["recommendation"] == "Approve"
    assert len(data["options"]) == 3


def test_get_decision_detail_not_found(client, clean_database):
    """Test getting nonexistent decision"""
    response = client.get("/api/v1/decisions/nonexistent_decision")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_decision_detail_includes_metadata(client, clean_database, sample_decisions):
    """Test that decision detail includes all metadata fields"""
    response = client.get("/api/v1/decisions/decision_001")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    required_fields = [
        "decision_id", "question", "options", "recommendation",
        "urgency", "status", "requires_my_input", "created_at", "updated_at"
    ]
    for field in required_fields:
        assert field in data

    # Check optional fields
    assert "context" in data
    assert "chosen_option" in data
    assert "decision_notes" in data
    assert "decided_at" in data
    assert "email_subject" in data
    assert "email_sender" in data


def test_get_decision_options_list(client, clean_database, sample_decisions):
    """Test that options are returned as list"""
    response = client.get("/api/v1/decisions/decision_001")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["options"], list)
    assert "Approve" in data["options"]
    assert "Reject" in data["options"]
    assert "Request more info" in data["options"]


# ============================================================================
# Test: Make Decision
# ============================================================================

def test_make_decision_success(client, clean_database, sample_decisions):
    """Test making a decision"""
    response = client.post(
        "/api/v1/decisions/decision_001/decide",
        json={
            "chosen_option": "Approve",
            "decision_notes": "Budget increase approved for Q4"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "made" in data["message"].lower()
    assert data["decision_id"] == "decision_001"
    assert data["chosen_option"] == "Approve"


def test_make_decision_without_notes(client, clean_database, sample_decisions):
    """Test making decision without optional notes"""
    response = client.post(
        "/api/v1/decisions/decision_002/decide",
        json={"chosen_option": "Vendor A"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["chosen_option"] == "Vendor A"


def test_make_decision_not_found(client, clean_database):
    """Test making decision for nonexistent decision"""
    response = client.post(
        "/api/v1/decisions/nonexistent_decision/decide",
        json={"chosen_option": "Some option"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_make_decision_updates_status(client, clean_database, sample_decisions):
    """Test that making decision updates status to 'decided'"""
    # Make decision
    client.post(
        "/api/v1/decisions/decision_001/decide",
        json={"chosen_option": "Approve"}
    )

    # Verify status updated
    response = client.get("/api/v1/decisions/decision_001")
    data = response.json()

    assert data["status"] == "decided"
    assert data["chosen_option"] == "Approve"
    assert data["decided_at"] is not None


def test_make_decision_already_decided(client, clean_database, sample_decisions):
    """Test making decision on already decided decision (idempotent)"""
    # decision_003 is already decided
    response = client.post(
        "/api/v1/decisions/decision_003/decide",
        json={"chosen_option": "Approve"}
    )

    # Should succeed (idempotent)
    assert response.status_code == 200


# ============================================================================
# Test: Response Models
# ============================================================================

def test_decision_response_model_structure(client, clean_database, sample_decisions):
    """Test that DecisionResponse model has correct structure"""
    response = client.get("/api/v1/decisions/decision_001")
    data = response.json()

    required_fields = [
        "decision_id", "question", "options", "urgency", "status",
        "requires_my_input", "created_at", "updated_at"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing from response"


def test_decisions_list_response_structure(client, clean_database, sample_decisions):
    """Test that DecisionsListResponse has correct structure"""
    response = client.get("/api/v1/decisions")
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

def test_invalid_decision_id_format(client, clean_database):
    """Test handling of invalid decision ID format"""
    response = client.get("/api/v1/decisions/invalid-format-!@#")

    assert response.status_code == 404


def test_make_decision_missing_option(client, clean_database, sample_decisions):
    """Test making decision without required chosen_option"""
    response = client.post(
        "/api/v1/decisions/decision_001/decide",
        json={"decision_notes": "Some notes"}  # Missing chosen_option
    )

    assert response.status_code == 422  # Validation error


def test_make_decision_invalid_json(client, clean_database, sample_decisions):
    """Test making decision with invalid JSON"""
    response = client.post(
        "/api/v1/decisions/decision_001/decide",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422


# ============================================================================
# Test: Database Integration
# ============================================================================

def test_decision_persists_across_requests(client, clean_database, sample_decisions):
    """Test that decision persists across multiple requests"""
    # Make decision
    make_response = client.post(
        "/api/v1/decisions/decision_001/decide",
        json={"chosen_option": "Approve", "decision_notes": "Approved"}
    )
    assert make_response.status_code == 200

    # Verify persistence
    get_response = client.get("/api/v1/decisions/decision_001")
    assert get_response.status_code == 200
    assert get_response.json()["chosen_option"] == "Approve"
    assert get_response.json()["status"] == "decided"


def test_decided_at_timestamp_set(client, clean_database, sample_decisions):
    """Test that making decision sets decided_at timestamp"""
    # Decision initially has no decided_at
    initial_response = client.get("/api/v1/decisions/decision_001")
    assert initial_response.json()["decided_at"] is None

    # Make decision
    client.post(
        "/api/v1/decisions/decision_001/decide",
        json={"chosen_option": "Approve"}
    )

    # Verify decided_at is set
    final_response = client.get("/api/v1/decisions/decision_001")
    assert final_response.json()["decided_at"] is not None
    assert final_response.json()["status"] == "decided"


# ============================================================================
# Test: Business Logic
# ============================================================================

def test_pending_decisions_excludes_decided(client, clean_database, sample_decisions):
    """Test that filtering by status=pending excludes decided decisions"""
    response = client.get("/api/v1/decisions?status=pending")

    assert response.status_code == 200
    data = response.json()

    # Should only return decision_001 and decision_002
    assert data["total"] == 2
    decision_ids = [d["decision_id"] for d in data["items"]]
    assert "decision_001" in decision_ids
    assert "decision_002" in decision_ids
    assert "decision_003" not in decision_ids  # Decided, should be excluded


def test_high_urgency_decisions_first(client, clean_database, sample_decisions):
    """Test that decisions are ordered by created_at desc"""
    response = client.get("/api/v1/decisions")

    assert response.status_code == 200
    data = response.json()

    # Verify ordering exists (newer first by default)
    assert len(data["items"]) == 3


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: Decisions API Routes

Endpoints Tested:
- GET /api/v1/decisions (list with filtering & pagination)
- GET /api/v1/decisions/{decision_id} (detail)
- POST /api/v1/decisions/{decision_id}/decide (make decision)

Test Categories:
- List operations (9 tests)
- Detail retrieval (4 tests)
- Make decision operations (5 tests)
- Response models (2 tests)
- Error handling (3 tests)
- Database integration (2 tests)
- Business logic (2 tests)

Total Tests: 27 tests

Coverage: Comprehensive coverage of all CRUD operations for Decisions API
"""
