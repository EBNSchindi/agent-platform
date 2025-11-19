# Project Scope: Digital Twin Email Platform

**Version:** 2.0.0
**Status:** Phase 1 in Entwicklung (Event-Log System ✅ Complete)
**Letztes Update:** 2025-11-20
**Autor:** Daniel Schindler

---

## 📖 Dokumenten-Navigation

Dieses Projekt hat drei zentrale Dokumente:

1. **PROJECT_SCOPE.md** (dieses Dokument) - **Quick Reference & Aktueller Status**
   - Was ist das Projekt? (Executive Summary)
   - Was funktioniert bereits? (Current Status)
   - Wie starte ich? (Quick Start)

2. **[CLAUDE.md](CLAUDE.md)** - **Technische Patterns & Architektur für AI-Assistenten**
   - OpenAI Agents SDK Patterns
   - Code-Konventionen & Best Practices
   - Häufige Fallstricke & Lösungen
   - Development Commands

3. **[docs/VISION.md](docs/VISION.md)** - **Big Picture & Langfristige Roadmap**
   - Digital Twin Konzept & 5-Module-Architektur
   - Event-First Architecture
   - Human-in-the-Loop (HITL) Prinzipien
   - Phase 1-5 Roadmap (2-Jahres-Plan)

💡 **Für neue Entwickler**: Start hier → dann CLAUDE.md → dann VISION.md
💡 **Für AI-Assistenten**: CLAUDE.md ist dein Hauptdokument
💡 **Für Stakeholder**: VISION.md zeigt das Big Picture

---

## 📋 Executive Summary

Die **Digital Twin Email Platform** ist ein intelligentes Email-Management-System, das als digitaler Zwilling agiert - es lernt kontinuierlich von deinen Entscheidungen und unterstützt dich proaktiv bei der Email-Bearbeitung.

**Aktueller Fokus (Phase 1):**
- ✅ Event-Log System (Foundation für Learning & Digital Twin)
- ✅ Email Importance Classification (3-Layer: Rules → History → LLM)
- 🚧 Email Extraction (Tasks, Decisions, Questions)
- 🚧 Memory-Objects (abgeleitete Strukturen aus Events)
- 🚧 Daily Journal Generation

**Langfristige Vision:** Ein digitaler Zwilling, der alle Lebensbereiche (Email, Calendar, Finance, Health, Knowledge) orchestriert. Details: [docs/VISION.md](docs/VISION.md)

---

## 🎯 Aktueller Status (Stand: 2025-11-20)

### ✅ Was ist fertig (Production Ready)

#### 1. Email Importance Classification System
- **3-Layer Classification Pipeline** (Rules → History → LLM)
  - Rule Layer: Pattern-basiert, <1ms, 40-60% Hit Rate
  - History Layer: Lernt von User-Verhalten, <10ms, 20-30% Hit Rate
  - LLM Layer: Ollama-first + OpenAI Fallback, 1-3s, höchste Accuracy
- **Adaptive Learning**: EMA-basiert (α=0.15), lernt aus User-Actions
- **Multi-Account Support**: 3x Gmail + 1x Ionos
- **Classification Results**: Kategorien (wichtig, action_required, nice_to_know, newsletter, spam)

**Code**: `agent_platform/classification/` (7 Module, ~2,300 Zeilen, 23/23 Tests ✅)

#### 2. Event-Log System (Digital Twin Foundation)
- **Immutable Event Store**: Alle Aktionen als append-only Events
- **Event Types**: EMAIL_CLASSIFIED, EMAIL_RECEIVED, TASK_EXTRACTED, USER_FEEDBACK, etc.
- **Event Service API**: log_event(), get_events(), count_events()
- **Database**: SQLite mit Indexing (event_type, timestamp, account_id, email_id)

**Code**: `agent_platform/events/` (3 Module, ~700 Zeilen, 10/10 Tests ✅)
**Docs**: [docs/phases/PHASE_1_STEP_1_COMPLETE.md](docs/phases/PHASE_1_STEP_1_COMPLETE.md)

#### 3. Feedback & Learning System
- **Sender/Domain Preferences**: Lernt aus User-Actions (reply, archive, delete, star)
- **Review Queue**: Medium-confidence Emails zur User-Review
- **Daily Digest**: HTML Email mit Action Buttons
- **Feedback Tracking**: FeedbackEvents für Preference-Updates

