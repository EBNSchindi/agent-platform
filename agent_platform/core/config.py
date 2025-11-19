"""
Platform Configuration
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from enum import Enum

# Load environment variables
load_dotenv()


class Mode(Enum):
    """Email processing modes"""
    DRAFT = "draft"              # Generate drafts for review
    AUTO_REPLY = "auto_reply"    # Send replies automatically (low-risk only)
    MANUAL = "manual"            # Classification only, no drafts


class Config:
    """Platform-wide configuration"""

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///platform.db")

    # Scheduler Settings
    INBOX_CHECK_INTERVAL_HOURS: int = int(os.getenv("INBOX_CHECK_INTERVAL_HOURS", "1"))
    BACKUP_DAY_OF_MONTH: int = int(os.getenv("BACKUP_DAY_OF_MONTH", "1"))
    BACKUP_HOUR: int = int(os.getenv("BACKUP_HOUR", "3"))

    # LLM Provider Configuration (Ollama-First with OpenAI Fallback)
    # Ollama (Local - Primary)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gptoss20b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    # OpenAI (Cloud - Fallback)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Fallback Strategy
    LLM_FALLBACK_ENABLED: bool = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"

    # Importance Classifier Thresholds
    IMPORTANCE_CONFIDENCE_HIGH_THRESHOLD: float = float(os.getenv("IMPORTANCE_CONFIDENCE_HIGH_THRESHOLD", "0.85"))
    IMPORTANCE_CONFIDENCE_MEDIUM_THRESHOLD: float = float(os.getenv("IMPORTANCE_CONFIDENCE_MEDIUM_THRESHOLD", "0.6"))
    IMPORTANCE_SCORE_LOW_THRESHOLD: float = float(os.getenv("IMPORTANCE_SCORE_LOW_THRESHOLD", "0.4"))
    IMPORTANCE_SCORE_HIGH_THRESHOLD: float = float(os.getenv("IMPORTANCE_SCORE_HIGH_THRESHOLD", "0.7"))

    # Review System
    DAILY_DIGEST_ENABLED: bool = os.getenv("DAILY_DIGEST_ENABLED", "true").lower() == "true"
    DAILY_DIGEST_TIME: str = os.getenv("DAILY_DIGEST_TIME", "08:00")

    # Feedback Tracking
    FEEDBACK_TRACKING_ENABLED: bool = os.getenv("FEEDBACK_TRACKING_ENABLED", "true").lower() == "true"
    FEEDBACK_CHECK_INTERVAL_HOURS: int = int(os.getenv("FEEDBACK_CHECK_INTERVAL_HOURS", "1"))

    # Email Module (Legacy - keep for backward compatibility)
    DEFAULT_MODE: Mode = Mode(os.getenv("DEFAULT_MODE", "draft"))
    CLASSIFIER_BATCH_SIZE: int = int(os.getenv("CLASSIFIER_BATCH_SIZE", "10"))
    RESPONDER_CONFIDENCE_THRESHOLD: float = float(os.getenv("RESPONDER_CONFIDENCE_THRESHOLD", "0.85"))

    # Gmail Accounts
    GMAIL_ACCOUNTS = {
        "gmail_1": {
            "email": os.getenv("GMAIL_1_EMAIL", ""),
            "credentials_path": os.getenv("GMAIL_1_CREDENTIALS_PATH", ""),
            "token_path": os.getenv("GMAIL_1_TOKEN_PATH", ""),
        },
        "gmail_2": {
            "email": os.getenv("GMAIL_2_EMAIL", ""),
            "credentials_path": os.getenv("GMAIL_2_CREDENTIALS_PATH", ""),
            "token_path": os.getenv("GMAIL_2_TOKEN_PATH", ""),
        },
        "gmail_3": {
            "email": os.getenv("GMAIL_3_EMAIL", ""),
            "credentials_path": os.getenv("GMAIL_3_CREDENTIALS_PATH", ""),
            "token_path": os.getenv("GMAIL_3_TOKEN_PATH", ""),
        },
    }

    # Ionos Account
    IONOS_ACCOUNT = {
        "email": os.getenv("IONOS_EMAIL", ""),
        "password": os.getenv("IONOS_PASSWORD", ""),
        "imap_server": os.getenv("IONOS_IMAP_SERVER", "imap.ionos.de"),
        "imap_port": int(os.getenv("IONOS_IMAP_PORT", "993")),
        "smtp_server": os.getenv("IONOS_SMTP_SERVER", "smtp.ionos.de"),
        "smtp_port": int(os.getenv("IONOS_SMTP_PORT", "587")),
    }

    # Backup Account
    BACKUP_ACCOUNT = {
        "email": os.getenv("BACKUP_EMAIL", ""),
        "credentials_path": os.getenv("BACKUP_CREDENTIALS_PATH", ""),
        "token_path": os.getenv("BACKUP_TOKEN_PATH", ""),
    }

    # Account Modes (configurable per account)
    ACCOUNT_MODES = {
        "gmail_1": DEFAULT_MODE,
        "gmail_2": DEFAULT_MODE,
        "gmail_3": DEFAULT_MODE,
        "ionos": DEFAULT_MODE,
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")

        # Check at least one email account is configured
        gmail_configured = any(acc["email"] for acc in cls.GMAIL_ACCOUNTS.values())
        ionos_configured = bool(cls.IONOS_ACCOUNT["email"])

        if not (gmail_configured or ionos_configured):
            raise ValueError("At least one email account must be configured")

        return True

    @classmethod
    def get_account_mode(cls, account_id: str) -> Mode:
        """Get processing mode for specific account"""
        return cls.ACCOUNT_MODES.get(account_id, cls.DEFAULT_MODE)

    @classmethod
    def set_account_mode(cls, account_id: str, mode: Mode):
        """Set processing mode for specific account"""
        cls.ACCOUNT_MODES[account_id] = mode


# Validate configuration on module load
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration warning: {e}")
    print("   Please set up .env file with required credentials")
