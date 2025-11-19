# Email Classification System - Setup & Configuration Guide

Dieses Dokument beschreibt die vollständige Konfiguration des Email Classification Systems für Entwicklung und Produktion.

---

## Schritt 1: Basis-Setup

### 1.1 Virtual Environment

```bash
cd /home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.2 Database Initialisierung

```bash
python -c "from agent_platform.db.database import init_db; init_db()"
```

Überprüfe, dass `platform.db` erstellt wurde:

```bash
ls -la *.db
```

---

## Schritt 2: OpenAI API Key

### 2.1 API Key generieren

1. Gehe zu https://platform.openai.com/api/keys
2. Neuen API Key erstellen ("Create new secret key")
3. Kopieren (wird nur einmal angezeigt!)

### 2.2 .env aktualisieren

Öffne `.env` und ersetze:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

durch deinen API Key:

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Sicherheit:**
- `.env` ist im `.gitignore` - wird nicht committed
- Niemals API Keys in Repository pushen!
- Pro Umgebung einen separaten Key verwenden (Dev/Staging/Prod)

---

## Schritt 3: Gmail OAuth2 Setup

### 3.1 Google Cloud Project erstellen

1. Gehe zu https://console.cloud.google.com/
2. Neues Projekt erstellen (z.B. "Email Classification System")
3. Projekt auswählen

### 3.2 Gmail API aktivieren

1. Gehe zu "APIs & Services" → "Library"
2. Suche nach "Gmail API"
3. Klick auf "Gmail API"
4. Klick auf "Enable"

### 3.3 OAuth2 Credentials erstellen

1. Gehe zu "APIs & Services" → "Credentials"
2. Klick auf "Create Credentials" → "OAuth client ID"
3. Wenn aufgefordert: "Configure OAuth Consent Screen" durchführen
   - User Type: "External" (für Entwicklung)
   - Required Scopes hinzufügen:
     - `https://www.googleapis.com/auth/gmail.readonly` (Read emails)
     - `https://www.googleapis.com/auth/gmail.modify` (Modify emails)
     - `https://www.googleapis.com/auth/gmail.labels` (Manage labels)
4. Back zu "Credentials"
5. Klick "Create Credentials" → "OAuth client ID"
6. Application type: "Desktop application"
7. Klick "Create"
8. Klick auf Download-Icon (JSON) → Speichern als `credentials/gmail_account_2.json`

### 3.4 .env konfigurieren

```env
GMAIL_2_CREDENTIALS_PATH=credentials/gmail_account_2.json
GMAIL_2_TOKEN_PATH=tokens/gmail_account_2_token.json
GMAIL_2_EMAIL=deine_gmail_adresse@gmail.com
```

**Wichtig:** `gmail_account_2_token.json` wird **automatisch** beim ersten Lauf erstellt!

---

## Schritt 4: Verzeichnisse vorbereiten

```bash
# Erstelle notwendige Verzeichnisse
mkdir -p credentials
mkdir -p tokens
mkdir -p logs
```

### Struktur:
```
agent-platform/
├── credentials/
│   ├── gmail_account_2.json    (deine OAuth credentials)
│   └── .gitignore              (schützt vor Commits)
├── tokens/
│   ├── gmail_account_2_token.json  (auto-generiert)
│   └── .gitignore
├── logs/
│   └── classification.log
└── platform.db                 (SQLite database)
```

---

## Schritt 5: Test-Konfiguration

Für die E2E Tests sollte die `.env` folgende Werte haben:

```env
# ============================================================================
# LLM PROVIDER CONFIGURATION
# ============================================================================

OPENAI_API_KEY=sk-proj-your_actual_key_here
OPENAI_MODEL=gpt-4o

# Ollama (kann disabled sein für Tests)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=gptoss20b
OLLAMA_TIMEOUT=60
LLM_FALLBACK_ENABLED=true

# ============================================================================
# IMPORTANCE CLASSIFIER CONFIGURATION
# ============================================================================

IMPORTANCE_CONFIDENCE_HIGH_THRESHOLD=0.85
IMPORTANCE_CONFIDENCE_MEDIUM_THRESHOLD=0.6
IMPORTANCE_SCORE_LOW_THRESHOLD=0.4
IMPORTANCE_SCORE_HIGH_THRESHOLD=0.7

DAILY_DIGEST_ENABLED=true
DAILY_DIGEST_TIME=08:00

FEEDBACK_TRACKING_ENABLED=true
FEEDBACK_CHECK_INTERVAL_HOURS=1

# ============================================================================
# EMAIL ACCOUNTS - GMAIL (TEST ACCOUNT 2)
# ============================================================================

GMAIL_2_CREDENTIALS_PATH=credentials/gmail_account_2.json
GMAIL_2_TOKEN_PATH=tokens/gmail_account_2_token.json
GMAIL_2_EMAIL=deine_gmail@gmail.com

# Optional: andere Accounts
GMAIL_1_CREDENTIALS_PATH=credentials/gmail_account_1.json
GMAIL_1_TOKEN_PATH=tokens/gmail_account_1_token.json
GMAIL_1_EMAIL=account1@gmail.com

GMAIL_3_CREDENTIALS_PATH=credentials/gmail_account_3.json
GMAIL_3_TOKEN_PATH=tokens/gmail_account_3_token.json
GMAIL_3_EMAIL=account3@gmail.com

# ============================================================================
# EMAIL ACCOUNTS - IONOS (OPTIONAL)
# ============================================================================

IONOS_EMAIL=your_email@ionos.de
IONOS_PASSWORD=your_ionos_password
IONOS_IMAP_SERVER=imap.ionos.de
IONOS_IMAP_PORT=993
IONOS_SMTP_SERVER=smtp.ionos.de
IONOS_SMTP_PORT=587

# ============================================================================
# BACKUP ACCOUNT (OPTIONAL)
# ============================================================================

BACKUP_EMAIL=backup@gmail.com
BACKUP_CREDENTIALS_PATH=credentials/backup_credentials.json
BACKUP_TOKEN_PATH=tokens/backup_token.json

# ============================================================================
# EMAIL MODULE CONFIGURATION
# ============================================================================

DEFAULT_MODE=draft
CLASSIFIER_BATCH_SIZE=10
RESPONDER_CONFIDENCE_THRESHOLD=0.85

# ============================================================================
# SCHEDULER SETTINGS
# ============================================================================

INBOX_CHECK_INTERVAL_HOURS=1
BACKUP_DAY_OF_MONTH=1
BACKUP_HOUR=3

# ============================================================================
# DATABASE
# ============================================================================

DATABASE_URL=sqlite:///platform.db
```

