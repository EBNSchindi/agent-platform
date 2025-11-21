"""
Tests for Email Agent API Routes
Tests Email-Agent status monitoring, run management, and HITL (Human-In-The-Loop) actions.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from agent_platform.api.main import app
from agent_platform.db.models import ProcessedEmail, Task, Decision, Question
from agent_platform.db.database import get_db
from agent_platform.events import get_events, EventType


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
        db.query(ProcessedEmail).delete()
        db.query(Task).delete()
        db.query(Decision).delete()
        db.query(Question).delete()
        db.commit()
    yield
    with get_db() as db:
        db.query(ProcessedEmail).delete()
        db.query(Task).delete()
        db.query(Decision).delete()
        db.query(Question).delete()
        db.commit()


@pytest.fixture
def sample_email_runs():
    """Create sample email runs (processed emails)"""
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)

    with get_db() as db:
        emails = [
            # High confidence - doesn't need human
            ProcessedEmail(
                email_id="email_001",
                account_id="gmail_1",
                subject="Weekly Newsletter",
                sender="newsletter@company.com",
                received_at=today - timedelta(hours=2),
                category="newsletter",
                confidence=0.95,
                importance_score=0.30,
                processed_at=today - timedelta(hours=2),
            ),
            # Medium confidence - needs human review
            ProcessedEmail(
                email_id="email_002",
                account_id="gmail_1",
                subject="Project Update - Action Required",
                sender="manager@company.com",
                received_at=today - timedelta(hours=1),
                category="wichtig",
                confidence=0.75,
                importance_score=0.80,
                processed_at=today - timedelta(hours=1),
            ),
            # Low confidence - needs human review
            ProcessedEmail(
                email_id="email_003",
                account_id="gmail_1",
                subject="Unclear Email Subject",
                sender="unknown@example.com",
                received_at=today - timedelta(minutes=30),
                category="unwichtig",
                confidence=0.55,
                importance_score=0.40,
                processed_at=today - timedelta(minutes=30),
            ),
            # Yesterday's email
            ProcessedEmail(
                email_id="email_004",
                account_id="gmail_2",
                subject="Yesterday's Email",
                sender="colleague@company.com",
                received_at=yesterday,
                category="wichtig",
                confidence=0.88,
                importance_score=0.75,
                processed_at=yesterday,
            ),
        ]
        for email in emails:
            db.add(email)
        db.commit()
    yield
    with get_db() as db:
        db.query(ProcessedEmail).delete()
        db.commit()


@pytest.fixture
def sample_run_with_extractions():
    """Create email run with extracted tasks, decisions, questions"""
    today = datetime.utcnow()

    with get_db() as db:
        # Email
        email = ProcessedEmail(
            email_id="email_with_extractions",
            account_id="gmail_1",
            subject="Meeting Request with Tasks",
            sender="boss@company.com",
            received_at=today,
            category="wichtig",
            confidence=0.85,
            importance_score=0.90,
            processed_at=today,
        )
        db.add(email)

        # Task
        task = Task(
            task_id="task_001",
            account_id="gmail_1",
            email_id="email_with_extractions",
            description="Prepare presentation for Friday",
            priority="high",
            status="pending",
            deadline=today + timedelta(days=2),
            created_at=today,
        )
        db.add(task)

        # Decision
        decision = Decision(
            decision_id="decision_001",
            account_id="gmail_1",
            email_id="email_with_extractions",
            question="Approve the budget increase?",
            options=["Yes", "No", "Defer"],
            status="pending",
            created_at=today,
        )
        db.add(decision)

        # Question
        question = Question(
            question_id="question_001",
            account_id="gmail_1",
            email_id="email_with_extractions",
            question="What time should we meet?",
            status="pending",
            created_at=today,
        )
        db.add(question)

        db.commit()
    yield
    with get_db() as db:
        db.query(ProcessedEmail).delete()
        db.query(Task).delete()
        db.query(Decision).delete()
        db.query(Question).delete()
        db.commit()


# ============================================================================
# Test: Get Email-Agent Status
# ============================================================================

def test_get_email_agent_status_success(client, clean_database, sample_email_runs):
    """Test getting Email-Agent status with sample data"""
    response = client.get("/api/v1/email-agent/status")

    assert response.status_code == 200
    data = response.json()

    assert "active" in data
    assert "emails_processed_today" in data
    assert "pending_runs" in data
    assert "last_run" in data

    assert data["active"] is True
    assert data["emails_processed_today"] >= 3  # 3 emails today
    assert data["pending_runs"] >= 2  # 2 emails with confidence < 0.90


def test_get_email_agent_status_counts_correct(client, clean_database, sample_email_runs):
    """Test that status counts are accurate"""
    response = client.get("/api/v1/email-agent/status")
    data = response.json()

    # Should have 3 emails processed today (email_001, email_002, email_003)
    assert data["emails_processed_today"] == 3

    # Should have 2 pending runs (email_002: 0.75, email_003: 0.55)
    # (confidence < 0.90 threshold)
    assert data["pending_runs"] == 2


def test_get_email_agent_status_last_run(client, clean_database, sample_email_runs):
    """Test that last_run timestamp is correct"""
    response = client.get("/api/v1/email-agent/status")
    data = response.json()

    assert data["last_run"] is not None

    # Last run should be email_003 (most recent - 30 minutes ago)
    last_run_time = datetime.fromisoformat(data["last_run"].replace('Z', '+00:00'))
    now = datetime.now(last_run_time.tzinfo)

    # Should be within last 2 hours (sample data creates emails up to 2 hours ago)
    time_diff = (now - last_run_time).total_seconds()
    assert time_diff < 7200  # Less than 2 hours


def test_get_email_agent_status_empty_database(client, clean_database):
    """Test status with empty database"""
    response = client.get("/api/v1/email-agent/status")

    assert response.status_code == 200
    data = response.json()

    assert data["active"] is True
    assert data["emails_processed_today"] == 0
    assert data["pending_runs"] == 0
    assert data["last_run"] is None


# ============================================================================
# Test: List Email-Agent Runs
# ============================================================================

def test_list_email_agent_runs_default(client, clean_database, sample_email_runs):
    """Test listing runs with default parameters"""
    response = client.get("/api/v1/email-agent/runs")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert data["limit"] == 20  # Default limit
    assert data["offset"] == 0
    assert data["total"] >= 4  # At least 4 emails


def test_list_email_agent_runs_ordered_by_time(client, clean_database, sample_email_runs):
    """Test that runs are ordered by processed_at descending"""
    response = client.get("/api/v1/email-agent/runs")
    data = response.json()

    items = data["items"]
    assert len(items) >= 2

    # First item should be most recent
    first_time = datetime.fromisoformat(items[0]["created_at"].replace('Z', '+00:00'))
    second_time = datetime.fromisoformat(items[1]["created_at"].replace('Z', '+00:00'))

    assert first_time >= second_time


def test_list_email_agent_runs_filter_by_account(client, clean_database, sample_email_runs):
    """Test filtering by account_id"""
    response = client.get("/api/v1/email-agent/runs?account_id=gmail_1")

    assert response.status_code == 200
    data = response.json()

    # Should only have gmail_1 emails
    assert all(item["email_id"].startswith("email_00") for item in data["items"])
    assert data["total"] == 3  # email_001, email_002, email_003


def test_list_email_agent_runs_filter_needs_human_true(client, clean_database, sample_email_runs):
    """Test filtering by needs_human=true (confidence < 0.90)"""
    response = client.get("/api/v1/email-agent/runs?needs_human=true")

    assert response.status_code == 200
    data = response.json()

    # Should only have medium/low confidence emails
    for item in data["items"]:
        assert item["needs_human"] is True
        assert item["confidence"] < 0.90

    # email_002 (0.75), email_003 (0.55), email_004 (0.88)
    assert data["total"] == 3


def test_list_email_agent_runs_filter_needs_human_false(client, clean_database, sample_email_runs):
    """Test filtering by needs_human=false (confidence >= 0.90)"""
    response = client.get("/api/v1/email-agent/runs?needs_human=false")

    assert response.status_code == 200
    data = response.json()

    # Should only have high confidence emails
    for item in data["items"]:
        assert item["needs_human"] is False
        assert item["confidence"] >= 0.90

    # Only email_001 (0.95) has confidence >= 0.90
    # email_004 (0.88) is < 0.90, so it needs human review
    assert data["total"] == 1


def test_list_email_agent_runs_pagination(client, clean_database, sample_email_runs):
    """Test pagination parameters"""
    response = client.get("/api/v1/email-agent/runs?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()

    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2


def test_list_email_agent_runs_item_structure(client, clean_database, sample_email_runs):
    """Test that run list items have correct structure"""
    response = client.get("/api/v1/email-agent/runs")
    data = response.json()

    if len(data["items"]) > 0:
        item = data["items"][0]

        required_fields = [
            "run_id", "email_id", "email_subject", "email_sender",
            "email_received_at", "category", "confidence",
            "needs_human", "status", "created_at"
        ]

        for field in required_fields:
            assert field in item, f"Missing field: {field}"


# ============================================================================
# Test: Get Run Detail
# ============================================================================

def test_get_run_detail_success(client, clean_database, sample_run_with_extractions):
    """Test getting detailed run information"""
    response = client.get("/api/v1/email-agent/runs/email_with_extractions")

    assert response.status_code == 200
    data = response.json()

    assert data["run_id"] == "email_with_extractions"
    assert data["email_subject"] == "Meeting Request with Tasks"
    assert data["category"] == "wichtig"
    assert data["confidence"] == 0.85


def test_get_run_detail_includes_extractions(client, clean_database, sample_run_with_extractions):
    """Test that run detail includes extracted memory-objects"""
    response = client.get("/api/v1/email-agent/runs/email_with_extractions")
    data = response.json()

    # Should have extracted tasks
    assert "tasks" in data
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["description"] == "Prepare presentation for Friday"

    # Should have extracted decisions
    assert "decisions" in data
    assert len(data["decisions"]) == 1
    assert data["decisions"][0]["question"] == "Approve the budget increase?"

    # Should have extracted questions
    assert "questions" in data
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "What time should we meet?"


def test_get_run_detail_all_fields(client, clean_database, sample_run_with_extractions):
    """Test that run detail has all required fields"""
    response = client.get("/api/v1/email-agent/runs/email_with_extractions")
    data = response.json()

    required_fields = [
        "run_id", "email_id", "email_subject", "email_sender",
        "email_received_at", "category", "confidence", "importance_score",
        "draft_reply", "needs_human", "status", "tasks", "decisions",
        "questions", "created_at"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing"


def test_get_run_detail_not_found(client, clean_database):
    """Test getting detail for nonexistent run"""
    response = client.get("/api/v1/email-agent/runs/nonexistent_email")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Test: Accept Run
# ============================================================================

def test_accept_run_success(client, clean_database, sample_email_runs):
    """Test accepting a run"""
    response = client.post(
        "/api/v1/email-agent/runs/email_002/accept",
        json={"feedback": "Classification looks correct"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "accepted" in data["message"].lower()
    assert data["run_id"] == "email_002"


def test_accept_run_logs_event(client, clean_database, sample_email_runs):
    """Test that accepting logs USER_CONFIRMATION event"""
    # Accept run
    client.post(
        "/api/v1/email-agent/runs/email_002/accept",
        json={"feedback": "Good classification"}
    )

    # Verify event was logged
    events = get_events(
        event_type=EventType.USER_CONFIRMATION,
        email_id="email_002",
        limit=1
    )

    assert len(events) > 0
    event = events[0]
    assert event.payload["action"] == "accept"
    assert event.payload["feedback"] == "Good classification"


def test_accept_run_without_feedback(client, clean_database, sample_email_runs):
    """Test accepting without feedback"""
    response = client.post(
        "/api/v1/email-agent/runs/email_002/accept",
        json={}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_accept_run_not_found(client, clean_database):
    """Test accepting nonexistent run"""
    response = client.post(
        "/api/v1/email-agent/runs/nonexistent_email/accept",
        json={}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Test: Reject Run
# ============================================================================

def test_reject_run_success(client, clean_database, sample_email_runs):
    """Test rejecting a run"""
    response = client.post(
        "/api/v1/email-agent/runs/email_002/reject",
        json={"feedback": "Wrong category - should be unwichtig"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "rejected" in data["message"].lower()
    assert data["run_id"] == "email_002"


def test_reject_run_logs_event(client, clean_database, sample_email_runs):
    """Test that rejecting logs USER_CORRECTION event"""
    # Reject run
    client.post(
        "/api/v1/email-agent/runs/email_002/reject",
        json={"feedback": "Incorrect classification"}
    )

    # Verify event was logged
    events = get_events(
        event_type=EventType.USER_CORRECTION,
        email_id="email_002",
        limit=1
    )

    assert len(events) > 0
    event = events[0]
    assert event.payload["action"] == "reject"
    assert event.payload["reason"] == "Incorrect classification"
    assert event.payload["original_category"] == "wichtig"


def test_reject_run_not_found(client, clean_database):
    """Test rejecting nonexistent run"""
    response = client.post(
        "/api/v1/email-agent/runs/nonexistent_email/reject",
        json={"feedback": "Wrong"}
    )

    assert response.status_code == 404


# ============================================================================
# Test: Edit Run
# ============================================================================

def test_edit_run_success(client, clean_database, sample_email_runs):
    """Test editing a run"""
    response = client.post(
        "/api/v1/email-agent/runs/email_002/edit",
        json={
            "updated_draft": "Dear Manager, I have reviewed the project update...",
            "feedback": "Improved tone and clarity"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "updated" in data["message"].lower()
    assert data["run_id"] == "email_002"


def test_edit_run_logs_event(client, clean_database, sample_email_runs):
    """Test that editing logs USER_CORRECTION event"""
    # Edit run
    client.post(
        "/api/v1/email-agent/runs/email_002/edit",
        json={
            "updated_draft": "New draft content",
            "feedback": "Changed tone"
        }
    )

    # Verify event was logged
    events = get_events(
        event_type=EventType.USER_CORRECTION,
        email_id="email_002",
        limit=1
    )

    assert len(events) > 0
    event = events[0]
    assert event.payload["action"] == "edit"
    assert event.payload["updated_draft"] == "New draft content"
    assert event.payload["feedback"] == "Changed tone"


def test_edit_run_missing_fields(client, clean_database, sample_email_runs):
    """Test editing without required fields"""
    response = client.post(
        "/api/v1/email-agent/runs/email_002/edit",
        json={"updated_draft": "New draft"}  # Missing feedback
    )

    assert response.status_code == 422  # Validation error


def test_edit_run_not_found(client, clean_database):
    """Test editing nonexistent run"""
    response = client.post(
        "/api/v1/email-agent/runs/nonexistent_email/edit",
        json={"updated_draft": "New draft", "feedback": "Test"}
    )

    assert response.status_code == 404


# ============================================================================
# Test: Trigger Test Run
# ============================================================================

def test_trigger_test_run_success(client, clean_database):
    """Test triggering a test run"""
    response = client.post("/api/v1/email-agent/trigger-test")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "triggered" in data["message"].lower()


def test_trigger_test_run_returns_pending_note(client, clean_database):
    """Test that test run returns pending implementation note"""
    response = client.post("/api/v1/email-agent/trigger-test")
    data = response.json()

    assert "note" in data
    assert "pending" in data["note"].lower()


# ============================================================================
# Test: Response Models
# ============================================================================

def test_email_agent_status_response_structure(client, clean_database, sample_email_runs):
    """Test that EmailAgentStatus response has correct structure"""
    response = client.get("/api/v1/email-agent/status")
    data = response.json()

    assert isinstance(data["active"], bool)
    assert isinstance(data["emails_processed_today"], int)
    assert isinstance(data["pending_runs"], int)
    # last_run can be None or datetime string


def test_runs_list_response_structure(client, clean_database, sample_email_runs):
    """Test that RunsListResponse has correct structure"""
    response = client.get("/api/v1/email-agent/runs")
    data = response.json()

    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["limit"], int)
    assert isinstance(data["offset"], int)


def test_run_detail_response_structure(client, clean_database, sample_run_with_extractions):
    """Test that RunDetail response has correct structure"""
    response = client.get("/api/v1/email-agent/runs/email_with_extractions")
    data = response.json()

    assert isinstance(data["tasks"], list)
    assert isinstance(data["decisions"], list)
    assert isinstance(data["questions"], list)
    assert isinstance(data["needs_human"], bool)
    assert isinstance(data["confidence"], float)


# ============================================================================
# Test: Business Logic
# ============================================================================

def test_needs_human_flag_logic(client, clean_database, sample_email_runs):
    """Test that needs_human flag is set correctly based on confidence"""
    response = client.get("/api/v1/email-agent/runs")
    data = response.json()

    for item in data["items"]:
        if item["confidence"] >= 0.90:
            assert item["needs_human"] is False
        else:
            assert item["needs_human"] is True


def test_status_inference_from_confidence(client, clean_database, sample_email_runs):
    """Test that status is inferred from confidence"""
    response = client.get("/api/v1/email-agent/runs")
    data = response.json()

    for item in data["items"]:
        if item["confidence"] >= 0.90:
            assert item["status"] == "accepted"
        else:
            assert item["status"] == "pending"


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: Email Agent API Routes

Endpoints Tested:
- GET /api/v1/email-agent/status (agent status)
- GET /api/v1/email-agent/runs (list runs with filtering & pagination)
- GET /api/v1/email-agent/runs/{run_id} (run detail with extractions)
- POST /api/v1/email-agent/runs/{run_id}/accept (accept classification)
- POST /api/v1/email-agent/runs/{run_id}/reject (reject classification)
- POST /api/v1/email-agent/runs/{run_id}/edit (edit draft)
- POST /api/v1/email-agent/trigger-test (trigger test run)

Test Categories:
- Agent status (4 tests)
- List runs (7 tests)
- Run detail (4 tests)
- Accept run (4 tests)
- Reject run (3 tests)
- Edit run (4 tests)
- Trigger test (2 tests)
- Response models (3 tests)
- Business logic (2 tests)

Total Tests: 33 tests

Coverage: Comprehensive coverage of all Email-Agent HITL operations with:
- Status monitoring and pending run tracking
- Run list filtering (account_id, needs_human)
- Detailed run information with extracted memory-objects
- User actions (accept, reject, edit) with event logging
- Response model validation
- Business logic for needs_human and status inference
"""
