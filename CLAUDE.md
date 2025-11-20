# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Digital Twin Email Platform** - Intelligentes Email-Management-System mit Event-First Architecture und kontinuierlichem Lernen.

**Current Status:** Phase 1 in Development
- ✅ Email Importance Classification (3-Layer: Rules → History → LLM)
- ✅ Event-Log System (Foundation für Digital Twin)
- 🚧 Email Extraction (Tasks, Decisions, Questions)

**Important Documents:**
- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) - Quick Reference & Aktueller Status
- [docs/VISION.md](docs/VISION.md) - Big Picture & Langfristige Roadmap
- [docs/MAINTENANCE.md](docs/MAINTENANCE.md) - Dokumentations-Wartung

## Architecture Principles

### 1. Plugin-Based Module System

Modules are independent plugins that register with the central `AgentRegistry`:

```python
# Module registration pattern
from platform.core.registry import get_registry

def register_email_module():
    registry = get_registry()

    # 1. Register module
    registry.register_module(name="email", version="1.0.0", description="...")

    # 2. Create agents
    classifier = create_classifier_agent()

    # 3. Register agents with capabilities
    registry.register_agent(
        module_name="email",
        agent_name="classifier",
        agent_instance=classifier,
        agent_type="classifier",
        capabilities=["email_classification", "spam_detection"]
    )
```

**Key Pattern:** Agent IDs follow `module_name.agent_name` format (e.g., `email.classifier`)

### 2. OpenAI Agents SDK Patterns

Based on patterns from `/agent-systems/2_openai/` Labs 1-4:

**Agent-as-Tool (Lab 2):**
- Agents can be used as tools for other agents via `.as_tool()`
- Example: Responder orchestrator uses 3 tone-specific sub-agents

**Structured Outputs (Lab 3):**
- All agents return Pydantic models for type safety
- Use `output_type=YourPydanticModel` in Agent definition
- Example: `EmailClassification` model with fields like `category`, `confidence`, `reasoning`

**Guardrails (Lab 3):**
- Use `@input_guardrail` and `@output_guardrail` decorators
- Return `GuardrailFunctionOutput` with `tripwire_triggered=True` to stop execution
- Example: PII detection, phishing detection, compliance checks

**Orchestration (Lab 4):**
- Manager-worker pattern with master orchestrator
- Use `asyncio.gather()` for parallel execution
- Example: EmailOrchestrator processes multiple accounts concurrently

### 3. Event-First Architecture (Digital Twin Foundation)

**Core Principle:** All actions are logged as immutable events. Memory-Objects are derived from these events.

**Event-Logging Pattern:**

```python
from agent_platform.events import log_event, get_events, EventType

# Log an event
log_event(
    event_type=EventType.EMAIL_CLASSIFIED,
    account_id="gmail_1",
    email_id="msg_123",
    payload={
        'category': 'wichtig',
        'confidence': 0.92,
        'importance': 0.85,
        'layer_used': 'llm'
    },
    extra_metadata={
        'llm_provider': 'openai_fallback'
    },
    processing_time_ms=1234.5
)

# Query events
events = get_events(
    event_type=EventType.EMAIL_CLASSIFIED,
    account_id="gmail_1",
    start_time=today_start,
    limit=100
)

# Get events for specific email
email_events = get_events_for_email(email_id="msg_123")

# Count events
count = count_events(
    event_type=EventType.EMAIL_CLASSIFIED,
    account_id="gmail_1"
)
```

**Event Types (agent_platform/events/event_types.py):**
- `EMAIL_RECEIVED`, `EMAIL_CLASSIFIED`, `EMAIL_ANALYZED`, `EMAIL_SUMMARIZED`
- `TASK_EXTRACTED`, `DECISION_EXTRACTED`, `QUESTION_EXTRACTED`
- `USER_FEEDBACK`, `USER_CORRECTION`, `USER_CONFIRMATION`
- `JOURNAL_GENERATED`, `JOURNAL_REVIEWED`

