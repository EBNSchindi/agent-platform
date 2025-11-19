# Deployment Guide - Email Classification System

Vollständige Anleitung für Production Deployment des Email Classification Systems.

---

## 📋 Voraussetzungen

### System Requirements

- **Python**: 3.10 oder höher
- **RAM**: Mindestens 2GB (4GB empfohlen mit Ollama)
- **Disk**: 5GB frei (für Ollama models + Database)
- **OS**: Linux, macOS, oder Windows

### Optional (für LLM Layer)

- **Ollama**: Für lokale LLM-Inferenz
- **OpenAI API Key**: Als Fallback oder Primary LLM

---

## 🚀 Production Setup

### 1. Server Vorbereitung

```bash
# System updates
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# oder
sudo yum update -y  # RHEL/CentOS

# Python 3.10+ installieren (falls nicht vorhanden)
sudo apt install python3.10 python3.10-venv python3-pip -y

# Optional: Ollama installieren
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository-url>
cd agent-platform

# Virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import agent_platform; print('✅ Import successful')"
```

### 3. Konfiguration

#### Production .env File

```bash
# Erstelle .env file
cat > .env << 'EOF'
# ============================================================================
# PRODUCTION CONFIGURATION
# ============================================================================

# Database
DATABASE_URL=sqlite:///./data/agent_platform.db
# Für PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/agent_platform_db

# ============================================================================
# LLM CONFIGURATION (Optional - System works without!)
# ============================================================================

# Ollama (Local LLM - Primary)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=gptoss20b

# OpenAI (Fallback)
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_MODEL=gpt-4o

# ============================================================================
# CLASSIFICATION CONFIGURATION
# ============================================================================

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD=0.85
MEDIUM_CONFIDENCE_THRESHOLD=0.60

# Learning rate (EMA)
LEARNING_RATE=0.15

# ============================================================================
# SCHEDULER CONFIGURATION
# ============================================================================

# Daily Digest
DIGEST_HOUR=9
DIGEST_MINUTE=0
DIGEST_EMAIL=user@example.com

# Feedback Check
FEEDBACK_CHECK_INTERVAL_HOURS=1

# Queue Cleanup
CLEANUP_HOUR=2
CLEANUP_MINUTE=0
CLEANUP_DAYS_TO_KEEP=30

# ============================================================================
# EMAIL ACCOUNTS (Optional - for email tool integration)
# ============================================================================

# Gmail Account 1
GMAIL_1_EMAIL=user@gmail.com
GMAIL_1_CREDENTIALS_PATH=credentials/gmail_1_credentials.json
GMAIL_1_TOKEN_PATH=tokens/gmail_1_token.json

# Ionos Account
IONOS_EMAIL=user@ionos.de
IONOS_PASSWORD=your-password
IONOS_IMAP_SERVER=imap.ionos.de
IONOS_SMTP_SERVER=smtp.ionos.de

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL=INFO
LOG_FILE=logs/agent_platform.log

EOF

# Set permissions
chmod 600 .env
```

#### Directory Structure

```bash
# Create necessary directories
mkdir -p data logs credentials tokens

# Set permissions
chmod 700 data credentials tokens
chmod 755 logs
```

### 4. Database Initialisierung

```bash
# Initialize database
python -c "from agent_platform.db.database import init_db; init_db()"

# Verify tables created
python << 'EOF'
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail, ReviewQueueItem

with get_db() as db:
    print(f"ProcessedEmail table exists: {db.query(ProcessedEmail).count() >= 0}")
    print(f"ReviewQueueItem table exists: {db.query(ReviewQueueItem).count() >= 0}")
    print("✅ Database initialized successfully")
EOF
```

### 5. Ollama Setup (Optional)

```bash
# Start Ollama service
ollama serve &

# Pull model
ollama pull gptoss20b

# Verify
curl http://localhost:11434/v1/models

# Should return list including gptoss20b
```

---

## 🔧 Production Configuration

### Systemd Service (Linux)

Erstelle `/etc/systemd/system/agent-platform.service`:

```ini
[Unit]
Description=Agent Platform Email Classification
After=network.target postgresql.service
# Remove postgresql.service if using SQLite

[Service]
Type=simple
User=agent-platform
Group=agent-platform
WorkingDirectory=/opt/agent-platform
Environment="PATH=/opt/agent-platform/venv/bin"
EnvironmentFile=/opt/agent-platform/.env

# Main service command (scheduler)
ExecStart=/opt/agent-platform/venv/bin/python -m agent_platform.orchestration.scheduler_jobs

# Restart on failure
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=append:/var/log/agent-platform/service.log
StandardError=append:/var/log/agent-platform/error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/agent-platform/data /opt/agent-platform/logs

[Install]
WantedBy=multi-user.target
```

#### Service Management

```bash
# Enable service
sudo systemctl enable agent-platform

# Start service
sudo systemctl start agent-platform

# Check status
sudo systemctl status agent-platform

# View logs
sudo journalctl -u agent-platform -f

# Restart
sudo systemctl restart agent-platform
```

