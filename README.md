# Email Classification System with Learning

**Intelligentes Email-Klassifizierungssystem mit Multi-Layer-Architektur und adaptivem Lernen**

Ein vollständiges System zur automatischen Klassifizierung von Emails nach Wichtigkeit mit integriertem Feedback-Tracking und Learning-Loop. Entwickelt über 6 Implementierungs-Phasen mit umfassenden Test-Suites.

---

## 🎯 Übersicht

Dieses System klassifiziert eingehende Emails automatisch in 6 Kategorien:
- **wichtig** - Wichtige persönliche oder geschäftliche Nachrichten
- **action_required** - Dringende Aktionen erforderlich
- **nice_to_know** - Informativ, keine sofortige Aktion nötig
- **newsletter** - Newsletter und Marketing-Emails
- **system_notifications** - Automatische System-Benachrichtigungen
- **spam** - Unerwünschte Emails

### Kernfeatures

✅ **3-Layer Classification** (Rule → History → LLM mit Early Stopping)
✅ **Ollama-First Strategie** (Lokal-First mit OpenAI Fallback)
✅ **Adaptive Learning** (Exponential Moving Average)
✅ **Review System** (Daily Digest für medium-confidence Items)
✅ **Feedback Tracking** (Lernt aus User-Aktionen)
✅ **Confidence-based Routing** (Auto-action / Review / Manual)
✅ **Multi-Account Support** (Gmail + IMAP/Ionos)
✅ **Scheduled Jobs** (Daily Digest, Feedback Check, Cleanup)

---

## 📊 Architektur

### 3-Layer Classification Pipeline

```
Email Input
    │
    ▼
┌─────────────────────────────────────┐
│   Layer 1: RULE LAYER               │
│   • Spam patterns (≥95% confidence) │
│   • Newsletter patterns (≥85%)      │
│   • Auto-reply detection (≥90%)     │
│   • System notifications (≥85%)     │
│   • Fast: <1ms per email            │
└────────────┬────────────────────────┘
             │ confidence < 0.85
             ▼
┌─────────────────────────────────────┐
│   Layer 2: HISTORY LAYER            │
│   • Sender preferences (EMA)        │
│   • Domain preferences              │
│   • Reply/archive/delete rates      │
│   • Fast: <10ms per email           │
└────────────┬────────────────────────┘
             │ confidence < 0.85
             ▼
┌─────────────────────────────────────┐
│   Layer 3: LLM LAYER                │
│   • Ollama (gptoss20b) - Primary    │
│   • OpenAI (gpt-4o) - Fallback      │
│   • Context from previous layers    │
│   • Structured outputs (Pydantic)   │
│   • Slow: ~1-3s per email           │
└─────────────────────────────────────┘
             │
             ▼
    ClassificationResult
```

**Early Stopping**: 60-80% der Emails werden von Rule/History Layers klassifiziert → LLM nur für schwierige Fälle!

### Learning Loop

```
User Action (reply/archive/delete)
    ↓
Feedback Tracker
    ↓
Update Sender/Domain Preferences (EMA)
    ↓
History Layer uses updated preferences
    ↓
Better classifications next time!
```

---

## 🆕 OpenAI Agents SDK Migration (Phase 7 - Week 1)

**Status:** ✅ Agent wrappers completed (Day 1-2)

Das System wurde auf **OpenAI Agents SDK** migriert während **100% der Logik preserviert** wurde:

### Neue Agent-basierte Architektur

```python
from agent_platform.classification.agents import AgentBasedClassifier

# Drop-in replacement for UnifiedClassifier
classifier = AgentBasedClassifier()
result = await classifier.classify(email)
```

**Preservation Principle: Extract → Wrap → Orchestrate**
- ✅ Pattern matching (40 keywords, 6 regex patterns) - UNVERÄNDERT
- ✅ EMA learning (α=0.15) - UNVERÄNDERT
- ✅ Early stopping (0.85 threshold) - UNVERÄNDERT
- ✅ Confidence scores (0.95, 0.90, 0.85, 0.80) - UNVERÄNDERT

**Neue Features:**
- 🤖 OpenAI Agents SDK Integration (Labs 1-4 patterns)
- 🔧 Agent als Tools (Rule, History, LLM agents)
- 🔀 Agent Registry kompatibel
- 📊 Identische Performance & Ergebnisse

Siehe [docs/PHASE_7_AGENT_MIGRATION_SUMMARY.md](docs/PHASE_7_AGENT_MIGRATION_SUMMARY.md) für vollständige Details.

---

## 🚀 Quick Start

### Installation

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Setup directories
chmod +x scripts/setup/setup_directories.sh
./scripts/setup/setup_directories.sh

# Database
python scripts/setup/init_database.py
```

### Configuration

```bash
# 1. Copy .env.example → .env
cp .env.example .env

# 2. Add your API keys to .env
# - OPENAI_API_KEY=sk-proj-...
# - GMAIL_2_EMAIL=your-email@gmail.com