**When to log events:**
- ✅ After every classification
- ✅ After every extraction (Task, Decision, Question)
- ✅ After every user action (feedback, corrections)
- ✅ After every journal generation
- ✅ Whenever state changes in the system

**Event-Log Benefits:**
- Complete audit trail
- Foundation for learning (preference tracking)
- Historical analysis
- Digital Twin behavior modeling

### 3.1 Email Extraction Pattern

Email extraction uses **Structured Outputs** (Pydantic models as `response_format`) for type-safe LLM responses:

```python
from agent_platform.extraction import ExtractionAgent
from agent_platform.classification import EmailToClassify

# Create extraction agent
extraction_agent = ExtractionAgent()

# Create email to analyze
email = EmailToClassify(
    email_id="msg_123",
    account_id="gmail_1",
    sender="boss@company.com",
    subject="Project Update - Action Required",
    body="Please review the Q4 report by Friday and send me the numbers.",
)

# Extract structured information
extraction_result = await extraction_agent.extract(email)

# Access extraction results
print(f"Summary: {extraction_result.summary}")
print(f"Main Topic: {extraction_result.main_topic}")
print(f"Sentiment: {extraction_result.sentiment}")
print(f"Has Action Items: {extraction_result.has_action_items}")

# Access extracted tasks
for task in extraction_result.tasks:
    print(f"  Task: {task.description}")
    print(f"  Deadline: {task.deadline}")
    print(f"  Priority: {task.priority}")
    print(f"  Requires My Action: {task.requires_action_from_me}")
    print(f"  Context: {task.context}")

# Access extracted decisions
for decision in extraction_result.decisions:
    print(f"  Decision: {decision.question}")
    print(f"  Options: {', '.join(decision.options)}")
    print(f"  Urgency: {decision.urgency}")
    print(f"  Requires My Input: {decision.requires_my_input}")

# Access extracted questions
for question in extraction_result.questions:
    print(f"  Question: {question.question}")
    print(f"  Requires Response: {question.requires_response}")
    print(f"  Type: {question.question_type}")

# Get summary dict
summary = extraction_result.to_summary_dict()
print(f"Total Items: {summary['total_items']}")
```

**Integration with Classification Pipeline:**

```python
from agent_platform.orchestration import ClassificationOrchestrator

orchestrator = ClassificationOrchestrator()

# Process emails (classification + extraction)
emails = [
    {
        'id': 'msg_1',
        'subject': 'Meeting Tomorrow',
        'sender': 'colleague@company.com',
        'body': 'Can we meet at 10am to discuss the budget?',
    },
    ...
]

stats = await orchestrator.process_emails(emails, 'gmail_1')

# Check extraction statistics
print(f"Emails with extractions: {stats.emails_with_extractions}")
print(f"Tasks extracted: {stats.total_tasks_extracted}")
print(f"Decisions extracted: {stats.total_decisions_extracted}")
print(f"Questions extracted: {stats.total_questions_extracted}")
```

**Extraction Models (agent_platform/extraction/models.py):**
- `ExtractedTask`: description, deadline, priority, requires_action_from_me, context, assignee
- `ExtractedDecision`: question, options, recommendation, urgency, requires_my_input, context
- `ExtractedQuestion`: question, context, requires_response, urgency, question_type
- `EmailExtraction`: summary, main_topic, sentiment, has_action_items, tasks, decisions, questions

**LLM Provider:**
- **Ollama-first** (qwen2.5:7b): Local, free, fast (~3s per email)
- **OpenAI fallback** (gpt-4o): Cloud, paid, reliable (~1s per email)
- Automatic fallback if Ollama unavailable

### 4. Multi-Account Configuration

Configuration uses a centralized `Config` class with per-account modes:

```python
from platform.core.config import Config, Mode

# Supported modes per account
Mode.DRAFT         # Generate drafts for review (default)
Mode.AUTO_REPLY    # Send automatically if confidence > 0.85
Mode.MANUAL        # Classification only, no drafts

# Setting modes
Config.set_account_mode("gmail_1", Mode.DRAFT)
Config.get_account_mode("gmail_1")  # Returns Mode enum
```

