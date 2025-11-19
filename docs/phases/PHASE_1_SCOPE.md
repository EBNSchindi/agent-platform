# Phase 1 - E-Mail Intake + Analyse + Tagesjournal

**MVP für Digital Twin Plattform**

---

## 🎯 Phase-1-Ziel

**Ein funktionierendes E-Mail-Verarbeitungssystem, das:**
- E-Mails einliest
- Intelligent analysiert und klassifiziert
- Tasks, Decisions und Questions extrahiert
- Ein tägliches Journal generiert
- Feedback-Loops implementiert (HITL)

**Scope:** Nur E-Mails als Input-Kanal
**Dauer:** 2-3 Monate
**Status:** In Entwicklung (Week 1-2 abgeschlossen)

---

## ✅ Was bereits existiert (Week 1-2)

### 1. Input Hub (E-Mail)
**Status:** ✅ Vollständig implementiert

**Implementierte Features:**
- Gmail API Integration (OAuth2)
- IMAP/SMTP Support (Ionos)
- Multi-Account Support (3x Gmail + 1x Ionos)
- Email-Fetching (unread emails)
- Token-Management (auto-refresh)

**Code:**
- `modules/email/tools/gmail_tools.py` (Gmail API)
- `modules/email/tools/ionos_tools.py` (IMAP/SMTP)

---

### 2. Analysis Engine (Classification)
**Status:** ✅ Vollständig implementiert

**3-Layer Classification Pipeline:**
```
Email Input
    │
    ▼
┌─────────────────────────────────────┐
│   Layer 1: RULE LAYER               │
│   • Spam patterns (≥95% confidence) │
│   • Newsletter patterns (≥85%)      │
│   • Auto-reply detection (≥90%)     │
│   • Fast: <1ms per email            │
└────────────┬────────────────────────┘
             │ confidence < 0.85
             ▼
┌─────────────────────────────────────┐
│   Layer 2: HISTORY LAYER            │
│   • Sender preferences (EMA)        │
│   • Domain preferences              │
│   • Fast: <10ms per email           │
└────────────┬────────────────────────┘
             │ confidence < 0.85
             ▼
┌─────────────────────────────────────┐
│   Layer 3: LLM LAYER                │
│   • Ollama (gptoss20b) - Primary    │
│   • OpenAI (gpt-4o) - Fallback      │
│   • Slow: ~1-3s per email           │
└─────────────────────────────────────┘
```

**Early Stopping:** 60-80% der Emails werden von Rule/History Layers klassifiziert!

**Implementierte Kategorien:**
- `wichtig` - Wichtige persönliche/geschäftliche Nachrichten
- `action_required` - Dringende Aktionen erforderlich
- `nice_to_know` - Informativ, keine sofortige Aktion
- `newsletter` - Newsletter, Marketing
- `system_notifications` - Automatische System-Benachrichtigungen
- `spam` - Unerwünschte Emails

**Code:**
- `agent_platform/classification/importance_rules.py` (Rule Layer)
- `agent_platform/classification/importance_history.py` (History Layer)
- `agent_platform/classification/importance_llm.py` (LLM Layer)
- `agent_platform/classification/unified_classifier.py` (Orchestration)
- `agent_platform/classification/agents/` (OpenAI Agents SDK wrappers)

---

### 3. Memory System (Partial)
**Status:** ✅ Teilweise implementiert

**Existierende Memory-Objects:**

#### ProcessedEmail
```python
class ProcessedEmail(Base):
    email_id: str
    account_id: str
    category: str
    importance: float
    confidence: float
    layer_used: str
    processed_at: datetime
```

#### SenderPreference (EMA Learning)
```python
class SenderPreference(Base):
    account_id: str
    sender_email: str
    sender_domain: str
    total_emails_received: int
    reply_rate: float  # EMA α=0.15
    archive_rate: float
    delete_rate: float
    avg_time_to_reply_hours: float
```

#### DomainPreference
```python
class DomainPreference(Base):
    account_id: str
    domain: str
    total_emails_received: int
    reply_rate: float  # EMA α=0.15
    archive_rate: float
```

**Code:**
- `agent_platform/db/models.py` (Database Models)
- `agent_platform/db/database.py` (Session Management)
- `agent_platform/feedback/tracker.py` (EMA Learning)

---

### 4. Review & Feedback System
**Status:** ✅ Vollständig implementiert

**Implementierte Features:**
- Review Queue (medium-confidence emails)
- Daily Digest (HTML Email mit Action Buttons)
- Feedback Tracking (reply/archive/delete/star)
- EMA Learning (α=0.15) aus User-Aktionen