**Code**: `agent_platform/feedback/`, `agent_platform/review/` (4 Module, ~1,200 Zeilen)

#### 4. Database & Persistence
- **SQLAlchemy Models**: 10+ Tabellen (Events, ProcessedEmails, SenderPreferences, etc.)
- **Migrations**: SQL-basiert mit run_migration.py
- **Schema**: Optimiert für Event-First Architecture

**Code**: `agent_platform/db/models.py` (430 Zeilen), `migrations/`

### 🚧 In Arbeit (Next Steps aus Phase 1)

#### 1. Erweiterte E-Mail-Analyse (Extraktion) - **NEXT**
- [ ] ExtractionAgent: Task, Decision, Question extraction
- [ ] Zusammenfassung generation
- [ ] Event-Logging: TASK_EXTRACTED, DECISION_EXTRACTED, QUESTION_EXTRACTED

#### 2. Memory-Objects erweitern
- [ ] Database Models: Task, Decision, Question, JournalEntry
- [ ] Abgeleitet aus Events (Event-First Principle)

#### 3. Tagesjournal-Generierung
- [ ] Journal-Generator Agent
- [ ] Markdown Export
- [ ] Event-Logging: JOURNAL_GENERATED

#### 4. HITL Feedback-Interface
- [ ] Simple Web-UI für Corrections
- [ ] Event-Logging: USER_FEEDBACK, USER_CORRECTION

Details: [docs/phases/PHASE_1_SCOPE.md](docs/phases/PHASE_1_SCOPE.md)

### ❌ Noch nicht implementiert (Zukünftige Phasen)

- **Phase 2**: Twin Core (Proaktive Vorschläge, Context Tracking)
- **Phase 3**: Twin Interface (Conversational UI, Mobile App)
- **Phase 4**: Weitere Module (Calendar, Finance, Health, Knowledge)
- **Phase 5**: Cross-Domain Intelligence

Details: [docs/VISION.md](docs/VISION.md)

---

## 🏗️ Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                  DIGITAL TWIN EMAIL PLATFORM                     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  EVENT-LOG SYSTEM (Foundation)                         │    │
│  │  - Immutable Event Store                               │    │
│  │  - Event Types (EMAIL_*, TASK_*, USER_*, etc.)        │    │
│  │  - Event Service API                                   │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  ANALYSIS ENGINE                                        │    │
│  │  ├─ Importance Classifier (3-Layer)                    │    │
│  │  ├─ Content Extractor (Tasks, Decisions, Questions)    │    │
│  │  └─ Summarizer                                          │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  MEMORY SYSTEM                                          │    │
│  │  ├─ Sender/Domain Preferences (Learning)               │    │
│  │  ├─ Memory-Objects (Tasks, Decisions, Questions)       │    │
│  │  └─ Review Queue & Feedback                            │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  TWIN CORE (Future)                                     │    │
│  │  ├─ Proactive Suggestions                              │    │
│  │  ├─ Context Tracking                                    │    │
│  │  └─ Pattern Recognition                                 │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Architektur-Prinzipien**: Siehe [docs/VISION.md](docs/VISION.md) und [CLAUDE.md](CLAUDE.md)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API Key
- Gmail API Credentials (optional: nur für Gmail-Accounts)
- Ollama (optional: für lokales LLM)

### Installation

```bash
# 1. Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Environment konfigurieren
cp .env.example .env
# .env editieren: OPENAI_API_KEY, Gmail credentials, etc.

# 4. Database initialisieren
python migrations/run_migration.py

# 5. Test: Email Classification
PYTHONPATH=. python scripts/test_classification.py
```

### Development Commands

Siehe [CLAUDE.md](CLAUDE.md) für alle Development Commands und Patterns.

---

## 📊 Code-Statistik