**Account Structure:**
- 3 Gmail accounts: `gmail_1`, `gmail_2`, `gmail_3`
- 1 Ionos account: `ionos`
- 1 Backup account: `backup`

### 4. Database Schema

SQLAlchemy models in `platform/db/models.py`:

**Platform Core Tables:**
- `modules`: Registered modules
- `agents`: Registered agents with capabilities
- `runs`: Agent execution history
- `steps`: Individual steps within runs

**Email Module Tables:**
- `email_accounts`: Account configurations and modes
- `processed_emails`: Email processing history with classifications

## Common Development Commands

### Setup and Initialization

```bash
# Initial setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database initialization
python -c "from platform.db.database import init_db; init_db()"
```

### Testing Email Module

```bash
# Test classification system
python scripts/run_classifier.py

# Test extraction agent
pytest tests/extraction/test_extraction_agent.py -v

# Test classification + extraction pipeline (integration)
pytest tests/integration/test_classification_extraction_pipeline.py -v

# Test responder (draft generation)
python scripts/run_responder.py

# Interactive multi-account workflow tester
python scripts/run_full_workflow.py

# Start scheduler (automated operation)
python scripts/run_scheduler.py
```

### Gmail API OAuth Setup

First run of any Gmail tool opens browser for OAuth consent. Tokens cached in `tokens/gmail_account_N_token.json`.

To re-authenticate an account:
```bash
rm tokens/gmail_account_1_token.json
python scripts/run_classifier.py  # Triggers OAuth flow
```

## Critical Implementation Details

### Email Tool Abstraction

Two email service implementations with unified interface:

**Gmail (`modules/email/tools/gmail_tools.py`):**
- Uses Gmail API with OAuth2
- Methods: `fetch_unread_emails()`, `create_draft()`, `apply_label()`, `archive_email()`, `send_email()`
- Service instances cached in `_gmail_services` dict to avoid re-authentication

**Ionos (`modules/email/tools/ionos_tools.py`):**
- Uses IMAP for fetch, SMTP for send
- IMAP connection to fetch emails, APPEND to Drafts folder for drafts

### Orchestrator Mode Routing

The `EmailOrchestrator` in `modules/email/agents/orchestrator.py` routes based on mode:

```python
# Mode-based workflow
if mode == Mode.MANUAL:
    # Classify + label only

elif mode == Mode.DRAFT:
    # Classify + generate draft + save to Drafts folder

elif mode == Mode.AUTO_REPLY:
    if response.confidence_score >= Config.RESPONDER_CONFIDENCE_THRESHOLD:
        # Send email directly
    else:
        # Fall back to draft mode
```

### Scheduler Configuration

APScheduler jobs in `scripts/run_scheduler.py`:

1. **Inbox Check:** Runs every `INBOX_CHECK_INTERVAL_HOURS` (default: 1 hour)
2. **Monthly Backup:** Runs on day `BACKUP_DAY_OF_MONTH` at `BACKUP_HOUR` (default: day 1 at 3 AM)
3. **Spam Cleanup:** Daily at 2 AM (placeholder, not fully implemented)

### Guardrails Tripwire Mechanism

Guardrails use a tripwire pattern to halt dangerous operations:

```python
@input_guardrail
async def check_pii_in_email(ctx, agent, message):
    result = await Runner.run(pii_agent, message)

    return GuardrailFunctionOutput(
        output_info={'pii_detected': result.contains_pii},
        tripwire_triggered=not result.safe  # STOPS execution if True
    )
```

When `tripwire_triggered=True`, agent execution halts immediately.

## Adding New Modules

To add a new module (e.g., Calendar):

1. **Create module structure:**
   ```
   modules/calendar/
   ├── __init__.py
   ├── module.py              # Registration logic
   ├── agents/
   │   ├── __init__.py
   │   ├── scheduler.py       # Calendar scheduling agent
   │   └── reminder.py        # Reminder agent
   ├── tools/
   │   └── gcal_tools.py      # Google Calendar API
   └── guardrails/
       └── calendar_guardrails.py
   ```