### Nginx Reverse Proxy (Optional - für API)

Falls Sie eine API exponen möchten:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## 📊 Monitoring & Logging

### Log Rotation

Erstelle `/etc/logrotate.d/agent-platform`:

```conf
/opt/agent-platform/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 agent-platform agent-platform
    sharedscripts
    postrotate
        systemctl reload agent-platform > /dev/null 2>&1 || true
    endscript
}
```

### Health Check Script

```bash
#!/bin/bash
# /opt/agent-platform/healthcheck.sh

# Check if service is running
systemctl is-active --quiet agent-platform
if [ $? -ne 0 ]; then
    echo "❌ Service not running"
    exit 1
fi

# Check database connection
python3 << 'EOF'
from agent_platform.db.database import get_db
try:
    with get_db() as db:
        db.execute("SELECT 1")
    print("✅ Database OK")
except Exception as e:
    print(f"❌ Database error: {e}")
    exit(1)
EOF

# Check Ollama (if configured)
if [ -n "$OLLAMA_BASE_URL" ]; then
    curl -sf http://localhost:11434/v1/models > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Ollama OK"
    else
        echo "⚠️  Ollama not available (fallback to OpenAI)"
    fi
fi

echo "✅ Health check passed"
exit 0
```

### Monitoring Script

```python
# /opt/agent-platform/monitor.py
"""Production monitoring script"""

from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail, ReviewQueueItem
from datetime import datetime, timedelta

def monitor():
    with get_db() as db:
        # Last 24 hours stats
        cutoff = datetime.utcnow() - timedelta(hours=24)

        processed_count = db.query(ProcessedEmail).filter(
            ProcessedEmail.processed_at >= cutoff
        ).count()

        pending_reviews = db.query(ReviewQueueItem).filter(
            ReviewQueueItem.status == 'pending'
        ).count()

        print(f"📊 Last 24h:")
        print(f"   Processed: {processed_count} emails")
        print(f"   Pending reviews: {pending_reviews}")

        if pending_reviews > 50:
            print("⚠️  High review queue - consider adjusting thresholds")

if __name__ == "__main__":
    monitor()
```

Run via cron:
```cron
# Monitor every hour
0 * * * * /opt/agent-platform/venv/bin/python /opt/agent-platform/monitor.py >> /var/log/agent-platform/monitor.log 2>&1
```

---

## 🔒 Security

### File Permissions

```bash
# Application directory
chown -R agent-platform:agent-platform /opt/agent-platform
chmod 750 /opt/agent-platform

# Sensitive files
chmod 600 /opt/agent-platform/.env
chmod 600 /opt/agent-platform/credentials/*
chmod 600 /opt/agent-platform/tokens/*

# Database
chmod 640 /opt/agent-platform/data/agent_platform.db
```

### Firewall

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Secrets Management

Für Production, verwenden Sie einen Secrets Manager:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id agent-platform/openai-key

# Azure Key Vault
az keyvault secret show --vault-name agent-platform --name openai-key

# HashiCorp Vault
vault kv get secret/agent-platform/openai-key
```

---

## 📈 Performance Tuning

### Database Optimization (PostgreSQL)

```sql
-- Create indexes
CREATE INDEX idx_processed_emails_account_sender
ON processed_emails(account_id, sender);

CREATE INDEX idx_processed_emails_processed_at
ON processed_emails(processed_at DESC);

CREATE INDEX idx_review_queue_status_added
ON review_queue(status, added_to_queue_at);

CREATE INDEX idx_sender_preferences_account_sender
ON sender_preferences(account_id, sender_email);

-- Analyze tables
ANALYZE processed_emails;
ANALYZE review_queue;
ANALYZE sender_preferences;
```

### Connection Pooling

```python
# In agent_platform/db/database.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Check connections before using
)
```

### Caching (Optional)

```python
# In-memory cache for frequent lookups
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_sender_preference_cached(account_id: str, sender: str):
    # Cache sender preferences
    pass
```

---

## 🔄 Backup & Recovery

### Database Backup

```bash
#!/bin/bash
# /opt/agent-platform/backup.sh

BACKUP_DIR=/opt/agent-platform/backups
DATE=$(date +%Y%m%d_%H%M%S)

# SQLite
cp /opt/agent-platform/data/agent_platform.db \
   $BACKUP_DIR/agent_platform_$DATE.db

# PostgreSQL
# pg_dump agent_platform_db | gzip > $BACKUP_DIR/agent_platform_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "agent_platform_*.db" -mtime +30 -delete

echo "✅ Backup completed: $DATE"
```

Cron job:
```cron
# Daily backup at 3 AM
0 3 * * * /opt/agent-platform/backup.sh >> /var/log/agent-platform/backup.log 2>&1
```

### Recovery

```bash
# Stop service
sudo systemctl stop agent-platform

# Restore database
cp /opt/agent-platform/backups/agent_platform_YYYYMMDD_HHMMSS.db \
   /opt/agent-platform/data/agent_platform.db

