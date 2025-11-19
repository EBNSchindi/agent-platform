# 🚀 Quickstart Guide

Schnelleinstieg für die Agent Platform.

## ⚡ 5-Minuten-Setup

### 1. Installation

```bash
cd /home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform

# Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt
```

### 2. Konfiguration

```bash
# .env erstellen
cp .env.example .env

# .env bearbeiten - mindestens eintragen:
# - OPENAI_API_KEY
# - GMAIL_1_EMAIL + GMAIL_1_CREDENTIALS_PATH
```

### 3. Gmail API Setup

1. **Google Cloud Console**: https://console.cloud.google.com/
2. **Gmail API aktivieren**: APIs & Services → Library → Gmail API → Enable
3. **OAuth Credentials erstellen**:
   - APIs & Services → Credentials
   - Create Credentials → OAuth Client ID
   - Application type: Desktop app
   - Download JSON → speichern als `credentials/gmail_account_1.json`
4. **In .env eintragen**:
   ```
   GMAIL_1_CREDENTIALS_PATH=credentials/gmail_account_1.json
   GMAIL_1_EMAIL=deine@email.com
   ```

### 4. Datenbank initialisieren

```bash
python -c "from platform.db.database import init_db; init_db()"
```

### 5. Erste Tests

```bash
# Test 1: Classifier
python scripts/run_classifier.py
# → Beim ersten Run: Browser öffnet sich für OAuth

# Test 2: Responder (Drafts generieren)
python scripts/run_responder.py

# Test 3: Kompletter Workflow
python scripts/run_full_workflow.py
```

---

## 📋 Features im Überblick

### ✅ Implementiert

- **Multi-Account-Support**: 3x Gmail + 1x Ionos
- **Email-Klassifizierung**: Spam/Important/Normal/Auto-Reply
- **Draft-Generierung**: 3 Tone-Varianten (Professional/Friendly/Brief)
- **Modi-System**:
  - **Draft Mode**: Generiert Drafts zur Review
  - **Auto-Reply Mode**: Sendet bei hoher Confidence
  - **Manual Mode**: Nur Klassifizierung
- **Guardrails**:
  - PII-Erkennung
  - Phishing-Detection
  - Compliance-Checks
- **Backup**: Monatliches Backup aller Accounts
- **Scheduler**: Automatische Ausführung (stündlich + monatlich)

### 🔧 Modi pro Account konfigurieren

```python
from platform.core.config import Config, Mode

# In Code
Config.set_account_mode("gmail_1", Mode.DRAFT)
Config.set_account_mode("gmail_2", Mode.AUTO_REPLY)
Config.set_account_mode("ionos", Mode.MANUAL)

# Oder in .env
DEFAULT_MODE=draft  # draft, auto_reply, manual
```

---

## 🎯 Typische Workflows

### Workflow 1: Tägliche Inbox-Verarbeitung

```bash
# Manuell alle Accounts prüfen
python scripts/run_full_workflow.py
# → Option 2 wählen

# Oder: Scheduler laufen lassen (automatisch)
python scripts/run_scheduler.py
```

### Workflow 2: Einzelner Account testen

```bash
python scripts/run_full_workflow.py
# → Option 1 wählen
# → Account + Mode auswählen
```

### Workflow 3: Monatliches Backup

```bash
# Manuell
python scripts/run_full_workflow.py
# → Option 3 wählen

# Oder: Wartet auf geplanten Scheduler-Run
# (1. Tag des Monats, 3 Uhr nachts)
```

---

## 📁 Wichtige Dateien

| Datei | Beschreibung |
|-------|--------------|
| `.env` | **Konfiguration** (API Keys, Account-Daten) |
| `platform/core/config.py` | Modi-System, Account-Verwaltung |
| `modules/email/agents/` | **Agents** (Classifier, Responder, Backup) |
| `modules/email/tools/` | **Tools** (Gmail API, Ionos IMAP/SMTP) |
| `modules/email/guardrails/` | **Guardrails** (PII, Phishing, Compliance) |
| `scripts/run_full_workflow.py` | **Interaktiver Test** |
| `scripts/run_scheduler.py` | **Automatischer Betrieb** |

---

## 🔍 Troubleshooting

### "No module named 'agents'"

```bash
# agents-sdk installieren
pip install agents-sdk

# Oder requirements neu installieren
pip install -r requirements.txt --upgrade
```

### "Gmail API: Access Denied"

1. Gmail API im Google Cloud Projekt aktiviert?
2. OAuth Credentials korrekt?
3. Token neu generieren:
   ```bash
   rm tokens/gmail_account_1_token.json
   python scripts/run_classifier.py  # Re-authenticate
   ```

### "OPENAI_API_KEY not set"

```bash
# In .env eintragen:
OPENAI_API_KEY=sk-proj-...
```

---

## 📚 Weitere Dokumentation

- **Vollständiges README**: [README.md](README.md)
- **Gmail API Setup**: [credentials/README.md](credentials/README.md)
- **2_openai Patterns**: `/agent-systems/2_openai/` (Lab 1-4)

---

## ☎️ Support

Bei Problemen:
1. Prüfe `.env` Konfiguration
2. Prüfe `credentials/` Ordner
3. Logs in Terminal beachten
4. README.md konsultieren
