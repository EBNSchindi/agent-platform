# Agent Platform API

FastAPI backend for the Digital Twin Email Platform Cockpit.

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Run migrations
python migrations/run_migration.py

# Verify database
python scripts/setup/verify_db.py
```

### 3. Start API Server

```bash
# Development mode (with auto-reload)
uvicorn agent_platform.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn agent_platform.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

---

## API Endpoints

### Email-Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/email-agent/status` | Get agent status |
| GET | `/api/v1/email-agent/runs` | List runs (processed emails) |
| GET | `/api/v1/email-agent/runs/{run_id}` | Get run details |
| POST | `/api/v1/email-agent/runs/{run_id}/accept` | Accept run |
| POST | `/api/v1/email-agent/runs/{run_id}/reject` | Reject run |
| POST | `/api/v1/email-agent/runs/{run_id}/edit` | Edit run |
| POST | `/api/v1/email-agent/trigger-test` | Trigger test run |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tasks` | List tasks |
| GET | `/api/v1/tasks/{task_id}` | Get task details |
| PATCH | `/api/v1/tasks/{task_id}` | Update task |
| POST | `/api/v1/tasks/{task_id}/complete` | Complete task |

### Decisions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/decisions` | List decisions |
| GET | `/api/v1/decisions/{decision_id}` | Get decision details |
| POST | `/api/v1/decisions/{decision_id}/decide` | Make decision |

### Questions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/questions` | List questions |
| GET | `/api/v1/questions/{question_id}` | Get question details |
| POST | `/api/v1/questions/{question_id}/answer` | Answer question |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/overview` | Dashboard overview stats |
| GET | `/api/v1/dashboard/today` | Today's summary |

---

## Query Parameters

### Filtering

All list endpoints support filtering:

```bash
# Filter tasks by status and priority
GET /api/v1/tasks?status=pending&priority=high

# Filter by account
GET /api/v1/tasks?account_id=gmail_1

# Filter email-agent runs needing human review
GET /api/v1/email-agent/runs?needs_human=true
```

### Pagination

```bash
# Limit results
GET /api/v1/tasks?limit=10

# Offset for pagination
GET /api/v1/tasks?limit=10&offset=20
```

---

## Example Requests

### Get Dashboard Overview

```bash
curl http://localhost:8000/api/v1/dashboard/overview
```

Response:
```json
{
  "tasks": {
    "pending": 15,
    "in_progress": 3,
    "completed_today": 8,
    "overdue": 2
  },
  "decisions": {
    "pending": 5,
    "decided_today": 3
  },
  "emails": {
    "processed_today": 42,
    "by_category": {
      "wichtig": 12,
      "normal": 25,
      "spam": 5
    },
    "high_confidence": 30,
    "medium_confidence": 8,
    "low_confidence": 4
  },
  "needs_human_count": 12
}
```

### List Email-Agent Runs

```bash
curl "http://localhost:8000/api/v1/email-agent/runs?limit=5&needs_human=true"
```

### Accept a Run

```bash
curl -X POST http://localhost:8000/api/v1/email-agent/runs/msg_123/accept \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Looks good!"}'
```

### Complete a Task

```bash
curl -X POST http://localhost:8000/api/v1/tasks/task_123/complete \
  -H "Content-Type: application/json" \
  -d '{"completion_notes": "Done and tested"}'
```

---

## Architecture

The API is a thin layer over existing services:

```
Frontend (Next.js)
    ↓ HTTP/REST
FastAPI Routes
    ↓ Function calls
Services (MemoryService, EventService, etc.)
    ↓ SQLAlchemy
Database (SQLite)
```

**Key Principles:**
- **Event-First:** All actions logged as events
- **Thin API Layer:** Business logic in services, not routes
- **Type-Safe:** Pydantic models for validation
- **Auto-Generated Docs:** OpenAPI/Swagger

---

## Testing

```bash
# Run API tests
pytest tests/api/ -v

# Test specific endpoint
pytest tests/api/test_email_agent.py -v

# With coverage
pytest tests/api/ --cov=agent_platform.api
```

---

## CORS Configuration

CORS is configured for Next.js frontend (localhost:3000).

To add more origins:

```python
# agent_platform/api/main.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-domain.com",
    ],
    # ...
)
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "agent_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service

```ini
[Unit]
Description=Agent Platform API
After=network.target

[Service]
User=agent
WorkingDirectory=/opt/agent-platform
ExecStart=/opt/agent-platform/venv/bin/uvicorn agent_platform.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Next Steps

1. ✅ Core APIs implemented
2. ⏳ Next.js Frontend (Week 2)
3. ⏳ Authentication/JWT (Phase 2)
4. ⏳ WebSocket for real-time updates (Phase 3)