# 3. Setup Gmail OAuth2 (see docs/setup/SETUP_GUIDE.md)
python scripts/testing/test_gmail_auth.py
```

### End-to-End Test with Real Gmail

```bash
# Test complete pipeline with real Gmail account
python tests/integration/test_e2e_real_gmail.py

# Expected output:
# ✅ Gmail authentication successful
# ✅ Fetched 10 email(s)
# Processing through classification pipeline...
# ✅ Processed: 10 emails
# Duration: 2.34s
```

### Analyze Mailbox History

```bash
# Analyze last 100-200 emails to initialize system
python scripts/operations/analyze_mailbox_history.py

# Expected output:
# Total Classified: 195
# Average Processing Time: 487ms
# Sender Preferences Initialized: 52
```

### Basic Usage

```python
from agent_platform.classification import UnifiedClassifier, EmailToClassify
import asyncio

async def main():
    classifier = UnifiedClassifier()

    email = EmailToClassify(
        email_id="msg_123",
        account_id="gmail_1",
        sender="boss@company.com",
        subject="Project Deadline",
        body="We need to finish by Friday...",
    )

    result = await classifier.classify(email)

    print(f"Category: {result.category}")
    print(f"Importance: {result.importance:.0%}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Layer: {result.layer_used}")

asyncio.run(main())
```

### All Tests

```bash
# Core classification tests (4/4)
python tests/classification/test_classification_layers.py      # ✅

# Feedback tracking tests (6/6)
python tests/feedback/test_feedback_tracking.py                # ✅

# Review system tests (7/7)
python tests/review/test_review_system.py                      # ✅

# E2E workflow test
python tests/integration/test_e2e_classification_workflow.py   # ✅

# E2E test with real Gmail (NEW)
python tests/integration/test_e2e_real_gmail.py                # ✅

# Agent migration tests (NEW)
python tests/agents/test_agents_quick.py                       # ✅
python tests/agents/test_agent_migration.py                    # ✅

# All tests
pytest tests/
```

---

## 📁 Projektstruktur

```
agent_platform/
├── classification/              # Phases 1-3 (~2,000 Zeilen)
│   ├── importance_rules.py     # Rule Layer
│   ├── importance_history.py   # History Layer
│   ├── importance_llm.py       # LLM Layer
│   ├── models.py               # Pydantic models
│   ├── unified_classifier.py   # Orchestration with logging
│   └── agents/                 # Phase 7 (~2,200 Zeilen)
│       ├── rule_agent.py       # Rule Agent
│       ├── history_agent.py    # History Agent
│       ├── llm_agent.py        # LLM Agent
│       └── orchestrator_agent.py # Orchestrator Agent
│
├── feedback/                    # Phase 4 (~800 Zeilen)
│   ├── tracker.py              # Feedback tracking & EMA
│   └── checker.py              # Background checker
│
├── review/                      # Phase 5 (~1,300 Zeilen)
│   ├── queue_manager.py        # Review queue
│   ├── digest_generator.py     # Daily digest
│   └── review_handler.py       # User reviews
│
├── orchestration/               # Phase 6 (~750 Zeilen)
│   ├── classification_orchestrator.py # Main workflow
│   └── scheduler_jobs.py       # Scheduled jobs
│
├── llm/                         # Phase 1 (~250 Zeilen)
│   └── providers.py            # Ollama + OpenAI
│
├── monitoring.py                # Phase 7 (~400 Zeilen)
│   └── Metrics, logging, daily reports
│
├── db/                          # Database layer
│   ├── models.py               # SQLAlchemy models
│   └── database.py             # Session management
│
└── core/                        # Configuration
    └── config.py               # Constants & config

tests/                           # ~2,500 Zeilen Tests
├── classification/              # Classification tests
├── integration/                 # E2E tests
├── feedback/                    # Feedback tests
├── llm/                        # LLM provider tests
├── review/                     # Review system tests
└── agents/                     # Agent migration tests

scripts/
├── setup/                      # Setup & DB initialization
│   ├── init_database.py
│   ├── verify_db.py
│   └── setup_directories.sh
├── testing/                    # Connection tests
│   ├── test_gmail_auth.py
│   ├── test_openai_connection.py
│   └── test_all_connections.py
└── operations/                 # Operational scripts
    ├── run_classifier.py
    ├── run_responder.py
    ├── run_scheduler.py
    ├── run_full_workflow.py
    └── analyze_mailbox_history.py

docs/                           # Complete documentation
├── phases/                     # Phase completion docs
├── architecture/               # Architecture & design
├── planning/                   # Roadmaps & next steps
└── setup/                      # Setup guides

