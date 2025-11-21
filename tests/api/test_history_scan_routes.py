"""
Tests for History Scan API Routes
Tests scan lifecycle, progress tracking, and statistics endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from agent_platform.api.main import app
from agent_platform.history_scan.models import ScanConfig, ScanStatus


# ============================================================================
# Test Client Setup
# ============================================================================

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_scan_config():
    """Sample scan configuration"""
    return {
        "account_id": "gmail_1",
        "batch_size": 50,
        "max_results": 1000,
        "query": "after:2024/01/01",
        "skip_already_processed": True,
        "process_attachments": True,
        "process_threads": True,
    }


# ============================================================================
# Test: Start Scan
# ============================================================================

def test_start_scan_success(client, sample_scan_config):
    """Test starting a new history scan"""
    response = client.post("/api/v1/history-scan/start", json=sample_scan_config)

    assert response.status_code == 200
    data = response.json()

    assert "scan_id" in data
    assert data["account_id"] == "gmail_1"
    assert data["status"] == "in_progress"
    assert data["total_found"] == 0
    assert data["processed"] == 0
    assert "started_at" in data


def test_start_scan_minimal_config(client):
    """Test starting scan with minimal required fields"""
    config = {
        "account_id": "gmail_2",
    }

    response = client.post("/api/v1/history-scan/start", json=config)

    assert response.status_code == 200
    data = response.json()

    assert data["account_id"] == "gmail_2"
    assert data["status"] == "in_progress"


def test_start_scan_custom_batch_size(client):
    """Test starting scan with custom batch size"""
    config = {
        "account_id": "gmail_1",
        "batch_size": 100,
    }

    response = client.post("/api/v1/history-scan/start", json=config)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "in_progress"


def test_start_scan_with_query_filter(client):
    """Test starting scan with Gmail query filter"""
    config = {
        "account_id": "gmail_1",
        "query": "from:boss@company.com after:2024/01/01",
        "max_results": 500,
    }

    response = client.post("/api/v1/history-scan/start", json=config)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "in_progress"


def test_start_scan_invalid_batch_size(client):
    """Test starting scan with invalid batch size (too large)"""
    config = {
        "account_id": "gmail_1",
        "batch_size": 1000,  # Max is 500
    }

    response = client.post("/api/v1/history-scan/start", json=config)

    assert response.status_code == 422  # Validation error


def test_start_scan_missing_account_id(client):
    """Test starting scan without required account_id"""
    config = {
        "batch_size": 50,
    }

    response = client.post("/api/v1/history-scan/start", json=config)

    assert response.status_code == 422


# ============================================================================
# Test: Get Scan Progress
# ============================================================================

def test_get_scan_progress_success(client, sample_scan_config):
    """Test getting progress of an active scan"""
    # Start a scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    assert start_response.status_code == 200
    scan_id = start_response.json()["scan_id"]

    # Get progress
    response = client.get(f"/api/v1/history-scan/{scan_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["scan_id"] == scan_id
    assert data["account_id"] == "gmail_1"
    assert "status" in data
    assert "total_found" in data
    assert "processed" in data


def test_get_scan_progress_not_found(client):
    """Test getting progress for nonexistent scan"""
    response = client.get("/api/v1/history-scan/nonexistent_scan_id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_scan_progress_includes_counters(client, sample_scan_config):
    """Test that progress includes all counter fields"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Get progress
    response = client.get(f"/api/v1/history-scan/{scan_id}")

    assert response.status_code == 200
    data = response.json()

    # Check counter fields
    counter_fields = [
        "total_found", "processed", "skipped", "failed",
        "classified_high", "classified_medium", "classified_low",
        "tasks_extracted", "decisions_extracted", "questions_extracted",
        "attachments_downloaded", "threads_summarized"
    ]

    for field in counter_fields:
        assert field in data, f"Missing counter field: {field}"


# ============================================================================
# Test: List Active Scans
# ============================================================================

