#!/usr/bin/env python3
"""
Migration: Properly fix processed_emails schema

Issues to fix:
1. account_id should be TEXT not INT
2. id column should be INTEGER PRIMARY KEY AUTOINCREMENT
3. All existing data needs to be preserved if possible
"""

import sys
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from sqlalchemy import create_engine, text
from agent_platform.core.config import Config

def run_migration():
    """Run the migration to properly fix the schema."""
    engine = create_engine(Config.DATABASE_URL)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🔧 Starting migration: Fix processed_emails schema")

            # 1. Drop the corrupted table (data is already lost from previous migration)
            print("   Dropping corrupted table...")
            conn.execute(text("DROP TABLE IF EXISTS processed_emails"))

            # 2. Create new table with correct schema
            print("   Creating new processed_emails table with correct schema...")
            conn.execute(text("""
                CREATE TABLE processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    email_id TEXT NOT NULL,
                    message_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    received_at TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category TEXT,
                    confidence REAL,
                    suggested_label TEXT,
                    should_reply INTEGER DEFAULT 0,
                    urgency TEXT,
                    importance_score REAL,
                    classification_confidence REAL,
                    llm_provider_used TEXT,
                    rule_layer_hint TEXT,
                    history_layer_hint TEXT,
                    draft_generated INTEGER DEFAULT 0,
                    draft_id TEXT,
                    replied INTEGER DEFAULT 0,
                    replied_at TIMESTAMP,
                    extra_metadata JSON,
                    storage_level TEXT DEFAULT 'full' NOT NULL,
                    summary TEXT,
                    body_text TEXT,
                    body_html TEXT,
                    snippet TEXT,
                    thread_id TEXT,
                    thread_summary TEXT,
                    thread_position INTEGER,
                    is_thread_start INTEGER DEFAULT 0,
                    in_reply_to TEXT,
                    email_references TEXT,
                    labels TEXT,
                    has_attachments INTEGER DEFAULT 0,
                    attachment_count INTEGER DEFAULT 0,
                    attachments_metadata JSON,
                    user_corrected INTEGER DEFAULT 0,
                    user_corrected_at TIMESTAMP,
                    original_category TEXT,
                    original_confidence REAL,
                    gmail_label_applied TEXT,
                    gmail_archived INTEGER DEFAULT 0,
                    gmail_marked_read INTEGER DEFAULT 0
                )
            """))

            # 3. Create indices
            print("   Creating indices...")
            conn.execute(text("""
                CREATE INDEX idx_processed_emails_account_id ON processed_emails (account_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_processed_emails_storage_level ON processed_emails (storage_level)
            """))
            conn.execute(text("""
                CREATE INDEX idx_processed_emails_category ON processed_emails (category)
            """))

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")
            print("   Schema fixed: account_id is now TEXT, id is AUTOINCREMENT")
            print("   Ready to load emails")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