---

## Schritt 6: Erste Authentifizierung testen

Führe ein Test-Script aus, um Gmail zu authentifizieren:

```bash
python scripts/test_gmail_auth.py
```

Beim ersten Lauf:
1. Browser öffnet sich
2. Du wirst aufgefordert, dich mit Google anzumelden
3. Consent-Screen bestätigen
4. Token wird in `tokens/gmail_account_2_token.json` gespeichert
5. Token wird automatisch bei jedem Request erneuert

---

## Schritt 7: Datenbank validieren

```bash
python scripts/verify_db.py
```

Output sollte zeigen:
```
✅ Database connected
✅ All tables created
✅ Ready for use
```

---

## Checkliste für E2E Tests

- [ ] Virtual Environment aktiviert
- [ ] Requirements installiert
- [ ] Database initialisiert
- [ ] `.env` mit echten API Keys & Emails konfiguriert
- [ ] `credentials/gmail_account_2.json` vorhanden
- [ ] OAuth Flow durchgeführt (token auto-generiert)
- [ ] Directories erstellt: credentials/, tokens/, logs/
- [ ] Erste Authentifizierung erfolgreich
- [ ] Database validiert

---

## Troubleshooting

### Problem: "OPENAI_API_KEY not found"

**Lösung:**
- Stelle sicher, dass `.env` im Projektverzeichnis liegt
- Starte Python/Tests aus dem Projektverzeichnis
- Verwende `python-dotenv` wird automatisch geladen

### Problem: "Gmail API: 404 Not Found"

**Lösung:**
- Gmail API muss im Google Cloud Console aktiviert sein
- Überprüfe: https://console.cloud.google.com/apis/api/gmail.googleapis.com

### Problem: "Credentials file not found"

**Lösung:**
- Stelle sicher, dass `credentials/` Verzeichnis existiert
- OAuth credentials müssen als `credentials/gmail_account_2.json` gespeichert sein
- Pfad in `.env` muss korrekt sein

### Problem: "Token expired"

**Lösung:**
- Delete `tokens/gmail_account_2_token.json`
- Führe das Script erneut aus (triggert OAuth Flow)

---

## Umgebungs-spezifische Konfigurationen

### Development (.env)

```env
OPENAI_API_KEY=sk-proj-dev-key
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_FALLBACK_ENABLED=true
DATABASE_URL=sqlite:///platform_dev.db
DAILY_DIGEST_ENABLED=false  # Disable in dev
```

### Staging (.env.staging)

```env
OPENAI_API_KEY=sk-proj-staging-key
OLLAMA_BASE_URL=http://localhost:11434/v1  # or staging server
LLM_FALLBACK_ENABLED=true
DATABASE_URL=sqlite:///platform_staging.db
DAILY_DIGEST_ENABLED=true
```

### Production (.env.production)

```env
OPENAI_API_KEY=sk-proj-prod-key
OLLAMA_BASE_URL=http://production-ollama-server/v1
LLM_FALLBACK_ENABLED=true
DATABASE_URL=postgresql://user:pwd@prod-db:5432/classification
DAILY_DIGEST_ENABLED=true
DAILY_DIGEST_TIME=08:00
```

---

## Sicherheit Best Practices

1. **Niemals Secrets in Code oder Logs**
   - `.env` in `.gitignore`
   - `credentials/` in `.gitignore`
   - `tokens/` in `.gitignore`

2. **API Key Rotation**
   - Regelmäßig neue API Keys generieren
   - Alte Keys in Google Cloud Console deaktivieren

3. **Least Privilege**
   - Gmail API: Nur benötigte Scopes aktivieren
   - Nicht `https://www.googleapis.com/auth/gmail` (all access) verwenden

4. **Token Management**
   - Token wird automatisch erneuert (keine manuelle Aktion nötig)
   - Token bleibt 60 Tage gültig ohne Nutzung

---

## Production Deployment Checklist

Weitere Details siehe: [DEPLOYMENT.md](DEPLOYMENT.md)

- [ ] All environment variables set
- [ ] Database migrated to PostgreSQL (oder äquivalent)
- [ ] Secrets in secure vault (nicht .env file)
- [ ] Monitoring & Logging configured
- [ ] Backup strategy implemented
- [ ] Rate limiting configured
- [ ] Error handling tested

---

**Nächste Schritte:**
1. Setup durchführen
2. E2E Tests ausführen: `python tests/test_e2e_real_gmail.py`
3. Mailbox-Analyse durchführen: `python scripts/analyze_mailbox_history.py`
4. System in Produktion gehen: Siehe [DEPLOYMENT.md](DEPLOYMENT.md)
