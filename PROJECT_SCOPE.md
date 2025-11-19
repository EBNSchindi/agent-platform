# Project Scope: Agent Platform

**Version:** 1.0.0
**Status:** MVP Complete
**Letztes Update:** 2025-11-19
**Autor:** Daniel Schindler

---

## 📋 Executive Summary

Die **Agent Platform** ist eine modulare Multi-Agent-Plattform zur Automatisierung verschiedener Lebensbereiche. Das System basiert auf OpenAI Agents SDK und implementiert bewährte Patterns aus dem OpenAI Agent-Ökosystem.

**Aktueller Fokus:** Email-Posteingang-Automatisierung mit Multi-Account-Support, intelligenter Klassifizierung, Draft-Generierung und automatischen Backups.

**Zukünftige Erweiterungen:** Calendar-Modul, Finance-Modul, Knowledge-Management und weitere Lebensbereiche.

---

## 🎯 Projektziele

### Primärziele (MVP - ✅ Erreicht)

1. **Automatisierung des Email-Posteingangs**
   - Multi-Account-Support (3x Gmail + 1x Ionos)
   - Intelligente Spam-Klassifizierung
   - Automatische Draft-Generierung für Antworten
   - Monatliche Backups auf Backup-Account

2. **Modulare, skalierbare Architektur**
   - Plugin-System für verschiedene Agent-Module
   - Zentrale Agent-Registry
   - Wiederverwendbare Komponenten (Guardrails, Tools)

3. **Sichere Automatisierung**
   - Input/Output-Guardrails
   - PII-Erkennung
   - Phishing-Detection
   - Compliance-Checks

4. **Flexibles Modi-System**
   - Draft Mode: Generiert Drafts zur manuellen Review
   - Auto-Reply Mode: Sendet bei hoher Confidence
   - Manual Mode: Nur Klassifizierung

### Sekundärziele (Roadmap)

1. **Web-Oberfläche (Dashboard)**
   - Visualisierung aller Agents
   - Run-History und Logs
   - Agent-Konfiguration via UI

2. **REST API**
   - HTTP-Zugriff auf alle Agents
   - Webhook-Support für Integrationen

3. **Weitere Module**
   - Calendar-Modul (Meeting-Scheduling, Reminder)
   - Finance-Modul (Transaktions-Tracking, Budget)
   - Knowledge-Modul (Note-Organizing, Research)

4. **Cross-Module-Workflows**
   - Email → Calendar Integration (Meeting-Requests)
   - Email → Finance Integration (Rechnung → Budget)

---

## 🏗️ Architektur

### Überblick

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Platform                        │
│  ┌────────────────────────────────────────────────┐    │
│  │  Platform Core                                  │    │
│  │  - Agent Registry (Module & Agents verwalten)  │    │
│  │  - Config System (Multi-Account, Modi)         │    │
│  │  - Database (SQLite/Postgres - Run-Logging)   │    │
│  │  - Scheduler (APScheduler - zeitgesteuert)    │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Modules (Plugins)                             │    │
│  │  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │ Email Module │  │ Calendar (🚧)│           │    │
│  │  │  ✅ Complete │  │   Planned    │           │    │
│  │  └──────────────┘  └──────────────┘           │    │
│  │  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │ Finance (🚧) │  │ Other...     │           │    │
│  │  │   Planned    │  │              │           │    │
│  │  └──────────────┘  └──────────────┘           │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Technologie-Stack

| Layer | Technologie | Version | Zweck |
|-------|-------------|---------|-------|
| **AI/Agents** | OpenAI Agents SDK | Latest | Agent-Framework |
| **LLM** | GPT-4o-mini | Latest | AI-Model (schnell, kostengünstig) |
| **Backend** | Python | 3.10+ | Hauptsprache |
| **Email APIs** | Gmail API, IMAP/SMTP | - | Email-Zugriff |
| **Database** | SQLAlchemy + SQLite | 2.0+ | Persistierung |
| **Scheduler** | APScheduler | 3.10+ | Zeitsteuerung |
| **Validation** | Pydantic | 2.5+ | Structured Outputs |
| **Auth** | OAuth 2.0 | - | Gmail-Authentifizierung |

### Design Patterns

1. **Plugin-Architektur**
   - Module sind eigenständige Plugins
   - Zentrale Registry für Discovery
   - Lose Kopplung