# Restart service
sudo systemctl start agent-platform
```

---

## 🧪 Production Testing

### Pre-Deployment Checklist

```bash
# 1. Run all tests
python tests/test_classification_layers.py
python tests/test_feedback_tracking.py
python tests/test_review_system.py

# 2. Check configuration
python -c "from agent_platform.core.config import Config; print('✅ Config OK')"

# 3. Check database
python -c "from agent_platform.db.database import get_db; \
           with get_db() as db: db.execute('SELECT 1'); \
           print('✅ Database OK')"

# 4. Check LLM providers (if configured)
python -c "from agent_platform.llm.providers import UnifiedLLMProvider; \
           import asyncio; \
           p = UnifiedLLMProvider(); \
           asyncio.run(p.complete([{'role': 'user', 'content': 'test'}])); \
           print('✅ LLM OK')"

# 5. Healthcheck
./healthcheck.sh
```

### Smoke Test

```python
# smoke_test.py
import asyncio
from agent_platform.classification import UnifiedClassifier, EmailToClassify

async def smoke_test():
    print("🧪 Running smoke test...")

    classifier = UnifiedClassifier()

    # Test email
    email = EmailToClassify(
        email_id="smoke_test",
        account_id="test",
        sender="test@example.com",
        subject="Test Email",
        body="This is a test",
    )

    result = await classifier.classify(email)

    assert result.category in ['spam', 'newsletter', 'wichtig', 'nice_to_know', 'action_required', 'system_notifications']
    assert 0 <= result.importance <= 1
    assert 0 <= result.confidence <= 1

    print("✅ Smoke test passed")
    print(f"   Category: {result.category}")
    print(f"   Confidence: {result.confidence:.0%}")

asyncio.run(smoke_test())
```

---

## 📧 Email Integration (Optional)

### Gmail OAuth Setup

```bash
# 1. Download credentials from Google Cloud Console
# 2. Place in credentials/gmail_1_credentials.json

# 3. First-time OAuth
python << 'EOF'
from modules.email.tools.gmail_tools import get_gmail_service

service = get_gmail_service(
    'gmail_1',
    'credentials/gmail_1_credentials.json',
    'tokens/gmail_1_token.json'
)
print("✅ Gmail authenticated")
EOF

# Browser will open for OAuth consent
# Token saved to tokens/gmail_1_token.json
```

### Ionos IMAP Setup

Credentials in `.env` file (see above). No additional setup needed.

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u agent-platform -n 50

# Check permissions
ls -la /opt/agent-platform/data

# Check Python version
python3 --version

# Check virtual environment
which python
```

### Database Errors

```bash
# Check database file
ls -la /opt/agent-platform/data/agent_platform.db

# Check SQLite version
sqlite3 --version

# Rebuild database
python -c "from agent_platform.db.database import init_db; init_db()"
```

### LLM Errors

```bash
# Check Ollama
curl http://localhost:11434/v1/models

# Check OpenAI key
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
           print('✅ Key loaded' if os.getenv('OPENAI_API_KEY') else '❌ No key')"

# Test provider
python << 'EOF'
from agent_platform.llm.providers import UnifiedLLMProvider
import asyncio

async def test():
    provider = UnifiedLLMProvider()
    response, provider_used = await provider.complete([
        {"role": "user", "content": "Hi"}
    ])
    print(f"✅ Provider {provider_used} works")

asyncio.run(test())
EOF
```

---

## 📊 Scaling

### Horizontal Scaling

Für hohe Last, mehrere Instances mit Load Balancer:

```
┌─────────────┐
│Load Balancer│
└──────┬──────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
│Inst1│ │Inst2│ │Inst3│ │Inst4│
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   │       │       │       │
   └───────┴───┬───┴───────┘
               │
        ┌──────▼──────┐
        │  PostgreSQL │
        │  (Shared DB)│
        └─────────────┘
```

### Database Migration

```bash
# Migrate from SQLite to PostgreSQL
# 1. Export SQLite
sqlite3 agent_platform.db .dump > export.sql

# 2. Import to PostgreSQL
psql agent_platform_db < export.sql

# 3. Update .env
DATABASE_URL=postgresql://user:pass@localhost/agent_platform_db

# 4. Restart service
sudo systemctl restart agent-platform
```

---

## ✅ Production Checklist

- [ ] Server vorbereitet (Python 3.10+, dependencies)
- [ ] Application deployed in `/opt/agent-platform`
- [ ] Virtual environment erstellt und aktiviert
- [ ] `.env` file konfiguriert
- [ ] Database initialisiert
- [ ] Ollama installiert und model gepullt (optional)
- [ ] Systemd service erstellt und enabled
- [ ] Log rotation konfiguriert
- [ ] File permissions gesetzt
- [ ] Firewall konfiguriert
- [ ] Backups eingerichtet
- [ ] Health check script erstellt
- [ ] Monitoring eingerichtet
- [ ] Alle Tests laufen grün
- [ ] Smoke test erfolgreich
- [ ] Service gestartet und läuft

---

**Ready for Production!** 🚀