2. **Create registration function in `module.py`:**
   ```python
   def register_calendar_module():
       registry = get_registry()
       registry.register_module(name="calendar", version="1.0.0", ...)

       scheduler_agent = create_scheduler_agent()
       registry.register_agent(
           module_name="calendar",
           agent_name="scheduler",
           agent_instance=scheduler_agent,
           capabilities=["meeting_scheduling", "availability_check"]
       )
   ```

3. **Initialize in scripts:**
   ```python
   from modules.calendar.module import register_calendar_module

   register_email_module()
   register_calendar_module()
   ```

## Environment Configuration

Critical `.env` variables:

```env
# Required
OPENAI_API_KEY=sk-proj-...

# Gmail accounts (OAuth)
GMAIL_1_EMAIL=user@gmail.com
GMAIL_1_CREDENTIALS_PATH=credentials/gmail_account_1.json
GMAIL_1_TOKEN_PATH=tokens/gmail_account_1_token.json

# Ionos account (IMAP/SMTP)
IONOS_EMAIL=user@ionos.de
IONOS_PASSWORD=yourpassword
IONOS_IMAP_SERVER=imap.ionos.de
IONOS_SMTP_SERVER=smtp.ionos.de

# Backup account (Gmail)
BACKUP_EMAIL=backup@gmail.com
BACKUP_CREDENTIALS_PATH=credentials/backup_account.json

# Mode configuration
DEFAULT_MODE=draft  # draft, auto_reply, manual

# Scheduler
INBOX_CHECK_INTERVAL_HOURS=1
BACKUP_DAY_OF_MONTH=1
BACKUP_HOUR=3
```

## Database Access Patterns

Use context manager for database sessions:

```python
from platform.db.database import get_db
from platform.db.models import ProcessedEmail

with get_db() as db:
    email_record = ProcessedEmail(
        account_id="gmail_1",
        email_id="msg_123",
        category="important",
        confidence=0.92
    )
    db.add(email_record)
    # Commit happens automatically on exit
```

## Agent Discovery

Use registry to discover agents by capability:

```python
from platform.core.registry import get_registry

registry = get_registry()

# Find all agents with spam detection capability
spam_detectors = registry.discover_agents("spam_detection")
# Returns: ["email.classifier"]

# Get specific agent
classifier = registry.get_agent("email.classifier")
```

## Async Execution Patterns

All agent runs and email operations use async/await:

```python
from agents import Runner

# Single agent run
result = await Runner.run(classifier_agent, email_content)

# Parallel batch processing
tasks = [
    classify_email(email, classifier)
    for email in emails
]
results = await asyncio.gather(*tasks)

# Sequential processing with delays (for rate limiting)
for account_id in accounts:
    result = await process_account(account_id)
    await asyncio.sleep(2)  # Delay between accounts
```

## Common Pitfalls

1. **Gmail API Rate Limits:** Add delays between batch operations using `await asyncio.sleep(0.5)`

2. **Token Expiration:** Gmail tokens auto-refresh, but if corrupted, delete token files and re-authenticate

3. **Mode Configuration:** Always use `Config.get_account_mode(account_id)` instead of accessing `Config.ACCOUNT_MODES` directly (provides defaults)

4. **Database Sessions:** Always use `with get_db() as db:` pattern, never create sessions manually

5. **Agent Registration:** Register modules before registering agents, otherwise module validation fails

6. **Pydantic Models:** When defining structured outputs, use Field descriptions - they're included in LLM prompts

## Testing Strategy

Manual testing via scripts:
- `run_classifier.py`: Test single agent
- `run_responder.py`: Test agent orchestration
- `run_full_workflow.py`: Test complete workflows with all modes
- `run_scheduler.py`: Test scheduled execution

Unit tests not yet implemented (planned in `tests/` directory).
