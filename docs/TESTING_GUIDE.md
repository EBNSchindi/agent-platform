# Testing Guide

**Comprehensive testing documentation for the Digital Twin Email Platform**

Last Updated: 2025-11-21
Total Test Functions: ~427 tests across 31 files
Test Coverage: ~85% (core workflows), 60-70% (E2E integration)

---

## Table of Contents

1. [Test Organization](#test-organization)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Manual Testing Scripts](#manual-testing-scripts)
5. [End-to-End Tests](#end-to-end-tests)
6. [Writing New Tests](#writing-new-tests)
7. [Troubleshooting](#troubleshooting)

---

## Test Organization

### Directory Structure

```
agent-platform/
├── tests/                    # Automated pytest tests (31 files, ~427 tests)
│   ├── api/                  # API route tests (236 tests)
│   ├── classification/       # Email classification tests (30+ tests)
│   ├── integration/          # End-to-end integration tests (19 tests)
│   ├── extraction/           # Email extraction tests (7 tests)
│   ├── events/               # Event system tests (10 tests)
│   ├── memory/               # Memory objects tests (15 tests)
│   ├── attachments/          # Attachment handling tests (35 tests)
│   ├── threads/              # Thread summarization tests (24 tests)
│   ├── history_scan/         # History scan tests (37 tests)
│   ├── webhooks/             # Webhook tests (35 tests)
│   ├── review/               # Review queue tests
│   ├── feedback/             # Feedback tracking tests
│   └── llm/                  # LLM provider tests
│
└── scripts/testing/          # Manual testing & setup scripts (10 scripts)
    ├── test_gmail_auth.py               # Gmail OAuth setup wizard
    ├── test_all_connections.py         # Health check all services
    ├── test_openai_connection.py       # OpenAI API validation
    ├── auth_gmail_1.py                 # Gmail account 1 auth
    ├── auth_gmail_3.py                 # Gmail account 3 auth
    ├── test_all_4_accounts_final.py    # Test all 4 email accounts
    ├── test_ionos_connection.py        # Ionos IMAP/SMTP test
    └── test_all_4_accounts.py          # (Deprecated - use _final version)
```

### Test vs Script Distinction

| Aspect | `tests/` (Automated) | `scripts/testing/` (Manual) |
|--------|----------------------|---------------------------|
| **Purpose** | Unit & integration testing | Setup, diagnostics, health checks |
| **Execution** | `pytest` (CI/CD) | Direct Python execution |
| **Data** | Mock data, fixtures | Real API connections |
| **When to use** | Development, PR validation | Initial setup, troubleshooting |
| **Examples** | `test_classification_layers.py` | `test_gmail_auth.py` |

**Key Principle**: Scripts prepare the environment; tests validate functionality.

---

## Running Tests

### Quick Start

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/classification/ -v

# Single file
pytest tests/api/test_tasks_routes.py -v

# With coverage
pytest tests/ --cov=agent_platform --cov-report=html

# Fast tests only (skip slow integration tests)
pytest tests/ -m "not slow" -v
```

### Test Markers

```python
@pytest.mark.slow          # Long-running tests (>5s)
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e           # End-to-end tests
@pytest.mark.gmail_api     # Requires real Gmail API
@pytest.mark.skip          # Temporarily disabled
```

### Environment Setup

```bash
# Required for all tests
export PYTHONPATH=.
source venv/bin/activate

# Required for Gmail E2E tests
export GMAIL_2_CREDENTIALS_PATH=credentials/gmail_account_2.json
export GMAIL_2_TOKEN_PATH=tokens/gmail_account_2_token.json
export GMAIL_2_EMAIL=your_email@gmail.com

# Optional: OpenAI for LLM tests
export OPENAI_API_KEY=sk-proj-...
```

---

## Test Categories

### 1. API Route Tests (236 tests)

**Location**: `tests/api/`
**Coverage**: All 10 API route modules

| File | Tests | Endpoints Covered |
|------|-------|------------------|
| `test_email_agent_routes.py` | 33 | Email agent status, runs, HITL actions |
| `test_tasks_routes.py` | 28 | Tasks CRUD, completion, filtering |
| `test_decisions_routes.py` | 27 | Decisions CRUD, decision-making |
| `test_dashboard_routes.py` | 26 | Dashboard stats, activity feed |
| `test_questions_routes.py` | 24 | Questions CRUD, answering |
| `test_review_queue_routes.py` | 24 | Review queue management, approval |
| `test_history_scan_routes.py` | 23 | History scan lifecycle |
| `test_webhooks_routes.py` | 20 | Webhook subscriptions, notifications |
| `test_attachments_routes.py` | 20 | Attachment listing, download |
| `test_threads_routes.py` | 11 | Thread emails, summaries |

**Run API tests:**
```bash
pytest tests/api/ -v
```

**Pattern**: All API tests use:
- `TestClient` from FastAPI
- `clean_database` fixture for isolation
- Sample data fixtures (`sample_tasks`, `sample_decisions`, etc.)

### 2. Classification Tests (30+ tests)

**Location**: `tests/classification/`

| File | Purpose | Tests |
|------|---------|-------|
| `test_ensemble_classifier.py` | Phase 2 parallel classifier | Ensemble logic, LLM skip, agreement detection |
| `test_classification_layers.py` | Individual layer tests | Rule, History, LLM layers separately |
| `test_unified_classifier.py` | Legacy sequential classifier | Backward compatibility |

**Run classification tests:**
```bash
pytest tests/classification/ -v
```

### 3. Integration Tests (19 tests)

**Location**: `tests/integration/`

| File | Purpose | Real APIs |
|------|---------|-----------|
| `test_e2e_real_gmail.py` | **Real Gmail integration** | ✅ Gmail API |
| `test_e2e_classification_workflow.py` | Full workflow: classify → route → review → feedback | ❌ Mock data |
| `test_classification_extraction_pipeline.py` | Classification + extraction | ❌ Mock data |
| `test_ensemble_orchestrator_integration.py` | Ensemble classifier integration | ❌ Mock data |
| `test_journal_generation_integration.py` | Journal generation workflow | ❌ Mock data |

**Run integration tests:**
```bash
pytest tests/integration/ -v

# Gmail E2E only (requires credentials)
pytest tests/integration/test_e2e_real_gmail.py -v
```

### 4. Service Layer Tests (131 tests)

**Phase 4 & 5 Features:**

| Module | Tests | File |
|--------|-------|------|
| Attachments | 35 | `tests/attachments/test_attachment_service.py` |
| History Scan | 37 | `tests/history_scan/test_history_scan_service.py` |
| Webhooks | 35 | `tests/webhooks/test_webhook_service.py` |
| Threads | 24 | `tests/threads/test_thread_service.py` |

**Core Services:**

| Module | File |
|--------|------|
| Memory | `tests/memory/test_memory_service.py` |
| Events | `tests/events/test_event_service.py` |
| Extraction | `tests/extraction/test_extraction_agent.py` |
| Feedback | `tests/feedback/test_feedback_tracking.py` |
| Review | `tests/review/test_review_system.py` |
| LLM | `tests/llm/test_llm_provider.py` |

**Run service tests:**
```bash
pytest tests/attachments/ tests/threads/ tests/history_scan/ tests/webhooks/ -v
```

---

## Manual Testing Scripts

### Setup Scripts

#### 1. Gmail OAuth Setup

```bash
PYTHONPATH=. ./venv/bin/python scripts/testing/test_gmail_auth.py
```

**Purpose**: Interactive OAuth setup wizard
**What it does**:
- Opens browser for Google OAuth consent
- Saves access/refresh tokens to `tokens/` directory
- Tests connection by fetching 5 unread emails
- Auto-refreshes expired tokens

**When to use**: Initial setup, or when tokens expire

#### 2. Account-Specific Authentication

```bash
# Gmail Account 1
PYTHONPATH=. ./venv/bin/python scripts/testing/auth_gmail_1.py

# Gmail Account 3
PYTHONPATH=. ./venv/bin/python scripts/testing/auth_gmail_3.py
```

**Purpose**: Authenticate specific Gmail accounts
**When to use**: When individual account tokens expire

### Diagnostic Scripts

#### 3. Health Check All Services

```bash
PYTHONPATH=. ./venv/bin/python scripts/testing/test_all_connections.py
```

**Purpose**: Comprehensive health check
**Checks**:
- ✅ Environment variables configured
- ✅ Gmail credentials/tokens exist
- ✅ Gmail API connection works
- ✅ OpenAI API connection works
- ✅ Database connection works

**Output**: Actionable next steps if any check fails

#### 4. Test All 4 Email Accounts

```bash
PYTHONPATH=. ./venv/bin/python scripts/testing/test_all_4_accounts_final.py
```

**Purpose**: Test all Gmail + Ionos accounts
**Tests**:
- gmail_1: daniel.schindler1992@gmail.com
- gmail_2: danischin92@gmail.com
- gmail_3: ebn.veranstaltungen.consulting@gmail.com
- ionos: info@ettlingen-by-night.de (IMAP/SMTP)

**Output**: Connection status + message counts

#### 5. Ionos Connection Test

```bash
PYTHONPATH=. ./venv/bin/python scripts/testing/test_ionos_connection.py
```

**Purpose**: Test Ionos IMAP/SMTP connection
**What it does**:
- Connects to imap.ionos.de:993
- Fetches unread emails
- Tests SMTP server (smtp.ionos.de:587)

---

## End-to-End Tests

### Current E2E Coverage: 60-70%

#### Well-Covered Workflows ✅

1. **Email Classification** (Rule → History → LLM)
   - File: `test_e2e_real_gmail.py`
   - Real Gmail API integration
   - Tests: 10 emails classified with real data

2. **Classification → Review → Feedback Loop**
   - File: `test_e2e_classification_workflow.py`
   - Full workflow with mock data
   - Tests: Review queue, daily digest, learning system

3. **Classification + Extraction Pipeline**
   - File: `test_classification_extraction_pipeline.py`
   - Tests: Tasks, decisions, questions extraction

#### E2E Gaps ⚠️

**Missing E2E Tests:**

1. **Multi-Account Workflows** (❌)
   - No test for processing all 4 accounts simultaneously
   - No account-switching scenarios

2. **OAuth Re-authentication** (❌)
   - No test for expired token handling
   - No test for OAuth refresh flow

3. **Attachments E2E** (⚠️ Partial)
   - Unit tests exist (35 tests)
   - No E2E test with real Gmail attachments

4. **Threads E2E** (⚠️ Partial)
   - Unit tests exist (24 tests)
   - No E2E test with real Gmail threads

5. **History Scan E2E** (⚠️ Partial)
   - Manual script exists: `scripts/test_real_world_history_scan.py`
   - No automated pytest E2E test

6. **Webhooks E2E** (❌)
   - Unit tests exist (35 tests)
   - No E2E test with real Gmail push notifications

7. **Frontend-Backend Integration** (❌)
   - No tests for API ↔ Frontend communication

---

## Writing New Tests

### Test File Template

```python
"""
Module: <Feature Name> Tests
Tests: <Brief description>
"""

import pytest
from agent_platform.<module> import <class>


@pytest.fixture
def sample_data():
    """Fixture providing test data."""
    return {
        'field': 'value'
    }


def test_basic_functionality(sample_data):
    """Test basic feature functionality."""
    # Arrange
    input_data = sample_data

    # Act
    result = process(input_data)

    # Assert
    assert result['status'] == 'success'
    assert 'expected_field' in result
```

### API Test Template

```python
"""API Route Tests: <Route Name>"""

import pytest
from fastapi.testclient import TestClient
from agent_platform.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def clean_database():
    """Clean database before each test."""
    from agent_platform.db.database import get_db
    with get_db() as db:
        # Clean tables
        pass


def test_endpoint_success(client, clean_database):
    """Test successful endpoint call."""
    response = client.get("/api/v1/resource")

    assert response.status_code == 200
    data = response.json()
    assert 'expected_field' in data
```

### Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Descriptive Names**: `test_endpoint_returns_404_when_not_found()`
4. **AAA Pattern**: Arrange → Act → Assert
5. **Mock External APIs**: Don't hit real APIs in unit tests
6. **Database Cleanup**: Use `clean_database` fixture

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
ModuleNotFoundError: No module named 'agent_platform'
```

**Solution:**
```bash
export PYTHONPATH=.
pytest tests/ -v
```

#### 2. Gmail API Errors

```bash
google.auth.exceptions.RefreshError: invalid_grant
```

**Solution:**
```bash
# Re-authenticate
PYTHONPATH=. ./venv/bin/python scripts/testing/auth_gmail_1.py
```

#### 3. Database Errors

```bash
sqlalchemy.exc.OperationalError: no such table
```

**Solution:**
```bash
# Run migrations
python migrations/run_migration.py
```

#### 4. Token Expired

```bash
Error: Token expired and refresh failed
```

**Solution:**
```bash
# Delete old token and re-authenticate
rm tokens/gmail_account_1_token.json
PYTHONPATH=. ./venv/bin/python scripts/testing/auth_gmail_1.py
```

#### 5. Tests Hanging

**Symptom**: Tests hang or timeout

**Possible Causes**:
- Background processes still running
- IMAP connections not closed
- LLM requests timing out

**Solution:**
```bash
# Kill background processes
pkill -f "python.*test"

# Run with timeout
pytest tests/ -v --timeout=60
```

### Debug Mode

```bash
# Verbose output
pytest tests/ -vv

# Show print statements
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -v -x

# Run specific test
pytest tests/api/test_tasks_routes.py::test_list_tasks -v

# Show full diff on failures
pytest tests/ -vv --tb=long
```

---

## Test Statistics

### Coverage by Module (as of 2025-11-21)

| Module | Tests | Coverage |
|--------|-------|----------|
| API Routes | 236 | 100% |
| Classification | 30+ | 90% |
| Integration | 19 | 70% (E2E gaps) |
| Service Layer | 131 | 85% |
| Events | 10 | 95% |
| Memory | 15 | 90% |
| Extraction | 7 | 80% |
| **Total** | **~427** | **~85%** |

### Test Execution Time

| Category | Time | Command |
|----------|------|---------|
| Fast tests | ~30s | `pytest tests/ -m "not slow"` |
| All unit tests | ~2m | `pytest tests/ --ignore=tests/integration` |
| Integration tests | ~5m | `pytest tests/integration/ -v` |
| Full suite | ~7m | `pytest tests/ -v` |

---

## Next Steps

### Recommended Test Additions

1. **Multi-Account E2E Test** - Test all 4 accounts in parallel
2. **OAuth Expiry Test** - Simulate token expiration and refresh
3. **Attachment E2E Test** - Real Gmail attachments download
4. **History Scan E2E Test** - Convert manual script to pytest
5. **Frontend Integration Tests** - API ↔ UI communication

### Test Maintenance

- Run full test suite before each PR: `pytest tests/ -v`
- Update this guide when adding new test categories
- Keep test coverage above 85%
- Add E2E tests for new major features

---

## Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Gmail API Python**: https://developers.google.com/gmail/api/quickstart/python
- **Project Documentation**: `docs/VISION.md`, `PROJECT_SCOPE.md`

---

**Last Updated**: 2025-11-21
**Maintained by**: Development Team
**Questions**: See `CLAUDE.md` for project architecture details
