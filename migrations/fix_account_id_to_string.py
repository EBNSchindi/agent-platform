#!/usr/bin/env python3
"""
Migration: Change account_id from Integer FK to String

Changes ProcessedEmail.account_id from Integer ForeignKey to String
to support dynamic account discovery without FK constraints.
"""

import sys
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from sqlalchemy import create_engine, text
from agent_platform.core.config import Config

def run_migration():
    """Run the migration to change account_id to String."""
    engine = create_engine(Config.DATABASE_URL)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🔧 Starting migration: account_id Integer → String")

            # 1. Create new table with String account_id
            print("   Creating new processed_emails_new table...")
            conn.execute(text("""
                CREATE TABLE processed_emails_new (
                    id INTEGER PRIMARY KEY,
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
                    storage_level TEXT DEFAULT 'full' NOT NULL,
                    body_text TEXT,
                    body_html TEXT,
                    snippet TEXT,
                    thread_id TEXT,
                    in_reply_to TEXT,
                    email_references TEXT,
                    labels TEXT,
                    attachments_metadata TEXT
                )
            """))

            # 2. Create indices on new table
            print("   Creating indices...")
            conn.execute(text("""
                CREATE INDEX idx_processed_emails_new_account_id ON processed_emails_new (account_id)
            """))
            conn.execute(text("""
                CREATE INDEX idx_processed_emails_new_storage_level ON processed_emails_new (storage_level)
            """))

            # 3. Map old FK integer account_ids to string account_ids
            #    Since we don't have the email_accounts table populated,
            #    we'll just use the integer as string for now
            print("   Copying data with account_id conversion...")
            conn.execute(text("""
                INSERT INTO processed_emails_new
                SELECT
                    id,
                    CAST(account_id AS TEXT) as account_id,
                    email_id,
                    message_id,
                    subject,
                    sender,
                    received_at,
                    processed_at,
                    category,
                    confidence,
                    suggested_label,
                    should_reply,
                    urgency,
                    importance_score,
                    classification_confidence,
                    llm_provider_used,
                    rule_layer_hint,
                    history_layer_hint,
                    storage_level,
                    body_text,
                    body_html,
                    snippet,
                    thread_id,
                    in_reply_to,
                    references as email_references,
                    labels,
                    attachments_metadata
                FROM processed_emails
            """))

            # 4. Drop old table
            print("   Dropping old table...")
            conn.execute(text("DROP TABLE processed_emails"))

            # 5. Rename new table
            print("   Renaming new table...")
            conn.execute(text("ALTER TABLE processed_emails_new RENAME TO processed_emails"))

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")
            print("   account_id is now TEXT instead of INTEGER FK")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