2. **Agent-as-Tool Pattern** (aus 2_openai/Lab 2)
   - Agents werden als Tools für andere Agents verwendet
   - Responder-Orchestrator nutzt 3 spezialisierte Sub-Agents

3. **Structured Outputs** (aus 2_openai/Lab 3)
   - Pydantic-Models für type-safe Kommunikation
   - Classifier → EmailClassification
   - Responder → EmailResponse

4. **Guardrails Pattern** (aus 2_openai/Lab 3)
   - Input Guardrails: Vor Agent-Ausführung
   - Output Guardrails: Nach Agent-Ausführung
   - Tripwire-Mechanismus für kritische Fälle

5. **Orchestration Pattern** (aus 2_openai/Lab 4)
   - Master-Orchestrator koordiniert Workflow
   - Parallel-Execution für Batch-Processing
   - Zustandsverwaltung über Context Store

---

## ✅ Scope: Was ist DRIN (MVP)

### Email-Modul (100% implementiert)

#### Features
- ✅ Multi-Account-Support (3x Gmail + 1x Ionos)
- ✅ Unread Email Fetching (Gmail API + IMAP)
- ✅ Email-Klassifizierung:
  - Spam-Detection
  - Important/Normal/Auto-Reply-Candidate
  - Confidence-Scoring
  - Urgency-Assessment
- ✅ Draft-Generierung:
  - 3 Tone-Varianten (Professional, Friendly, Brief)
  - Automatic Tone Selection
  - Confidence-based Quality-Assessment
- ✅ Modi-System:
  - Draft Mode (generiert Drafts)
  - Auto-Reply Mode (sendet bei hoher Confidence)
  - Manual Mode (nur Klassifizierung)
  - Pro-Account konfigurierbar
- ✅ Guardrails:
  - PII-Erkennung (Input)
  - Phishing-Detection (Input)
  - Compliance-Checks (Output)
  - Risk-Assessment
- ✅ Backup:
  - Monatliches vollständiges Backup
  - Backup auf separatem Gmail-Account
  - Alle 4 Source-Accounts
- ✅ Scheduler:
  - Stündliche Inbox-Checks
  - Monatliches Backup (1. Tag, 3 Uhr)
  - Täglicher Spam-Cleanup (2 Uhr)

#### Tools
- ✅ Gmail API Tools (fetch, create_draft, label, archive, send)
- ✅ Ionos IMAP/SMTP Tools

#### Agents
- ✅ Classifier Agent (EmailClassification mit Structured Output)
- ✅ Responder Agent (3 Sub-Agents + Orchestrator)
- ✅ Backup Agent

#### Scripts
- ✅ `run_classifier.py` - Test Klassifizierung
- ✅ `run_responder.py` - Test Draft-Generierung
- ✅ `run_full_workflow.py` - Interaktiver Multi-Account-Test
- ✅ `run_scheduler.py` - Automatischer Betrieb

#### Dokumentation
- ✅ `README.md` - Vollständige Dokumentation
- ✅ `QUICKSTART.md` - 5-Minuten-Setup
- ✅ `PROJECT_SCOPE.md` - Dieses Dokument
- ✅ `credentials/README.md` - Gmail API Setup
- ✅ `.env.example` - Konfigurationstemplate

---

## ❌ Scope: Was ist NICHT DRIN (Out of Scope für MVP)

### Nicht implementiert (aber geplant)

1. **Web-Dashboard / UI**
   - Visualisierung von Agents
   - Run-History Browser
   - Live-Monitoring
   - Agent-Konfiguration via UI

2. **REST API**
   - HTTP-Endpunkte für Agents
   - Webhook-Support
   - API-Dokumentation (OpenAPI/Swagger)

3. **Weitere Module**
   - Calendar-Modul
   - Finance-Modul
   - Knowledge-Modul
   - Health-Modul

4. **Cross-Module-Features**
   - Email → Calendar Integration
   - Email → Finance Integration
   - Shared Context Store zwischen Modulen

5. **Advanced Features**
   - Machine Learning für bessere Klassifizierung
   - Custom Guardrails per User
   - A/B-Testing für Tone-Varianten
   - Multi-Language-Support (aktuell: Deutsch/Englisch gemischt)