Total: ~11,700+ Zeilen Production Code (inkl. Phase 7)
```

---

## 📈 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Rule Layer** | <1ms | 40-60% hit rate |
| **History Layer** | <10ms | 20-30% hit rate |
| **LLM Layer** | 1-3s | 10-20% only |
| **Avg Time** | ~500ms | With 60% Rule hits |
| **Accuracy** | 85-95% | After 2 weeks learning |

---

## 🧪 Testing

**23/23 Tests Passing (100%)**

- ✅ Classification Layers (4/4)
- ✅ Unified Classifier (6/6)
- ✅ Feedback Tracking (6/6)
- ✅ Review System (7/7)
- ✅ E2E Integration (validated)

---

## 📚 Dokumentation

### Setup & Operations
- **[SETUP_GUIDE](docs/setup/SETUP_GUIDE.md)** - Kompletter Setup & Konfiguration
- **[DEPLOYMENT](docs/setup/DEPLOYMENT.md)** - Production Deployment
- **[CONNECTION_TESTS](docs/setup/CONNECTION_TESTS.md)** - Connection Testing
- **[QUICKSTART](docs/setup/QUICKSTART.md)** - Quick Start Guide

### Architecture & Planning
- **[ARCHITECTURE_MIGRATION](docs/architecture/ARCHITECTURE_MIGRATION.md)** - OpenAI Agents SDK Migration
- **[PROJECT_SCOPE](docs/architecture/PROJECT_SCOPE.md)** - Project Scope & Goals
- **[PROJECT_SUMMARY](docs/architecture/PROJECT_SUMMARY.md)** - Complete Project Summary
- **[CLAUDE.md](docs/architecture/CLAUDE.md)** - Development Guide für Claude Code
- **[ROADMAP](docs/planning/ROADMAP.md)** - Timeline & Milestones
- **[NEXT_STEPS](docs/planning/NEXT_STEPS.md)** - Future Development

### Phase Documentation
- **[PHASE_1_COMPLETE](docs/phases/PHASE_1_COMPLETE.md)** - Foundation + Ollama
- **[PHASE_2_COMPLETE](docs/phases/PHASE_2_COMPLETE.md)** - Rule + History Layers
- **[PHASE_3_COMPLETE](docs/phases/PHASE_3_COMPLETE.md)** - LLM + Unified Classifier
- **[PHASE_4_COMPLETE](docs/phases/PHASE_4_COMPLETE.md)** - Feedback Tracking
- **[PHASE_5_COMPLETE](docs/phases/PHASE_5_COMPLETE.md)** - Review System
- **[PHASE_6_COMPLETE](docs/phases/PHASE_6_COMPLETE.md)** - Orchestrator Integration
- **[PHASE_7_E2E_TESTING](docs/phases/PHASE_7_E2E_TESTING.md)** - E2E Tests & Monitoring
- **[PHASE_7_AGENT_MIGRATION](docs/PHASE_7_AGENT_MIGRATION_SUMMARY.md)** - OpenAI Agents SDK Migration (Week 1)

---

## 🎓 Konzepte

### Exponential Moving Average (EMA)

```python
# Learning rate: 15% new, 85% history
new_importance = 0.15 * action_importance + 0.85 * old_importance

# Example:
# Old: importance = 0.60
# User replies (action_importance = 0.85)
# New: 0.15 * 0.85 + 0.85 * 0.60 = 0.6375
# → Gradually adapts to new behavior!
```

### Confidence-Based Routing

- **≥0.85**: High confidence → Auto-action
- **0.6-0.85**: Medium → Review queue (daily digest)
- **<0.6**: Low → Manual review flag

### Early Stopping

```
60% emails → Rule Layer stops (high confidence)
25% emails → History Layer stops
15% emails → Need LLM Layer

→ Saves 85% of LLM calls!
```

---

## 🔧 Konfiguration

### Confidence Thresholds

```python
# In ClassificationOrchestrator
HIGH_CONFIDENCE_THRESHOLD = 0.85  # Auto-action
MEDIUM_CONFIDENCE_THRESHOLD = 0.60  # Review queue
```

### Learning Rate

```python
# In FeedbackTracker
LEARNING_RATE = 0.15  # 15% new, 85% history
```

### Scheduler

```python
# Daily Digest: 9 AM
# Feedback Check: Every hour
# Queue Cleanup: 2 AM
```

---

## 🎉 Entwickelt in 6 Phasen

- **Phase 1**: Foundation + Ollama (~600 Zeilen)
- **Phase 2**: Rule + History Layers (~1,400 Zeilen)
- **Phase 3**: LLM + Unified Classifier (~1,000 Zeilen)
- **Phase 4**: Feedback Tracking (~1,200 Zeilen)
- **Phase 5**: Review System (~1,900 Zeilen)
- **Phase 6**: Orchestrator Integration (~1,130 Zeilen)

**Total: ~7,230+ Zeilen Code + Tests**

Alle 23 Tests laufen erfolgreich ✅

---

**Built with:**
- Python 3.10+
- OpenAI Agents SDK patterns
- SQLAlchemy + SQLite
- Pydantic (Structured Outputs)
- APScheduler
- Ollama + OpenAI

**Powered by:**
- Rule-based patterns (fast!)
- Historical learning (EMA)
- LLM intelligence (when needed)
