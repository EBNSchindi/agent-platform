# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Digital Twin Email Platform** - An intelligent email management system with Event-First Architecture and continuous learning. The system learns from user behavior to assist with email processing proactively.

**Current Status:** Phase 2 COMPLETE ✅
- ✅ Email Importance Classification (3-Layer: Rules → History → LLM)
- ✅ Ensemble Classification System (Parallel 3-Layer + Weighted Scoring)
- ✅ Event-Log System (Foundation for Digital Twin)
- ✅ Email Extraction (Tasks, Decisions, Questions)
- ✅ Memory-Objects & Journal Generation
- ✅ Integration Testing (80 test functions, all passing)

**Important Documents:**
- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) - Quick Reference & Current Status
- [docs/VISION.md](docs/VISION.md) - Big Picture & Long-term Roadmap

## Architecture Principles

### 1. Event-First Architecture (Digital Twin Foundation)

**Core Principle:** All actions are logged as immutable events. Memory-Objects are derived from these events.

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
        'layer_used': 'ensemble'
    },
    extra_metadata={
        'weights_used': {'rule': 0.20, 'history': 0.30, 'llm': 0.50}
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

### 2. Classification Architecture

The system uses TWO classification approaches:

#### 2.1 Ensemble Classifier (Phase 2 - DEFAULT, Recommended)

All three layers run in parallel, then scores are combined with configurable weights:

```python
from agent_platform.classification import EnsembleClassifier, ScoringWeights

# Default configuration
classifier = EnsembleClassifier()

# Custom weights
custom_weights = ScoringWeights(
    rule_weight=0.25,
    history_weight=0.35,
    llm_weight=0.40
)
classifier = EnsembleClassifier(weights=custom_weights)

# Smart LLM Skip (automatically skip LLM when Rule+History agree)
classifier = EnsembleClassifier(smart_llm_skip=True)  # ~60-70% cost savings

result = await classifier.classify(email)
```

**Benefits:**
- Parallel execution (~1-3s for all layers)
- Agreement detection (+0.10 to +0.20 confidence boost)
- Smart LLM skip (60-70% cost savings when Rule+History agree)
- Disagreement tracking for learning
- Flexible weight configuration

**File:** `agent_platform/classification/ensemble_classifier.py:1`

#### 2.2 Legacy Classifier (Phase 1 - Sequential, Early-Stopping)

Sequential execution with early stopping at high confidence:

```python
from agent_platform.classification import LegacyClassifier

classifier = LegacyClassifier()
result = await classifier.classify(email)
```

**Early Stopping Logic:**
- Rule Layer → if confidence ≥ 0.85, stop
- History Layer → if confidence ≥ 0.85, stop
- LLM Layer → always provides result

**When to use Legacy:**
- Backwards compatibility testing
- Comparison benchmarks
- Budget-conscious scenarios (more LLM skips, but longer sequential time)

**File:** `agent_platform/classification/legacy_classifier.py:1`

### 3. Email Extraction Pattern

Email extraction uses **Structured Outputs** (Pydantic models) for type-safe LLM responses:

```python
from agent_platform.extraction import ExtractionAgent
from agent_platform.classification import EmailToClassify

extraction_agent = ExtractionAgent()

email = EmailToClassify(
    email_id="msg_123",
    account_id="gmail_1",
    sender="boss@company.com",
    subject="Project Update - Action Required",
    body="Please review the Q4 report by Friday and send me the numbers.",
)

# Extract structured information
extraction_result = await extraction_agent.extract(email)

# Access extracted tasks
for task in extraction_result.tasks:
    print(f"Task: {task.description}")
    print(f"Deadline: {task.deadline}")
    print(f"Priority: {task.priority}")

# Access extracted decisions
for decision in extraction_result.decisions:
    print(f"Decision: {decision.question}")
    print(f"Options: {', '.join(decision.options)}")

# Access extracted questions
for question in extraction_result.questions:
    print(f"Question: {question.question}")
    print(f"Type: {question.question_type}")
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

### 4. Orchestration Pattern

The `ClassificationOrchestrator` integrates classification + extraction + routing:

```python
from agent_platform.orchestration import ClassificationOrchestrator

# Default: Uses EnsembleClassifier
orchestrator = ClassificationOrchestrator()

# Or use legacy classifier
orchestrator = ClassificationOrchestrator(use_legacy=True)

# Custom ensemble weights
from agent_platform.classification import ScoringWeights
weights = ScoringWeights(rule_weight=0.3, history_weight=0.3, llm_weight=0.4)
orchestrator = ClassificationOrchestrator(ensemble_weights=weights)

# Process emails
emails = [
    {
        'id': 'msg_1',
        'subject': 'Meeting Tomorrow',
        'sender': 'colleague@company.com',
        'body': 'Can we meet at 10am to discuss the budget?',
    }
]

stats = await orchestrator.process_emails(emails, 'gmail_1')

# Stats include:
# - total_processed, high/medium/low confidence counts
# - by_category breakdown
# - extraction counts (tasks, decisions, questions)
# - timing information
```

**Confidence-Based Routing:**
- **≥0.90**: High confidence → Auto-action (label, archive)
- **0.65-0.90**: Medium → Add to review queue
- **<0.65**: Low → Mark for manual review

**File:** `agent_platform/orchestration/classification_orchestrator.py:1`

### 5. Memory System

Memory-Objects are derived from Events (Event-First principle):

```python
from agent_platform.memory import MemoryService

memory = MemoryService()

# Save extracted task to memory
await memory.save_task(
    email_id="msg_123",
    account_id="gmail_1",
    task={
        'description': 'Review Q4 report',
        'deadline': '2025-11-25',
        'priority': 'high',
        'requires_action_from_me': True,
    }
)

# Query active tasks
tasks = await memory.get_active_tasks(account_id="gmail_1")

# Query decisions
decisions = await memory.get_pending_decisions(account_id="gmail_1")
```

**Memory Tables:**
- `memory_tasks`: Extracted tasks with status tracking
- `memory_decisions`: Extracted decisions with resolution tracking
- `memory_questions`: Extracted questions with answer tracking
- `journal_entries`: Daily journal summaries

### 6. Database Schema

SQLAlchemy models in `agent_platform/db/models.py`:

**Event Tables:**
- `events`: Immutable event log (all actions)

**Memory Tables:**
- `memory_tasks`: Tasks extracted from emails
- `memory_decisions`: Decisions extracted from emails
- `memory_questions`: Questions extracted from emails
- `journal_entries`: Daily journal summaries

**Email Processing Tables:**
- `processed_emails`: Email processing history with classifications
- `sender_preferences`: Learned preferences (EMA-based)
- `review_queue`: Medium-confidence emails for review

## Common Development Commands

### Setup and Initialization

```bash
# Initial setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database initialization
python migrations/run_migration.py

# Verify database
python scripts/setup/verify_db.py
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/classification/ -v          # Classification tests
pytest tests/integration/ -v             # Integration tests
pytest tests/extraction/ -v              # Extraction tests
pytest tests/events/ -v                  # Event system tests
pytest tests/memory/ -v                  # Memory system tests

# Run specific test file
pytest tests/classification/test_ensemble_classifier.py -v

# Run with coverage
pytest tests/ --cov=agent_platform --cov-report=html
```

### Testing Email Classification

```bash
# Test classification system (interactive)
PYTHONPATH=. python scripts/operations/run_classifier.py

# Analyze mailbox history (initialize sender preferences)
PYTHONPATH=. python scripts/operations/analyze_mailbox_history.py

# Test full workflow (classification + extraction)
PYTHONPATH=. python scripts/operations/run_full_workflow.py
```

### Journal Generation

```bash
# Generate journal for today (single account)
PYTHONPATH=. python scripts/operations/run_journal_generator.py gmail_1

# Generate for specific date
PYTHONPATH=. python scripts/operations/run_journal_generator.py gmail_1 --date 2025-11-20

# Generate for all accounts
PYTHONPATH=. python scripts/operations/run_journal_generator.py --all

# Export to markdown files
PYTHONPATH=. python scripts/operations/run_journal_generator.py gmail_1 --export

# Custom output directory
PYTHONPATH=. python scripts/operations/run_journal_generator.py gmail_1 --export --output-dir ./my_journals
```

### Scheduler (Automated Operations)

```bash
# Run scheduler for automated operations
PYTHONPATH=. python scripts/operations/run_scheduler.py

# Scheduled jobs:
# - Inbox check: Every 1 hour (configurable)
# - Monthly backup: Day 1 at 3 AM (configurable)
# - Journal generation: Daily at 8 PM (configurable)
# - Spam cleanup: Daily at 2 AM
```

## Critical Implementation Details

### Ensemble vs Legacy Classifier

**When to use Ensemble (DEFAULT):**
- Production scenarios (parallel execution, better confidence)
- When you need agreement detection
- When you want flexible weight configuration
- When you want smart LLM skip with cost savings

**When to use Legacy:**
- Backwards compatibility testing
- Budget-conscious scenarios (more aggressive LLM skipping)
- Comparison benchmarks

**Performance Comparison:**
```
Ensemble: ~1-3s (all layers parallel), higher confidence
Legacy:   ~0.5-3s (early stopping), variable time
```

### LLM Provider Configuration

Two providers with automatic fallback:

```python
from agent_platform.llm import get_llm_client

# Automatically selects Ollama (primary) or OpenAI (fallback)
client = get_llm_client()

# Force specific provider
client = get_llm_client(provider="openai")
client = get_llm_client(provider="ollama")
```

**Environment Variables:**
```env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o

OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b
```

### Confidence Thresholds

Configuration in `ClassificationOrchestrator`:

```python
# Phase 2 (Ensemble) - Higher thresholds due to better confidence
HIGH_CONFIDENCE_THRESHOLD = 0.90   # Auto-action
MEDIUM_CONFIDENCE_THRESHOLD = 0.65  # Review queue

# Phase 1 (Legacy) - Lower thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60
```

### Learning System (EMA)

The system learns from user actions using Exponential Moving Average:

```python
# Learning rate: 15% new, 85% history
new_importance = 0.15 * action_importance + 0.85 * old_importance

# Example:
# Old: importance = 0.60
# User replies (action_importance = 0.85)
# New: 0.15 * 0.85 + 0.85 * 0.60 = 0.6375
```

**Tracked Actions:**
- Reply → High importance (0.85)
- Archive → Medium importance (0.5)
- Delete → Low importance (0.2)
- Star → Very high importance (0.95)

**File:** `agent_platform/feedback/tracker.py:1`

### Journal Generation

Daily journals are generated from events and memory-objects:

```python
from agent_platform.journal import JournalGenerator
from datetime import datetime

generator = JournalGenerator()

# Generate journal for specific day
journal = await generator.generate_daily_journal(
    account_id="gmail_1",
    date=datetime(2025, 11, 20)
)

# Export to markdown file
filepath = generator.export_to_file(
    journal_entry=journal,
    account_id="gmail_1",
    output_dir="journals"  # Creates journals/gmail_1/2025-11-20.md
)

# Journal includes:
# - Email summary (counts by category)
# - Extracted tasks (with priorities)
# - Pending decisions
# - Unanswered questions
# - Top senders
# - Important items (high-priority tasks, urgent decisions/questions)
```

**Output Format:** Markdown with structured sections (see `docs/journal_format.md`)

**File Structure:**
```
journals/
├── gmail_1/
│   ├── 2025-11-20.md
│   └── 2025-11-21.md
├── gmail_2/
│   └── 2025-11-20.md
└── gmail_3/
    └── 2025-11-20.md
```

**Scheduled Generation:**
- Automatic: Daily at 8 PM (configurable via `JOURNAL_GENERATION_HOUR`)
- Manual: Use `scripts/operations/run_journal_generator.py`
- Idempotent: Generating twice for same date returns same journal

**File:** `agent_platform/journal/generator.py:1`

## Database Access Patterns

Use context manager for database sessions:

```python
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail

with get_db() as db:
    email_record = ProcessedEmail(
        account_id="gmail_1",
        email_id="msg_123",
        category="wichtig",
        confidence=0.92
    )
    db.add(email_record)
    # Commit happens automatically on exit
```

## Async Execution Patterns

All operations use async/await:

```python
import asyncio

# Parallel execution
results = await asyncio.gather(
    classify_email(email1, classifier),
    classify_email(email2, classifier),
    classify_email(email3, classifier),
)

# Sequential with delays (rate limiting)
for email in emails:
    result = await process_email(email)
    await asyncio.sleep(0.5)
```

## Common Pitfalls

1. **Ensemble vs Legacy:** Always use `EnsembleClassifier` for new code unless specifically testing legacy behavior

2. **Event Logging:** ALWAYS log events after actions. Missing event logs break the Digital Twin architecture.

3. **Database Sessions:** Always use `with get_db() as db:` pattern, never create sessions manually

4. **Pydantic Models:** When defining structured outputs, use Field descriptions - they're included in LLM prompts

5. **Smart LLM Skip:** Only works with `EnsembleClassifier(smart_llm_skip=True)`, not with legacy classifier

6. **Async/Await:** All classification and extraction operations are async. Don't forget `await`.

## Testing Strategy

**Unit Tests:**
- Test individual layers (Rule, History, LLM)
- Test ensemble combining logic
- Test extraction agent
- Test event logging

**Integration Tests:**
- Test classification + extraction pipeline
- Test orchestrator workflow
- Test ensemble vs legacy comparison
- Test journal generation

**E2E Tests:**
- Test with real Gmail API
- Test complete workflows

**File Locations:**
- `tests/classification/` - Classification unit tests
- `tests/integration/` - Integration tests
- `tests/extraction/` - Extraction tests
- `tests/events/` - Event system tests
- `tests/memory/` - Memory system tests

## Code Quality Guidelines

1. **Type Hints:** Use type hints for all function parameters and return values
2. **Pydantic Models:** Use Pydantic models for all data structures
3. **Event Logging:** Log events for all state changes
4. **Error Handling:** Use try-except with specific exceptions
5. **Testing:** Write tests for all new features (unit + integration)
6. **Documentation:** Update docstrings and CLAUDE.md for architectural changes

## Environment Variables

Critical `.env` variables:

```env
# LLM Providers
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b

# Classification Thresholds
IMPORTANCE_CONFIDENCE_HIGH_THRESHOLD=0.85
IMPORTANCE_CONFIDENCE_MEDIUM_THRESHOLD=0.6

# Scheduler Settings
INBOX_CHECK_INTERVAL_HOURS=1
BACKUP_DAY_OF_MONTH=1
BACKUP_HOUR=3
JOURNAL_GENERATION_HOUR=20  # 8 PM (24-hour format)

# Database
DATABASE_URL=sqlite:///platform.db
```

## Project Structure

```
agent_platform/
├── classification/           # Phase 1-2 Classification System
│   ├── ensemble_classifier.py    # Phase 2: Parallel 3-layer
│   ├── legacy_classifier.py      # Phase 1: Early-stopping
│   ├── importance_rules.py       # Rule Layer
│   ├── importance_history.py     # History Layer (EMA)
│   ├── importance_llm.py         # LLM Layer
│   └── models.py                 # Pydantic models
│
├── extraction/               # Email Extraction System
│   ├── extraction_agent.py       # Main extraction agent
│   ├── models.py                 # Task/Decision/Question models
│   └── prompts.py                # LLM prompts
│
├── events/                   # Event-Log System
│   ├── event_types.py            # Event type enums
│   └── event_service.py          # Event logging API
│
├── memory/                   # Memory-Objects System
│   ├── memory_service.py         # Memory CRUD operations
│   └── models.py                 # Memory object models
│
├── journal/                  # Journal Generation
│   └── generator.py              # Daily journal generator
│
├── orchestration/            # Workflow Orchestration
│   └── classification_orchestrator.py  # Main orchestrator
│
├── feedback/                 # Learning System
│   ├── tracker.py                # Feedback tracking (EMA)
│   └── checker.py                # Background checker
│
├── review/                   # Review Queue System
│   ├── queue_manager.py          # Queue management
│   └── digest_generator.py       # Daily digest
│
├── llm/                      # LLM Provider Abstraction
│   └── providers.py              # Ollama + OpenAI
│
├── db/                       # Database Layer
│   ├── models.py                 # SQLAlchemy models
│   └── database.py               # Session management
│
└── core/                     # Core Configuration
    └── config.py                 # Configuration constants

tests/                        # 80+ test functions
├── classification/           # Classification tests
├── integration/              # Integration tests
├── extraction/               # Extraction tests
├── events/                   # Event system tests
└── memory/                   # Memory system tests
```

## Next Steps (Post-Phase 2)

See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) and [docs/VISION.md](docs/VISION.md) for:
- Phase 3: Twin Core (Proactive suggestions)
- Phase 4: Additional modules (Calendar, Finance, etc.)
- Phase 5: Cross-domain intelligence
