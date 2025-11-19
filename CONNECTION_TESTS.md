# Connection Tests - Quick Reference

Drei vollständige Tests zur Validierung Ihrer Konfiguration.

---

## 🧪 Test 1: Gmail OAuth2 Connection

### Command
```bash
python scripts/test_gmail_auth.py
```

### Was dieser Test macht
- ✅ Validiert `credentials/gmail_account_2.json` existiert
- ✅ Lädt/refreshed cached OAuth Token
- ✅ Triggert OAuth Flow (beim ersten Lauf → Browser öffnet sich)
- ✅ Fetcht 5 unread emails
- ✅ Zeigt Email-Liste mit Details
- ✅ Bestätigt Gmail API Zugang

### Erwarteter Output (beim ersten Mal)
```
Gmail OAuth2 Authentication Test

🌐 Opening browser for authorization...
   If browser doesn't open, visit the URL manually

[Browser öffnet sich → Google Login → Grant Permissions]

✅ Authorization successful!
💾 Token saved: tokens/gmail_account_2_token.json

📧 Fetching unread emails...
✅ Found 8 unread email(s):

   1. Meeting Tomorrow
      From: boss@company.com
      Date: Mon, 19 Nov 2024 09:30:00 +0000

   2. Project Status Update
      From: team@company.com
      ...

✅ Gmail authentication successful!
Token location: tokens/gmail_account_2_token.json

You can now use the Email Classification System with gmail_2
```

### Troubleshooting
- **Browser öffnet nicht:** Manuelle URL kopieren aus Terminal
- **"Credentials file not found":** Download credentials.json von Google Cloud Console
- **"Permission denied":** Gmail API muss im Google Cloud Console aktiviert sein

---

## 🧪 Test 2: OpenAI API Connection

### Command
```bash
python scripts/test_openai_connection.py
```

### Was dieser Test macht
- ✅ Validiert `OPENAI_API_KEY` in .env
- ✅ Überprüft API Key Format (sk-proj-...)
- ✅ Testet Verbindung zu OpenAI API
- ✅ Listet verfügbare Models auf
- ✅ Macht einen Test-API-Call (minimal cost)
- ✅ Zeigt Token Usage & Pricing Info

### Erwarteter Output
```
===============================================================================
OpenAI API Connection Test
===============================================================================

1️⃣  Checking API Key Configuration...
   ✅ OPENAI_API_KEY is set
   Key preview: sk-proj-xxxxxxxxxxxxx...yyyyyyyyy

2️⃣  Validating API Key Format...
   ✅ API key format looks valid (sk-proj-...)

3️⃣  Testing Connection to OpenAI...
   ✅ Connection successful!

4️⃣  Available Models:
   • gpt-4o
   • gpt-4-turbo
   • gpt-3.5-turbo
   • ...

5️⃣  Testing with Simple LLM Request...
   ✅ LLM Response: Connection successful!

6️⃣  Request Usage:
   Tokens used: 12
   Prompt tokens: 8
   Completion tokens: 4

7️⃣  Pricing Information:
   Model: gpt-4o
   Input: $5 per 1M tokens
   Output: $15 per 1M tokens

   Estimated cost for this test: ~$0.00001 (negligible)

===============================================================================
✅ OpenAI Connection Test PASSED
===============================================================================

You can now:
1. Run E2E tests: python tests/test_e2e_real_gmail.py
2. Analyze mailbox: python scripts/analyze_mailbox_history.py
```

### Troubleshooting
- **"OPENAI_API_KEY not found":** .env muss OPENAI_API_KEY enthalten
- **"Connection failed":** API Key möglicherweise revoked oder expired
- **"Invalid API key":** Überprüfe Key im OpenAI Dashboard

---

## 🧪 Test 3: All Connections Health Check

### Command
```bash
python scripts/test_all_connections.py
```

### Was dieser Test macht
- ✅ Testet **Environment Configuration**
- ✅ Testet **Gmail Files** (credentials.json)
- ✅ Testet **Gmail API Connection**
- ✅ Testet **OpenAI API Connection**
- ✅ Testet **Database Connection**
- ✅ Gibt umfassenden Status-Report