**Code:**
- `agent_platform/review/queue_manager.py`
- `agent_platform/review/digest_generator.py`
- `agent_platform/review/review_handler.py`
- `agent_platform/feedback/tracker.py`
- `agent_platform/feedback/checker.py`

---

### 5. Orchestration & Scheduling
**Status:** ✅ Vollständig implementiert

**Scheduled Jobs:**
- Daily Digest: 9 AM
- Feedback Check: Every hour
- Queue Cleanup: 2 AM

**Code:**
- `agent_platform/orchestration/classification_orchestrator.py`
- `agent_platform/orchestration/scheduler_jobs.py`
- `scripts/operations/run_scheduler.py`

---

### 6. Tests & Monitoring
**Status:** ✅ Vollständig implementiert

**Test Coverage:**
- 23/23 Tests passing (100%)
- E2E Tests mit real Gmail
- Agent Migration Tests (OpenAI Agents SDK)

**Code:**
- `tests/classification/` (4 tests)
- `tests/integration/` (2 E2E tests)
- `tests/feedback/` (6 tests)
- `tests/review/` (7 tests)
- `tests/agents/` (2 migration tests)

---

## 🔄 Was noch fehlt für Phase 1 MVP

### 1. Event-Log System
**Status:** ❌ Nicht implementiert

**Ziel:**
- Alle Aktionen als unveränderliche Events speichern
- Event-Types:
  - `EMAIL_RECEIVED`
  - `EMAIL_ANALYZED`
  - `EMAIL_CLASSIFIED`
  - `TASK_EXTRACTED`
  - `DECISION_EXTRACTED`
  - `QUESTION_EXTRACTED`
  - `USER_FEEDBACK` (reply/archive/delete)
  - `JOURNAL_GENERATED`

**Implementierung:**
```python
class Event(Base):
    event_id: str (UUID)
    event_type: str
    timestamp: datetime
    account_id: str
    email_id: Optional[str]
    payload: JSON
    metadata: JSON
```

**Priorität:** 🔥 Hoch (Grundlage für alles Weitere)

---

### 2. Erweiterte E-Mail-Analyse
**Status:** ❌ Nicht implementiert

**Ziel:**
- Über Klassifikation hinausgehen
- Semantic Analysis für Extraktion

**Neue Analyse-Funktionen:**

#### Zusammenfassung
```python
class EmailSummary(BaseModel):
    summary: str  # 2-3 Sätze Zusammenfassung
    key_points: list[str]  # 3-5 wichtigste Punkte
    sentiment: str  # positive/neutral/negative
```

#### Task-Extraktion
```python
class ExtractedTask(BaseModel):
    task_description: str
    priority: str  # high/medium/low
    deadline: Optional[str]
    context: str  # Kontext aus Email
```

#### Decision-Extraktion
```python
class ExtractedDecision(BaseModel):
    decision_question: str
    options: list[str]
    deadline: Optional[str]
    context: str
```

#### Question-Extraktion
```python
class ExtractedQuestion(BaseModel):
    question: str
    requires_answer: bool
    context: str
```

**Implementierung:**
- Neuer Agent: `ExtractionAgent` (OpenAI Agents SDK)
- LLM-basiert (Ollama-first + OpenAI fallback)
- Structured Outputs (Pydantic)

**Priorität:** 🔥 Hoch (Kernfunktion)

---

### 3. Memory-Objects erweitern
**Status:** ❌ Nicht implementiert

**Neue Memory-Objects:**

#### Task
```python
class Task(Base):
    task_id: str (UUID)
    source_email_id: str
    description: str
    priority: str
    deadline: Optional[datetime]
    status: str  # open/in_progress/completed/cancelled
    created_at: datetime
    updated_at: datetime
```

#### Decision
```python
class Decision(Base):
    decision_id: str (UUID)
    source_email_id: str
    question: str
    options: list[str] (JSON)
    deadline: Optional[datetime]
    status: str  # pending/decided/cancelled
    decision_made: Optional[str]
    decided_at: Optional[datetime]
```

#### Question
```python
class Question(Base):
    question_id: str (UUID)
    source_email_id: str
    question: str
    requires_answer: bool
    status: str  # open/answered/cancelled
    answer: Optional[str]
    answered_at: Optional[datetime]
```

#### JournalEntry
```python
class JournalEntry(Base):
    journal_id: str (UUID)
    date: date
    type: str  # daily/weekly
    content: str  # Markdown
    emails_processed: int
    tasks_extracted: int
    decisions_extracted: int
    questions_extracted: int
    generated_at: datetime
```