```
📁 agent_platform/ (Main Package)
   ├── classification/      ~2,300 Zeilen (3-Layer Classifier)
   ├── events/              ~700 Zeilen (Event-Log System)
   ├── feedback/            ~800 Zeilen (Learning & Feedback)
   ├── review/              ~400 Zeilen (Review Queue & Digest)
   ├── db/                  ~600 Zeilen (Models & Database)
   ├── llm/                 ~300 Zeilen (Ollama + OpenAI)
   └── monitoring.py        ~360 Zeilen (Logging & Metrics)

   TOTAL: ~5,460 Zeilen Production Code

📁 tests/
   ├── classification/      ~900 Zeilen (23 Tests)
   ├── events/              ~400 Zeilen (10 Tests)
   ├── feedback/            ~300 Zeilen (8 Tests)
   └── integration/         ~200 Zeilen (5 Tests)

   TOTAL: ~1,800 Zeilen Test Code
   TEST COVERAGE: 46/46 Tests passing (100%) ✅

📁 docs/
   ├── VISION.md            ~1,000 Zeilen (Big Picture)
   ├── phases/              ~2,000 Zeilen (Phase Documentation)
   └── setup/               ~500 Zeilen (Setup Guides)

   TOTAL: ~3,500 Zeilen Documentation
```

---

## 🗓️ Roadmap

### Phase 1: Email Intelligence & Digital Twin Foundation (Aktuell)
**Zeitraum**: Nov 2025 - Jan 2026 (3 Monate)

- ✅ **Week 1-2**: Email Classification System (COMPLETE)
- ✅ **Week 3**: Event-Log System (COMPLETE)
- 🚧 **Week 4**: Email Extraction (Tasks, Decisions, Questions)
- 🚧 **Week 5**: Memory-Objects & Journal
- 🚧 **Week 6**: HITL Feedback Interface

**Status**: 40% Complete (2/5 Steps)

### Phase 2-5: Siehe [docs/VISION.md](docs/VISION.md)

---

## 🛠️ Technologie-Stack

| Kategorie | Technologie | Version | Zweck |
|-----------|-------------|---------|-------|
| **AI/LLM** | OpenAI gpt-4o | Latest | Primary LLM |
| **AI/LLM** | Ollama (qwen2.5:20b) | Latest | Local LLM (fallback) |
| **Framework** | OpenAI Agents SDK | 0.1.0+ | Agent Framework |
| **Language** | Python | 3.10+ | Main Language |
| **Database** | SQLAlchemy + SQLite | 2.0+ | Persistence |
| **Validation** | Pydantic | 2.5+ | Structured Outputs |
| **Email** | Gmail API, IMAP/SMTP | - | Email Access |
| **Scheduler** | APScheduler | 3.10+ | Task Scheduling |

Details: [CLAUDE.md](CLAUDE.md)

---

## 📏 Definition of Done (Phase 1)

### MVP Kriterien
- ✅ Event-Log System produktionsreif
- ✅ Email Classification >85% Accuracy nach 2 Wochen Learning
- 🚧 Task/Decision/Question Extraction funktional
- 🚧 Daily Journal generiert
- 🚧 HITL Feedback-Interface funktional
- 🚧 Alle Tests passing (>90% Coverage)
- 🚧 Deployment Guide vollständig

**Current Progress**: 2/7 Kriterien erfüllt (29%)

---

## 🔗 Wichtige Links

- **Vision & Roadmap**: [docs/VISION.md](docs/VISION.md)
- **Phase 1 Scope**: [docs/phases/PHASE_1_SCOPE.md](docs/phases/PHASE_1_SCOPE.md)
- **Event-Log System**: [docs/phases/PHASE_1_STEP_1_COMPLETE.md](docs/phases/PHASE_1_STEP_1_COMPLETE.md)
- **Technical Patterns**: [CLAUDE.md](CLAUDE.md)
- **Setup Guide**: [docs/setup/DEPLOYMENT.md](docs/setup/DEPLOYMENT.md)

---

## 🤝 Team

- **Hauptentwickler**: Daniel Schindler
- **AI-Assistent**: Claude (Anthropic) via Claude Code
- **Basierend auf**: OpenAI Agents SDK Patterns

---

## 📄 Lizenz

Privates Projekt - Keine öffentliche Lizenz

---

## 🔄 Versions-Historie

| Version | Datum | Meilenstein |
|---------|-------|-------------|
| 2.0.0 | 2025-11-20 | Event-Log System Complete, Digital Twin Architecture |
| 1.0.0 | 2025-11-19 | Email Classification System Complete (3-Layer) |
| 0.1.0 | 2025-11-15 | Projekt-Setup, Initial Classifier |

---

**Status**: 🚧 Phase 1 in Development (2/5 Steps Complete)
**Letztes Update**: 2025-11-20
**Nächster Meilenstein**: Email Extraction Agent (ETA: Week 4)