### Erwarteter Output
```
===============================================================================
Service Connection Health Check
Time: 2024-11-19 10:30:45 UTC
===============================================================================

1️⃣  Environment Configuration
   ───────────────────────────────────────────────────────────────
   ✅ OPENAI_API_KEY                  set
   ✅ GMAIL_2_CREDENTIALS_PATH        set
   ✅ GMAIL_2_TOKEN_PATH              set
   ✅ GMAIL_2_EMAIL                   set

2️⃣  Gmail Configuration Files
   ───────────────────────────────────────────────────────────────
   ✅ Credentials file exists: credentials/gmail_account_2.json
   ✅ Token cached: tokens/gmail_account_2_token.json

3️⃣  Gmail API Connection
   ───────────────────────────────────────────────────────────────
   ✅ Gmail API connection successful
      Email: your.email@gmail.com
      Messages in inbox: 125

4️⃣  OpenAI API Connection
   ───────────────────────────────────────────────────────────────
   ✅ OpenAI API connection successful
      Total models available: 15
      GPT models available: 8
   ✅ LLM request successful (gpt-4o available)

5️⃣  Database Connection
   ───────────────────────────────────────────────────────────────
   ✅ Database connection successful
      Database URL: sqlite:///platform.db
      Database type: SQLite

===============================================================================
Summary
===============================================================================

  ✅ OK         Environment Configuration
  ✅ OK         Gmail Files
  ✅ OK         Gmail Connection
  ✅ OK         Openai Connection
  ✅ OK         Database Connection

🎉 All tests passed! System is ready.

Next steps:
1. Run E2E test: python tests/test_e2e_real_gmail.py
2. Or analyze mailbox: python scripts/analyze_mailbox_history.py
```

---

## 🚀 Quick Start Sequence

### Schritt 1: Health Check (1 Min)
```bash
# Alle Verbindungen testen
python scripts/test_all_connections.py
```

### Schritt 2a: Wenn Gmail Token fehlt
```bash
# Gmail OAuth2 durchführen (interaktiv)
python scripts/test_gmail_auth.py
# → Browser öffnet sich → Authorize → Done
```

### Schritt 2b: Wenn OpenAI Test fehlschlägt
```bash
# OpenAI API Key überprüfen
python scripts/test_openai_connection.py
# Überprüfe .env: OPENAI_API_KEY=sk-proj-...
```

### Schritt 3: Nach erfolgreichen Tests
```bash
# E2E Test mit echtem Gmail
python tests/test_e2e_real_gmail.py
```

---

## 📊 Test Dependencies

```
test_all_connections.py
├─ test_environment()
│  └─ Prüft .env Variablen
├─ test_gmail_files()
│  └─ Prüft credentials.json & token.json
├─ test_gmail_connection()
│  └─ Benötigt: test_gmail_auth.py bereits gelaufen
├─ test_openai_connection()
│  └─ Benötigt: OPENAI_API_KEY in .env
└─ test_database_connection()
   └─ Benötigt: database initialisiert
```

**Recommended Sequence:**
1. `test_all_connections.py` (findet Probleme)
2. `test_gmail_auth.py` (wenn Gmail Token fehlt)
3. `test_openai_connection.py` (wenn OpenAI Test fehlschlägt)
4. `test_all_connections.py` (nochmal, zur Bestätigung)

---

## 🔧 Fehlerbehandlung

### Gmail Fehler

| Problem | Lösung |
|---------|--------|
| Credentials file not found | Download von Google Cloud Console |
| OAuth token expired | Delete `tokens/gmail_account_2_token.json`, re-auth |
| Gmail API: 403 Permission denied | Gmail API im Cloud Console aktivieren |
| "not authorized to access resource" | Prüfe Scopes im OAuth credentials |

### OpenAI Fehler

| Problem | Lösung |
|---------|--------|
| OPENAI_API_KEY not found | Set in .env |
| API key invalid | Überprüfe Key im OpenAI Dashboard |
| Connection timeout | Überprüfe Internet-Verbindung |
| Rate limit exceeded | Warte kurz, dann nochmal versuchen |

### Database Fehler

| Problem | Lösung |
|---------|--------|
| Database not found | `python -c "from agent_platform.db.database import init_db; init_db()"` |
| Connection refused | Prüfe DATABASE_URL in .env |
| Permission denied | Überprüfe Dateiberechtigungen |

---

## 💡 Best Practices

1. **Vor E2E Tests:** Always run `test_all_connections.py`
2. **Nach .env Änderungen:** Re-run health check
3. **Tägliche Nutzung:** Nur nötig, wenn Fehler auftreten
4. **Token Refresh:** Automatisch, kein manuelles Handeln nötig
5. **API Costs:** Tests kosten ~$0.00001 pro Lauf (negligible)

---

## 📋 Zusammenfassung

```bash
# 1. Health Check (finding issues)
python scripts/test_all_connections.py

# 2. Individual Tests (debugging)
python scripts/test_gmail_auth.py      # Gmail OAuth
python scripts/test_openai_connection.py # OpenAI API

# 3. Full System Test (after fixes)
python tests/test_e2e_real_gmail.py
```

**Jetzt können Sie testen!** 🎉