**Implementierung:**
- Database Models in `agent_platform/db/models.py`
- Abgeleitet aus Events
- Können korrigiert werden (neue Events)

**Priorität:** 🔥 Hoch (benötigt für Journal)

---

### 4. Tagesjournal-Generierung
**Status:** ❌ Nicht implementiert

**Ziel:**
- Täglich automatisch ein Journal generieren
- Zusammenfassung des Tages aus Events + Memory-Objects

**Journal-Struktur:**
```markdown
# Tagesjournal - 19. November 2025

## 📧 E-Mail-Verarbeitung

**Verarbeitet:** 47 Emails
**Wichtige Emails:** 8
**Action Required:** 5
**Newsletter:** 12
**Spam:** 3

## ✅ Extrahierte Aufgaben (12)

- [ ] Q4 Budget Review vorbereiten (Prio: High, Deadline: 22.11.)
- [ ] Meeting mit Team X planen (Prio: Medium)
- ...

## 🤔 Offene Entscheidungen (3)

- Wahl zwischen Option A und B für Projekt Y (Deadline: 25.11.)
- ...

## ❓ Offene Fragen (5)

- Frage von Kunde Z: "Wann ist das Feature fertig?"
- ...

## 📊 Statistiken

- Durchschnittliche Classification Zeit: 487ms
- Rule Layer Hit Rate: 65%
- LLM Layer Usage: 15%
```

**Implementierung:**
- Neuer Agent: `JournalGenerator` (OpenAI Agents SDK)
- Template-basiert (Markdown)
- Scheduled Job (täglich 20:00 Uhr)
- Export als `.md` File

**Priorität:** 🔶 Medium (nach Extraktion)

---

### 5. HITL Feedback-Interface
**Status:** 🔶 Teilweise implementiert

**Was existiert:**
- ✅ Daily Digest mit Action Buttons
- ✅ Feedback Tracking (reply/archive/delete)
- ✅ EMA Learning aus Feedback

**Was fehlt:**
- ❌ Korrektur-Interface für Klassifikationen
- ❌ Korrektur-Interface für Tasks/Decisions/Questions
- ❌ Bestätigungs-Interface
- ❌ Feedback-Events in Event-Log

**Neue Implementierung:**
- Web-UI (Flask/FastAPI) für Korrekturen
- API Endpoints:
  - `POST /feedback/classification` (Korrektur)
  - `POST /feedback/task` (Korrektur)
  - `POST /feedback/confirm` (Bestätigung)
- Feedback erzeugt Events
- Events fließen zurück in Learning-Loop

**Priorität:** 🔶 Medium (nach Extraktion)

---

## 🎯 Nächste Schritte (Priorisiert)

### Schritt 1: Event-Log System ⭐
**Warum zuerst?**
- Grundlage für alle weiteren Features
- Event-First Architecture ist Kernprinzip
- Nachvollziehbarkeit aller Aktionen

**Tasks:**
1. Database Model für `Event` erstellen
2. Event-Service implementieren (`agent_platform/events/event_service.py`)
3. Bestehende Aktionen mit Events instrumentieren:
   - EMAIL_RECEIVED (bei Email-Fetch)
   - EMAIL_CLASSIFIED (nach Classification)
   - USER_FEEDBACK (bei Feedback-Tracking)
4. Tests für Event-System
5. Migration für Event-Tabelle

**Dauer:** 1-2 Tage

---

### Schritt 2: Erweiterte E-Mail-Analyse (Extraktion) ⭐⭐
**Warum als zweites?**
- Kernfunktion für Phase 1
- Benötigt Event-System (Events für Extraktion)

**Tasks:**
1. `ExtractionAgent` implementieren (OpenAI Agents SDK)
2. Pydantic Models für Structured Outputs:
   - `EmailSummary`
   - `ExtractedTask`
   - `ExtractedDecision`
   - `ExtractedQuestion`
3. LLM Prompts für Extraktion
4. Integration in Classification Pipeline
5. Events erzeugen:
   - TASK_EXTRACTED
   - DECISION_EXTRACTED
   - QUESTION_EXTRACTED
6. Tests für Extraktion

**Dauer:** 2-3 Tage

---

### Schritt 3: Memory-Objects (Tasks, Decisions, Questions) ⭐⭐
**Warum als drittes?**
- Benötigt Event-System + Extraktion
- Grundlage für Journal

**Tasks:**
1. Database Models erstellen:
   - `Task`
   - `Decision`
   - `Question`
2. Service-Layer für Memory-Objects:
   - `agent_platform/memory/task_service.py`
   - `agent_platform/memory/decision_service.py`
   - `agent_platform/memory/question_service.py`
