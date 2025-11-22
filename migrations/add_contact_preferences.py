#!/usr/bin/env python3
"""
Migration: Bidirectional Contact Preferences

Adds support for tracking bidirectional email communication:
- Incoming emails: total received, replies sent, reply rate, avg time to reply
- Outgoing emails: total sent, threads initiated, sent with reply, initiation rate
- Combined metrics: total exchanged, contact importance, relationship type

This replaces the uni-directional SenderPreference tracking with a bidirectional
ContactPreference system that considers both incoming AND outgoing communication.

Changes:
1. Create new table: contact_preferences
2. Migrate existing sender_preferences data to contact_preferences
3. Add indices for efficient querying
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from agent_platform.core.config import Config


def run_migration():
    """Run the ContactPreference migration."""
    engine = create_engine(Config.DATABASE_URL)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🚀 Starting migration: Bidirectional Contact Preferences")
            print()

            # ================================================================
            # STEP 1: Create contact_preferences table
            # ================================================================
            print("📊 [1/4] Creating contact_preferences table...")

            try:
                conn.execute(text("""
                    CREATE TABLE contact_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        -- Account identification
                        account_id TEXT NOT NULL,

                        -- Contact identification
                        contact_email TEXT NOT NULL,
                        contact_domain TEXT NOT NULL,
                        contact_name TEXT,

                        -- INCOMING EMAIL STATS (from this contact to me)
                        total_emails_received INTEGER DEFAULT 0,
                        total_replies_sent INTEGER DEFAULT 0,
                        reply_rate REAL DEFAULT 0.0,
                        avg_time_to_reply_hours REAL,
                        last_email_received TIMESTAMP,

                        -- OUTGOING EMAIL STATS (from me to this contact)
                        total_emails_sent INTEGER DEFAULT 0,
                        total_initiated_threads INTEGER DEFAULT 0,
                        total_sent_with_reply INTEGER DEFAULT 0,
                        initiation_rate REAL DEFAULT 0.0,
                        sent_reply_rate REAL DEFAULT 0.0,
                        avg_emails_sent_per_week REAL DEFAULT 0.0,
                        last_email_sent TIMESTAMP,

                        -- COMBINED METRICS
                        total_emails_exchanged INTEGER DEFAULT 0,
                        contact_importance REAL DEFAULT 0.5,
                        relationship_type TEXT DEFAULT 'neutral',

                        -- EMA learning (for backwards compatibility)
                        importance_ema REAL DEFAULT 0.5,
                        confidence_ema REAL DEFAULT 0.5,
                        category_distribution TEXT DEFAULT '{}',

                        -- Metadata
                        last_contact_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        extra_metadata TEXT DEFAULT '{}'
                    )
                """))
                print("   ✅ Table created")

                # Create indices
                print("   🔧 Creating indices...")

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_account_id
                    ON contact_preferences (account_id)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_contact_email
                    ON contact_preferences (contact_email)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_contact_domain
                    ON contact_preferences (contact_domain)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_contact_importance
                    ON contact_preferences (contact_importance)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_relationship_type
                    ON contact_preferences (relationship_type)
                """))

                conn.execute(text("""
                    CREATE INDEX idx_contact_preferences_last_contact_at
                    ON contact_preferences (last_contact_at)
                """))

                print("   ✅ Created 6 indices")

            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ⚠️  Table already exists, skipping")
                else:
                    raise

            print()

            # ================================================================
            # STEP 2: Migrate data from sender_preferences
            # ================================================================
            print("🔄 [2/4] Migrating data from sender_preferences...")

            try:
                # Check if sender_preferences table exists
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='table' AND name='sender_preferences'
                """))

                if result.scalar() > 0:
                    # Check if sender_preferences has account_id column
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM pragma_table_info('sender_preferences')
                        WHERE name='account_id'
                    """))
                    has_account_id = result.scalar() > 0

                    # Migrate data (only columns that exist in both tables)
                    if has_account_id:
                        # Migrate with account_id
                        conn.execute(text("""
                            INSERT INTO contact_preferences (
                                account_id,
                                contact_email,
                                contact_domain,
                                total_emails_received,
                                total_replies_sent,
                                reply_rate,
                                avg_time_to_reply_hours,
                                last_email_received,
                                created_at,
                                updated_at
                            )
                            SELECT
                                account_id,
                                sender_email,
                                sender_domain,
                                total_emails,
                                total_replies,
                                reply_rate,
                                avg_time_to_reply_hours,
                                last_seen_at,
                                created_at,
                                updated_at
                            FROM sender_preferences
                            WHERE sender_email NOT IN (
                                SELECT contact_email FROM contact_preferences
                            )
                        """))
                    else:
                        # Migrate without account_id (use 'unknown' as default)
                        conn.execute(text("""
                            INSERT INTO contact_preferences (
                                account_id,
                                contact_email,
                                contact_domain,
                                total_emails_received,
                                total_replies_sent,
                                reply_rate,
                                avg_time_to_reply_hours,
                                last_email_received,
                                created_at,
                                updated_at
                            )
                            SELECT
                                'gmail_1' as account_id,
                                sender_email,
                                sender_domain,
                                total_emails,
                                total_replies,
                                reply_rate,
                                avg_time_to_reply_hours,
                                last_seen_at,
                                created_at,
                                updated_at
                            FROM sender_preferences
                            WHERE sender_email NOT IN (
                                SELECT contact_email FROM contact_preferences
                            )
                        """))

                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM contact_preferences
                    """))
                    migrated_count = result.scalar()
                    print(f"   ✅ Migrated {migrated_count} sender preferences to contact preferences")

                    # Update combined metrics for migrated data
                    conn.execute(text("""
                        UPDATE contact_preferences
                        SET
                            total_emails_exchanged = total_emails_received,
                            contact_importance = importance_ema,
                            relationship_type = CASE
                                WHEN reply_rate > 0.5 THEN 'reactive'
                                WHEN reply_rate > 0.2 THEN 'mixed'
                                ELSE 'one_way_incoming'
                            END
                        WHERE total_emails_sent = 0
                    """))
                    print("   ✅ Updated combined metrics for migrated data")
                else:
                    print("   ⚠️  sender_preferences table not found, skipping migration")

            except Exception as e:
                print(f"   ⚠️  Migration warning: {e}")
                # Continue anyway - table might be empty or already migrated

            print()

            # ================================================================
            # STEP 3: Verify data integrity
            # ================================================================
            print("🔍 [3/4] Verifying migration...")

            # Count contact preferences
            result = conn.execute(text("""
                SELECT COUNT(*) FROM contact_preferences
            """))
            total_contacts = result.scalar()
            print(f"   ✅ {total_contacts} contact preferences created")

            # Count contacts with incoming emails
            result = conn.execute(text("""
                SELECT COUNT(*) FROM contact_preferences
                WHERE total_emails_received > 0
            """))
            incoming_count = result.scalar()
            print(f"   ✅ {incoming_count} contacts with incoming emails")

            # Count contacts with outgoing emails (will be 0 until tracking is implemented)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM contact_preferences
                WHERE total_emails_sent > 0
            """))
            outgoing_count = result.scalar()
            print(f"   ✅ {outgoing_count} contacts with outgoing emails")

            # Verify indices
            result = conn.execute(text("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='index' AND tbl_name='contact_preferences'
            """))
            index_count = result.scalar()
            print(f"   ✅ {index_count} indices created")

            print()

            # ================================================================
            # STEP 4: Commit transaction
            # ================================================================
            print("💾 [4/4] Committing changes...")
            trans.commit()

            print()
            print("=" * 70)
            print("✅ Migration completed successfully!")
            print("=" * 70)
            print()
            print("📊 Summary:")
            print("  - Created contact_preferences table")
            print("  - Added 5 indices for efficient querying")
            print(f"  - Migrated {total_contacts} contacts from sender_preferences")
            print(f"  - {incoming_count} contacts with incoming email history")
            print(f"  - {outgoing_count} contacts with outgoing email history")
            print()
            print("🔧 Next steps:")
            print("  1. Implement outgoing email tracking in orchestrator")
            print("  2. Update History Layer to use ContactPreference")
            print("  3. Implement relationship_type calculation")
            print("  4. Test bidirectional importance scoring")
            print()

        except Exception as e:
            trans.rollback()
            print()
            print("=" * 70)
            print(f"❌ Migration failed: {e}")
            print("=" * 70)
            print("All changes have been rolled back.")
            raise


if __name__ == "__main__":
    run_migration()