### Bewusst ausgeschlossen

1. **Auto-Delete von Spam**
   - Zu riskant (False Positives)
   - Nur Labeling + Archivierung

2. **Unbegrenzte Auto-Replies**
   - Nur bei hoher Confidence (>85%)
   - Guardrails verhindern problematische Antworten

3. **Direkte Änderungen an Original-Emails**
   - Nur Labeling, keine Modifikation
   - Backups sind read-only Copies

---

## 📊 Aktuelle Implementierung

### Dateien & Code-Statistik

```
📁 Projekt-Struktur:
   24 Python-Dateien
   ~3,500 Zeilen Code

📦 Platform Core:
   - platform/core/registry.py (Agent Registry)
   - platform/core/config.py (Config System)
   - platform/db/models.py (DB Models)
   - platform/db/database.py (DB Connection)

🔌 Email-Modul:
   Agents:
   - modules/email/agents/classifier.py
   - modules/email/agents/responder.py
   - modules/email/agents/orchestrator.py
   - modules/email/agents/backup.py

   Tools:
   - modules/email/tools/gmail_tools.py
   - modules/email/tools/ionos_tools.py

   Guardrails:
   - modules/email/guardrails/email_guardrails.py

   Module:
   - modules/email/module.py

🧪 Scripts:
   - scripts/run_classifier.py
   - scripts/run_responder.py
   - scripts/run_full_workflow.py
   - scripts/run_scheduler.py

📚 Dokumentation:
   - README.md
   - QUICKSTART.md
   - PROJECT_SCOPE.md
   - credentials/README.md
```

### Datenbank-Schema

```sql
-- Platform Core
modules (id, name, version, description, active, ...)
agents (id, module_id, agent_id, name, agent_type, ...)
runs (id, agent_id, run_id, status, started_at, finished_at, ...)
steps (id, run_id, index, role, content, ...)

-- Email-Specific
email_accounts (id, account_id, account_type, email_address, mode, ...)
processed_emails (id, account_id, email_id, category, confidence, ...)
```

---

## 🗓️ Roadmap

### Phase 1: MVP ✅ COMPLETE (Nov 2025)

- ✅ Platform Core (Registry, Config, DB)
- ✅ Email-Modul (vollständig)
- ✅ Guardrails (PII, Phishing, Compliance)
- ✅ Backup Agent
- ✅ Scheduler
- ✅ Test-Scripts
- ✅ Dokumentation

### Phase 2: API & Dashboard 🚧 PLANNED (Dez 2025)

- [ ] FastAPI REST API
  - [ ] `/agents` - Agent-Management
  - [ ] `/runs` - Run-History
  - [ ] `/modules` - Module-Management
  - [ ] Webhook-Support
- [ ] Web Dashboard (React/Next.js)
  - [ ] Agent-Übersicht
  - [ ] Run-Timeline
  - [ ] Live-Monitoring
  - [ ] Config-Editor

### Phase 3: Weitere Module 🚧 PLANNED (Q1 2026)

- [ ] Calendar-Modul
  - [ ] Meeting-Scheduler Agent
  - [ ] Reminder Agent
  - [ ] Availability-Checker
  - [ ] Google Calendar API Integration
- [ ] Finance-Modul
  - [ ] Transaction-Tracker Agent
  - [ ] Budget-Advisor Agent
  - [ ] Tax-Helper Agent
  - [ ] Banking API Integration

### Phase 4: Cross-Module & Advanced 🔮 FUTURE

- [ ] Cross-Module-Workflows
  - [ ] Email → Calendar (Meeting-Requests)
  - [ ] Email → Finance (Rechnungen)
- [ ] Master Orchestrator
  - [ ] Morning Briefing (über alle Module)
  - [ ] Proaktive Vorschläge
- [ ] Advanced Features
  - [ ] Machine Learning Integration
  - [ ] Custom Guardrails
  - [ ] Multi-Language-Support

---

## 🔗 Abhängigkeiten

### Externe Services

| Service | Zweck | Erforderlich |
|---------|-------|--------------|
| **OpenAI API** | LLM für Agents | ✅ Ja |
| **Gmail API** | Gmail-Zugriff (OAuth) | ✅ Ja (für Gmail-Accounts) |
| **Google Cloud** | OAuth Credentials | ✅ Ja (für Gmail-Accounts) |
| **IMAP/SMTP** | Ionos Email-Zugriff | ⚠️ Optional (nur für Ionos) |