3. Memory-Objects aus Events ableiten
4. API Endpoints für CRUD
5. Tests für Memory-Objects
6. Migration für neue Tabellen

**Dauer:** 2-3 Tage

---

### Schritt 4: Tagesjournal-Generierung ⭐
**Warum als viertes?**
- Benötigt alle vorherigen Schritte
- Showcase für Phase 1

**Tasks:**
1. `JournalGenerator` Agent implementieren
2. Markdown Template für Tagesjournal
3. Scheduled Job (täglich 20:00 Uhr)
4. Export als `.md` File
5. Journal als `JournalEntry` in Database
6. Event: JOURNAL_GENERATED
7. Tests für Journal-Generierung

**Dauer:** 1-2 Tage

---

### Schritt 5: HITL Feedback-Interface ⭐
**Warum als letztes?**
- Ergänzung zu bestehendem System
- Polishing für bessere UX

**Tasks:**
1. Web-UI (Flask/FastAPI) Grundgerüst
2. Korrektur-Interface für Klassifikationen
3. Korrektur-Interface für Tasks/Decisions/Questions
4. Bestätigungs-Interface
5. API Endpoints für Feedback
6. Feedback-Events erzeugen
7. Integration in Learning-Loop

**Dauer:** 3-4 Tage

---

## 📊 Phase 1 MVP - Definition of Done

Phase 1 ist **abgeschlossen**, wenn:

✅ **Event-Log System:**
- [ ] Alle Aktionen werden als Events gespeichert
- [ ] Events sind unveränderlich (Append-Only)
- [ ] Event-Historie ist vollständig nachvollziehbar

✅ **E-Mail-Analyse:**
- [ ] Klassifikation funktioniert (bereits ✅)
- [ ] Zusammenfassung wird generiert
- [ ] Tasks werden extrahiert
- [ ] Decisions werden extrahiert
- [ ] Questions werden extrahiert

✅ **Memory-Objects:**
- [ ] Tasks werden in Database gespeichert
- [ ] Decisions werden in Database gespeichert
- [ ] Questions werden in Database gespeichert
- [ ] Memory-Objects können korrigiert werden

✅ **Tagesjournal:**
- [ ] Journal wird täglich generiert
- [ ] Journal enthält Zusammenfassung + Tasks + Decisions + Questions
- [ ] Journal wird als Markdown exportiert

✅ **HITL Feedback:**
- [ ] Feedback-Interface existiert
- [ ] Korrekturen erzeugen Events
- [ ] Feedback fließt zurück in Learning-Loop

✅ **Tests & Monitoring:**
- [ ] Alle neuen Features haben Tests
- [ ] E2E-Tests für kompletten Workflow
- [ ] System läuft stabil im Produktionsbetrieb

---

## 🚫 Explizit NICHT Teil von Phase 1

❌ Twin Core (Persönlichkeit, Präferenz-Modell)
❌ Chat-Interface (natürliche Konversation)
❌ Knowledge Graph (Visualisierung)
❌ Musteranalyse (über Zeit)
❌ Personen-Analyse (Beziehungen)
❌ Themen-Erkennung (Topics)
❌ Weitere Input-Kanäle (Kalender, Notizen, etc.)
❌ Proaktive Automationen
❌ Wochenjournal (kommt Phase 2)

---

## 📅 Zeitplan (geschätzt)

**Week 1-2:** ✅ Email Classification System (abgeschlossen)
**Week 3:** Event-Log System
**Week 4:** Erweiterte E-Mail-Analyse (Extraktion)
**Week 5:** Memory-Objects (Tasks, Decisions, Questions)
**Week 6:** Tagesjournal-Generierung
**Week 7:** HITL Feedback-Interface
**Week 8:** Testing, Polishing, Documentation

**Gesamt:** ~8 Wochen (2 Monate)

---

## 🎯 Erfolgs-Metriken für Phase 1

- [ ] 90%+ der E-Mails werden korrekt klassifiziert ✅ (bereits erfüllt)
- [ ] Tasks werden mit 80%+ Genauigkeit extrahiert
- [ ] Decisions werden mit 70%+ Genauigkeit extrahiert
- [ ] Questions werden mit 85%+ Genauigkeit extrahiert
- [ ] Tagesjournal wird täglich generiert (100% Uptime)
- [ ] HITL-Feedback wird in 100% der Fälle erfasst
- [ ] System läuft stabil (>99% Uptime)

---

**Status:** Week 1-2 abgeschlossen, Week 3 beginnt mit Event-Log System! 🚀