def test_list_active_scans_empty(client):
    """Test listing scans when none are active"""
    # Note: Service is stateful, may have scans from previous tests
    response = client.get("/api/v1/history-scan/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_list_active_scans_multiple(client, sample_scan_config):
    """Test listing multiple active scans"""
    # Start 2 scans
    config1 = {**sample_scan_config, "account_id": "gmail_1"}
    config2 = {**sample_scan_config, "account_id": "gmail_2"}

    response1 = client.post("/api/v1/history-scan/start", json=config1)
    response2 = client.post("/api/v1/history-scan/start", json=config2)

    assert response1.status_code == 200
    assert response2.status_code == 200

    # List all scans
    response = client.get("/api/v1/history-scan/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 2  # At least our 2 scans


# ============================================================================
# Test: Pause Scan
# ============================================================================

def test_pause_scan_success(client, sample_scan_config):
    """Test pausing an active scan"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Pause scan
    response = client.post(f"/api/v1/history-scan/{scan_id}/pause")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "paused"
    assert data["scan_id"] == scan_id


def test_pause_scan_not_found(client):
    """Test pausing nonexistent scan"""
    response = client.post("/api/v1/history-scan/nonexistent_scan/pause")

    assert response.status_code == 400
    assert "cannot pause" in response.json()["detail"].lower()


# ============================================================================
# Test: Resume Scan
# ============================================================================

def test_resume_scan_success(client, sample_scan_config):
    """Test resuming a paused scan"""
    # Start and pause scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    pause_response = client.post(f"/api/v1/history-scan/{scan_id}/pause")
    assert pause_response.status_code == 200

    # Resume scan
    response = client.post(f"/api/v1/history-scan/{scan_id}/resume")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "resumed"
    assert data["scan_id"] == scan_id


def test_resume_scan_not_paused(client, sample_scan_config):
    """Test resuming scan that is not paused"""
    # Start scan (still in progress)
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Try to resume (should fail because not paused)
    response = client.post(f"/api/v1/history-scan/{scan_id}/resume")

    assert response.status_code == 400
    assert "cannot resume" in response.json()["detail"].lower()


# ============================================================================
# Test: Cancel Scan
# ============================================================================

def test_cancel_scan_success(client, sample_scan_config):
    """Test cancelling an active scan"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Cancel scan
    response = client.post(f"/api/v1/history-scan/{scan_id}/cancel")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "cancelled"
    assert data["scan_id"] == scan_id


def test_cancel_scan_not_found(client):
    """Test cancelling nonexistent scan"""
    response = client.post("/api/v1/history-scan/nonexistent_scan/cancel")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Test: Get Scan Stats
# ============================================================================

def test_get_scan_stats_success(client, sample_scan_config):
    """Test getting detailed statistics for a scan"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Get stats
    response = client.get(f"/api/v1/history-scan/{scan_id}/stats")

    assert response.status_code == 200
    data = response.json()

    assert data["scan_id"] == scan_id
    assert data["account_id"] == "gmail_1"
    assert "progress" in data
    assert "classification" in data
    assert "extraction" in data
    assert "resources" in data
    assert "timing" in data


def test_get_scan_stats_progress_breakdown(client, sample_scan_config):
    """Test that stats include progress breakdown"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Get stats
    response = client.get(f"/api/v1/history-scan/{scan_id}/stats")
    data = response.json()

    progress = data["progress"]
    assert "total_found" in progress
    assert "processed" in progress
    assert "skipped" in progress
    assert "failed" in progress
    assert "percent" in progress


def test_get_scan_stats_classification_breakdown(client, sample_scan_config):
    """Test that stats include classification breakdown"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Get stats
    response = client.get(f"/api/v1/history-scan/{scan_id}/stats")
    data = response.json()

    classification = data["classification"]
    assert "high" in classification
    assert "medium" in classification
    assert "low" in classification


def test_get_scan_stats_extraction_breakdown(client, sample_scan_config):
    """Test that stats include extraction breakdown"""
    # Start scan
    start_response = client.post("/api/v1/history-scan/start", json=sample_scan_config)
    scan_id = start_response.json()["scan_id"]

    # Get stats
    response = client.get(f"/api/v1/history-scan/{scan_id}/stats")
    data = response.json()

    extraction = data["extraction"]
    assert "tasks" in extraction
    assert "decisions" in extraction
    assert "questions" in extraction


def test_get_scan_stats_not_found(client):
    """Test getting stats for nonexistent scan"""
    response = client.get("/api/v1/history-scan/nonexistent_scan/stats")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Test: Response Models
# ============================================================================

def test_scan_progress_response_structure(client, sample_scan_config):
    """Test that ScanProgress response has correct structure"""
    response = client.post("/api/v1/history-scan/start", json=sample_scan_config)

    assert response.status_code == 200
    data = response.json()

    required_fields = [
        "scan_id", "account_id", "status",
        "total_found", "processed", "skipped", "failed",
        "started_at", "last_updated_at"
    ]

    for field in required_fields:
        assert field in data, f"Required field '{field}' missing from response"


# ============================================================================
# Summary
# ============================================================================
"""
Test Coverage: History Scan API Routes

Endpoints Tested:
- POST /api/v1/history-scan/start (start scan)
- GET /api/v1/history-scan/{scan_id} (get progress)
- GET /api/v1/history-scan/ (list active scans)
- POST /api/v1/history-scan/{scan_id}/pause (pause scan)
- POST /api/v1/history-scan/{scan_id}/resume (resume scan)
- POST /api/v1/history-scan/{scan_id}/cancel (cancel scan)
- GET /api/v1/history-scan/{scan_id}/stats (get detailed stats)

Test Categories:
- Start scan (6 tests)
- Get progress (3 tests)
- List scans (2 tests)
- Pause scan (2 tests)
- Resume scan (2 tests)
- Cancel scan (2 tests)
- Get stats (5 tests)
- Response models (1 test)

Total Tests: 23 tests

Coverage: Comprehensive coverage of all history scan lifecycle operations
"""