### Python-Pakete (requirements.txt)

```
Core:
- openai>=1.54.0
- agents-sdk>=0.1.0
- pydantic>=2.5.0
- python-dotenv>=1.0.0

Google APIs:
- google-api-python-client>=2.100.0
- google-auth-httplib2>=0.1.1
- google-auth-oauthlib>=1.1.0

Database:
- sqlalchemy>=2.0.23
- alembic>=1.13.0

Scheduler:
- apscheduler>=3.10.4

Async:
- aiohttp>=3.9.0
```

---

## 🔐 Sicherheit & Datenschutz

### Implementierte Sicherheitsmaßnahmen

1. **Credentials-Management**
   - OAuth 2.0 für Gmail
   - Credentials nie in Code oder Git
   - `.gitignore` für alle sensitiven Dateien
   - Token-Rotation via OAuth

2. **Guardrails**
   - PII-Erkennung verhindert Leaking von persönlichen Daten
   - Phishing-Detection schützt vor Malware
   - Compliance-Checks verhindern rechtliche Probleme

3. **Modi-System**
   - Draft Mode als sicherer Standard
   - Auto-Reply nur bei hoher Confidence
   - Tripwire-Mechanismus stoppt kritische Fälle

4. **Datenbank**
   - Lokale SQLite (keine Cloud)
   - Logs können gelöscht werden
   - Kein Tracking von Inhalten

### GDPR-Konformität

- ✅ Alle Daten lokal gespeichert
- ✅ Keine externen Tracker
- ✅ User hat volle Kontrolle
- ✅ Daten können gelöscht werden
- ⚠️ OpenAI API: Daten werden verarbeitet (gemäß OpenAI Terms)

---

## 🧪 Testing

### Aktueller Test-Coverage

- ✅ **Manuelle Tests**: Alle Scripts funktionsfähig
- ✅ **Integration Tests**: Multi-Account-Workflow getestet
- ⚠️ **Unit Tests**: Noch nicht implementiert (geplant)
- ⚠️ **E2E Tests**: Noch nicht implementiert (geplant)

### Test-Strategie

```python
# Geplante Test-Struktur
tests/
├── unit/
│   ├── test_classifier.py
│   ├── test_responder.py
│   └── test_guardrails.py
├── integration/
│   ├── test_gmail_tools.py
│   └── test_orchestrator.py
└── e2e/
    └── test_full_workflow.py
```

---

## 📏 Erfolgs-Kriterien

### MVP (✅ Erreicht)

- ✅ Alle 4 Email-Accounts werden unterstützt
- ✅ Spam-Klassifizierung funktioniert zuverlässig
- ✅ Draft-Generierung in allen 3 Tones
- ✅ Modi-System funktioniert pro Account
- ✅ Guardrails verhindern kritische Fehler
- ✅ Monatliches Backup läuft automatisch
- ✅ Scheduler führt Tasks aus
- ✅ Dokumentation ist vollständig

### Phase 2 (Zukünftig)

- [ ] REST API mit 100% Coverage aller Features
- [ ] Web Dashboard mit allen Agents
- [ ] <1s Response-Zeit für API-Calls
- [ ] 99% Uptime für Scheduler

---

## 🤝 Beitragende

- **Hauptentwickler**: Daniel Schindler
- **AI-Assistent**: Claude (Anthropic) via Claude Code
- **Basierend auf**: OpenAI Agents SDK, 2_openai/ Labs 1-4

---

## 📄 Lizenz

Privates Projekt - Keine öffentliche Lizenz

---

## 🔄 Versions-Historie

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0.0 | 2025-11-19 | MVP Complete - Email-Modul vollständig implementiert |
| 0.1.0 | 2025-11-19 | Projekt-Setup, Platform Core |

---

## 📞 Kontakt & Support

Bei Fragen oder Problemen:
1. Konsultiere `README.md` und `QUICKSTART.md`
2. Prüfe `.env` Konfiguration
3. Checke Logs in Terminal
4. Review `2_openai/` Patterns für Beispiele

---

**Letztes Update:** 2025-11-19
**Status:** ✅ MVP COMPLETE
