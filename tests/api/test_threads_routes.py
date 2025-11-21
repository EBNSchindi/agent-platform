"""
Tests for Threads API Routes
Tests thread management and summarization endpoints.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from agent_platform.api.main import app
from agent_platform.db.models import ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.threads.models import ThreadSummary


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
        db.commit()
    yield
    with get_db() as db:
        db.query(ProcessedEmail).delete()
        db.commit()


@pytest.fixture
def sample_thread_emails():
    """Create sample thread emails in database"""
    with get_db() as db:
        emails = [
            ProcessedEmail(
                email_id="email_001",
                account_id="gmail_1",
                thread_id="thread_abc123",
                subject="Project Discussion",
                sender="alice@company.com",
                category="wichtig",
                received_at=datetime(2025, 11, 20, 10, 0),
                thread_position=1,
                is_thread_start=True,
            ),
            ProcessedEmail(
                email_id="email_002",
                account_id="gmail_1",
                thread_id="thread_abc123",
                subject="Re: Project Discussion",
                sender="bob@company.com",
                category="wichtig",
                received_at=datetime(2025, 11, 20, 11, 0),
                thread_position=2,
                is_thread_start=False,
            ),
            ProcessedEmail(
                email_id="email_003",
                account_id="gmail_1",
                thread_id="thread_abc123",
                subject="Re: Project Discussion",
                sender="alice@company.com",
                category="wichtig",
                received_at=datetime(2025, 11, 20, 12, 0),
                thread_position=3,
                is_thread_start=False,
            ),
        ]
        for email in emails:
            db.add(email)
        db.commit()
    yield
    with get_db() as db:
        db.query(ProcessedEmail).delete()
        db.commit()


# ============================================================================
# Test: Get Thread Emails
# ============================================================================

def test_get_thread_emails_success(client, clean_database, sample_thread_emails):
    """Test getting emails in a thread"""
    response = client.get("/api/v1/threads/thread_abc123/emails")

    assert response.status_code == 200
    data = response.json()

    assert data["thread_id"] == "thread_abc123"
    assert data["email_count"] == 3
    assert len(data["emails"]) == 3

    # Check first email
    first_email = data["emails"][0]
    assert first_email["email_id"] == "email_001"
    assert first_email["subject"] == "Project Discussion"
    assert first_email["sender"] == "alice@company.com"
    assert first_email["thread_position"] == 1
    assert first_email["is_thread_start"] is True


def test_get_thread_emails_not_found(client, clean_database):
    """Test getting emails for nonexistent thread"""
    response = client.get("/api/v1/threads/nonexistent_thread/emails")

    assert response.status_code == 404
    assert "no emails found" in response.json()["detail"].lower()


def test_get_thread_emails_with_account_filter(client, clean_database, sample_thread_emails):
    """Test that thread emails endpoint works (account_id is informational)"""
    # Note: The account_id parameter exists but thread_id is the primary identifier
    # Since all test emails are in gmail_1, this should return them all
    response = client.get("/api/v1/threads/thread_abc123/emails")

    assert response.status_code == 200
    data = response.json()

    # Should return all emails in the thread
    assert data["email_count"] == 3
    assert all(email["thread_position"] > 0 for email in data["emails"])


def test_get_thread_emails_chronological_order(client, clean_database, sample_thread_emails):
    """Test that emails are returned in chronological order"""
    response = client.get("/api/v1/threads/thread_abc123/emails")

    assert response.status_code == 200
    data = response.json()

    # Verify order by thread_position
    positions = [email["thread_position"] for email in data["emails"]]
    assert positions == [1, 2, 3]


def test_get_thread_emails_includes_metadata(client, clean_database, sample_thread_emails):
    """Test that email metadata is included"""
    response = client.get("/api/v1/threads/thread_abc123/emails")

    assert response.status_code == 200
    data = response.json()

    first_email = data["emails"][0]
    required_fields = [
        "email_id", "subject", "sender", "received_at",
        "category", "thread_position", "is_thread_start"
    ]

    for field in required_fields:
        assert field in first_email, f"Missing field: {field}"


# ============================================================================
# Test: Get Thread Summary
# ============================================================================

@patch("agent_platform.threads.thread_service.ThreadService.summarize_thread")
def test_get_thread_summary_success(mock_summarize, client, clean_database, sample_thread_emails):
    """Test getting thread summary"""
    from agent_platform.threads.models import ThreadEmail

    # Mock the summarize_thread method with all required fields
    mock_summary = ThreadSummary(
        thread_id="thread_abc123",
        account_id="gmail_1",
        subject="Project Discussion",
        summary="Discussion about project timeline and deliverables",
        key_points=["Timeline agreed", "Deliverables defined"],
        email_count=3,
        participants=["alice@company.com", "bob@company.com"],
        started_at=datetime(2025, 11, 20, 10, 0),
        last_email_at=datetime(2025, 11, 20, 12, 0),
        emails=[
            ThreadEmail(
                email_id="email_001",
                subject="Project Discussion",
                sender="alice@company.com",
                received_at=datetime(2025, 11, 20, 10, 0),
                position=1,
                is_thread_start=True,
            )
        ],
    )
    mock_summarize.return_value = mock_summary

    response = client.get("/api/v1/threads/thread_abc123/summary?account_id=gmail_1")

    assert response.status_code == 200
    data = response.json()

    assert data["thread_id"] == "thread_abc123"
    assert "summary" in data
    assert "key_points" in data
    assert data["email_count"] == 3


@patch("agent_platform.threads.thread_service.ThreadService.summarize_thread")
def test_get_thread_summary_not_found(mock_summarize, client, clean_database):
    """Test getting summary for nonexistent thread"""
    mock_summarize.side_effect = ValueError("Thread not found")

    response = client.get("/api/v1/threads/nonexistent_thread/summary?account_id=gmail_1")

    assert response.status_code == 404


@patch("agent_platform.threads.thread_service.ThreadService.summarize_thread")
def test_get_thread_summary_force_regenerate(mock_summarize, client, clean_database, sample_thread_emails):
    """Test forcing regeneration of thread summary"""
    from agent_platform.threads.models import ThreadEmail

    mock_summary = ThreadSummary(
        thread_id="thread_abc123",
        account_id="gmail_1",
        subject="Project Discussion",
        summary="Regenerated summary",
        key_points=["Point 1", "Point 2"],
        email_count=3,
        participants=["alice@company.com"],
        started_at=datetime.utcnow(),
        last_email_at=datetime.utcnow(),
        emails=[
            ThreadEmail(
                email_id="email_001",
                subject="Project Discussion",
                sender="alice@company.com",
                received_at=datetime.utcnow(),
                position=1,
                is_thread_start=True,
            )
        ],
    )
    mock_summarize.return_value = mock_summary

    response = client.get(
        "/api/v1/threads/thread_abc123/summary?account_id=gmail_1&force_regenerate=true"
    )

    assert response.status_code == 200
    # Verify force_regenerate was passed
    mock_summarize.assert_called_once()
    call_kwargs = mock_summarize.call_args.kwargs
    assert call_kwargs["force_regenerate"] is True


@patch("agent_platform.threads.thread_service.ThreadService.summarize_thread")
def test_get_thread_summary_server_error(mock_summarize, client, clean_database):
    """Test handling of server errors during summarization"""
    mock_summarize.side_effect = Exception("LLM service unavailable")

    response = client.get("/api/v1/threads/thread_abc123/summary?account_id=gmail_1")

    assert response.status_code == 500


# ============================================================================
# Test: Query Parameters
# ============================================================================

def test_get_thread_summary_missing_account_id(client, clean_database):
    """Test that account_id is required for summary endpoint"""
    response = client.get("/api/v1/threads/thread_abc123/summary")

    # Should fail validation (account_id is required)
    assert response.status_code == 422


def test_get_thread_emails_account_id_optional(client, clean_database, sample_thread_emails):
    """Test that account_id is optional for emails endpoint"""
    response = client.get("/api/v1/threads/thread_abc123/emails")

    # Should succeed without account_id
    assert response.status_code == 200


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: Threads API Routes

Endpoints Tested:
- GET /api/v1/threads/{thread_id}/emails (get thread emails)
- GET /api/v1/threads/{thread_id}/summary (get/generate summary)

Test Categories:
- Get thread emails (5 tests)
- Get thread summary (4 tests)
- Query parameters (2 tests)

Total Tests: 11 tests

Coverage: Comprehensive coverage of thread retrieval and summarization endpoints
"""
