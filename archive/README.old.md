# Agent Platform - Multi-Agent System

Modulare Plattform für AI-Agents basierend auf OpenAI Agents SDK.

## 🎯 Überblick

Diese Plattform ermöglicht die Verwaltung und Orchestrierung mehrerer AI-Agents für verschiedene Lebensbereiche:

- **📧 Email-Modul**: Posteingang-Automatisierung mit Klassifizierung, Draft-Generierung und Backup
- **📅 Calendar-Modul**: (geplant) Meeting-Scheduling und Reminder
- **💰 Finance-Modul**: (geplant) Transaktions-Tracking und Budget-Beratung
- Weitere Module erweiterbar

## 🏗️ Architektur

```
Platform (Zentrale)
├── Agent Registry (alle Agents)
├── REST API (FastAPI)
├── Datenbank (SQLite/Postgres)
└── Scheduler (zeitgesteuerte Tasks)

Modules (Plugins)
├── Email-Modul
│   ├── Classifier Agent (Spam/Important)
│   ├── Responder Agent (Draft-Generierung)
│   └── Backup Agent (monatliches Backup)
├── Calendar-Modul (geplant)
└── Finance-Modul (geplant)
```

## 📦 Installation

### 1. Repository klonen

```bash
cd /home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform
```

### 2. Virtual Environment erstellen

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# Bearbeite .env mit deinen API-Keys und Credentials
```

### 5. Datenbank initialisieren

```bash
python -c "from platform.db.database import init_db; init_db()"
```

## 🔑 Gmail API Setup

### Schritt 1: Google Cloud Console

1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle neues Projekt oder wähle bestehendes aus
3. Aktiviere **Gmail API**:
   - APIs & Services → Library
   - Suche nach "Gmail API"
   - Klicke "Enable"

### Schritt 2: OAuth Credentials erstellen

1. APIs & Services → Credentials
2. Create Credentials → OAuth Client ID
3. Application type: **Desktop app**
4. Name: "Email Agent Platform"
5. Download JSON → speichern als `credentials/gmail_account_1.json`
6. Wiederhole für weitere Gmail-Accounts

### Schritt 3: .env konfigurieren

```env
GMAIL_1_CREDENTIALS_PATH=credentials/gmail_account_1.json
GMAIL_1_TOKEN_PATH=tokens/gmail_account_1_token.json
GMAIL_1_EMAIL=your_email_1@gmail.com
```

Beim ersten Run wird ein Browser-Fenster für OAuth-Authentifizierung geöffnet.

## 🚀 Schnellstart

### Email-Klassifizierung testen

```bash
python scripts/run_classifier.py
```

### Draft-Generierung testen

```bash
python scripts/run_responder.py
```

### Scheduler starten (stündliche Inbox-Checks)

```bash
python scripts/run_scheduler.py
```

## 🎛️ Modi-System

Das Email-Modul unterstützt 3 Modi pro Account:

### 1. **Draft Mode** (Standard)
- Klassifiziert E-Mails
- Generiert Antwort-Drafts
- Speichert Drafts im Entwurfsordner
- **Keine automatischen Antworten**

### 2. **Auto-Reply Mode**
- Klassifiziert E-Mails
- Generiert Antworten
- **Sendet direkt** (nur bei hoher Confidence > 0.85)
- Bei geringer Confidence → Draft Mode

### 3. **Manual Mode**
- Klassifiziert E-Mails
- Setzt Labels
- **Keine Drafts, keine Antworten**

Konfiguration in `.env`:

```env
DEFAULT_MODE=draft
```

Pro Account in Code konfigurierbar:

```python
from platform.core.config import Config, Mode

Config.set_account_mode("gmail_1", Mode.DRAFT)
Config.set_account_mode("gmail_2", Mode.AUTO_REPLY)
Config.set_account_mode("ionos", Mode.MANUAL)
```

## 📋 Features

### Email-Modul

- ✅ **Multi-Account-Support**: 3x Gmail + 1x Ionos
- ✅ **Spam-Klassifizierung**: Automatische Kategorisierung
- ✅ **Draft-Generierung**: AI-generierte Antworten mit Review
- ✅ **Guardrails**: PII-Erkennung, Compliance-Checks
- ✅ **Modi-System**: Draft / Auto-Reply / Manual
- ✅ **Backup**: Monatliches automatisches Backup auf Backup-Account
- ✅ **Scheduler**: Stündliche Inbox-Checks

### Platform

- ✅ **Agent Registry**: Zentrale Verwaltung aller Agents
- ✅ **Datenbank**: SQLite für Run-Logging
- ✅ **Structured Outputs**: Type-Safe mit Pydantic
- 🚧 **REST API**: (in Entwicklung)
- 🚧 **Web Dashboard**: (in Entwicklung)

## 📁 Projekt-Struktur

```
agent-platform/
├── platform/              # Platform Core
│   ├── core/
│   │   ├── registry.py   # Agent Registry
│   │   └── config.py     # Configuration
│   └── db/
│       ├── models.py     # SQLAlchemy Models
│       └── database.py   # DB Connection
├── modules/              # Agent Modules
│   └── email/
│       ├── agents/       # Classifier, Responder, Backup
│       ├── tools/        # Gmail API, Ionos IMAP/SMTP
│       └── guardrails/   # Safety Checks
├── scripts/              # Executable Scripts
└── .env                  # Configuration (nicht in Git)
```

## 🔧 Entwicklung

### Neue Module hinzufügen

1. Erstelle Verzeichnis in `modules/`
2. Implementiere Agents mit OpenAI Agents SDK
3. Registriere Modul in Registry
4. Agents werden automatisch verfügbar

Beispiel siehe: `modules/email/`

## 📚 Basiert auf

- [OpenAI Agents SDK](https://platform.openai.com/docs/agents)
- Patterns aus `/agent-systems/2_openai/` (Labs 1-4)
- Manager-Worker-Architektur aus `deep_research/`
- Guardrails-Patterns aus Community Contributions

## ⚙️ Konfiguration

Siehe `.env.example` für alle Konfigurationsoptionen.

Wichtige Settings:

```env
# Modi
DEFAULT_MODE=draft                     # draft, auto_reply, manual
RESPONDER_CONFIDENCE_THRESHOLD=0.85    # Min. Confidence für Auto-Reply

# Scheduler
INBOX_CHECK_INTERVAL_HOURS=1           # Stündlicher Check
BACKUP_DAY_OF_MONTH=1                  # Monatliches Backup am 1.
BACKUP_HOUR=3                          # Um 3 Uhr nachts
```

## 🐛 Troubleshooting

### Gmail API: "Access Denied"

- Stelle sicher, dass Gmail API im Google Cloud Projekt aktiviert ist
- Überprüfe OAuth Scopes in credentials.json
- Lösche `tokens/*.json` und authentifiziere neu

### "Module not found"

```bash
# Stelle sicher, dass du im richtigen Verzeichnis bist
cd /home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform

# Virtual Environment aktiviert?
source venv/bin/activate
```

## 📝 Lizenz

Privates Projekt

## 🚀 Roadmap

- [ ] Email-Modul vollständig (in Arbeit)
- [ ] REST API (FastAPI)
- [ ] Web Dashboard (React/Next.js)
- [ ] Calendar-Modul
- [ ] Finance-Modul
- [ ] Cross-Module-Workflows
- [ ] Deployment (Docker)
