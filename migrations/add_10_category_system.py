#!/usr/bin/env python3
"""
Migration: 10-Category System (Phase 8)

Adds support for 10 fine-grained email categories with primary/secondary classification:
- New categories: wichtig_todo, termine, finanzen, bestellungen, job_projekte,
                  vertraege, persoenlich, newsletter, werbung, spam
- Primary + Secondary category support (1 primary + 0-3 secondary)
- Multi-label Gmail support (primary + secondary as labels)
- Single folder IONOS support (primary only)
- Enhanced sender profiling (trust_level, whitelist/blacklist, category preferences)
- NLP intent tracking and user preference rules

Changes:
1. ProcessedEmail: Add primary_category, secondary_categories, category_confidence,
                   gmail_labels_applied, ionos_folder_applied
2. SenderPreference: Add trust_level, is_whitelisted, is_blacklisted,
                     allowed_categories, muted_categories, preferred_primary_category
3. New table: user_preference_rules
4. New table: nlp_intents
5. Migrate old category values to new primary_category
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from agent_platform.core.config import Config

# Category mapping: Old → New
OLD_TO_NEW_CATEGORY_MAP = {
    "wichtig": "wichtig_todo",
    "action_required": "wichtig_todo",
    "nice_to_know": "newsletter",
    "newsletter": "newsletter",
    "system_notifications": "newsletter",
    "spam": "spam",
}

def run_migration():
    """Run the 10-category system migration."""
    engine = create_engine(Config.DATABASE_URL)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🚀 Starting migration: 10-Category System (Phase 8)")
            print()

            # ================================================================
            # STEP 1: Update processed_emails table
            # ================================================================
            print("📊 [1/6] Updating processed_emails table...")

            # Add new columns
            columns_to_add = [
                ("primary_category", "TEXT"),
                ("secondary_categories", "TEXT DEFAULT '[]'"),  # JSON array as TEXT
                ("category_confidence", "REAL"),
                ("gmail_labels_applied", "TEXT DEFAULT '[]'"),  # JSON array
                ("ionos_folder_applied", "TEXT"),
            ]

            for col_name, col_type in columns_to_add:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE processed_emails
                        ADD COLUMN {col_name} {col_type}
                    """))
                    print(f"   ✅ Added column: {col_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"   ⚠️  Column {col_name} already exists, skipping")
                    else:
                        raise

            # Migrate old category to new primary_category
            print("   🔄 Migrating old categories to primary_category...")
            for old_cat, new_cat in OLD_TO_NEW_CATEGORY_MAP.items():
                result = conn.execute(text(f"""
                    UPDATE processed_emails
                    SET primary_category = :new_cat
                    WHERE category = :old_cat AND primary_category IS NULL
                """), {"old_cat": old_cat, "new_cat": new_cat})
                count = result.rowcount
                if count > 0:
                    print(f"      {old_cat} → {new_cat} ({count} emails)")

            # Set category_confidence from existing confidence field
            conn.execute(text("""
                UPDATE processed_emails
                SET category_confidence = confidence
                WHERE category_confidence IS NULL AND confidence IS NOT NULL
            """))
            print("   ✅ Migrated confidence scores")

            # Create index on primary_category
            try:
                conn.execute(text("""
                    CREATE INDEX idx_processed_emails_primary_category
                    ON processed_emails (primary_category)
                """))
                print("   ✅ Created index on primary_category")
            except:
                print("   ⚠️  Index on primary_category already exists")

            print()

            # ================================================================
            # STEP 2: Update sender_preferences table
            # ================================================================
            print("👤 [2/6] Updating sender_preferences table...")

            sender_columns = [
                ("trust_level", "TEXT DEFAULT 'neutral'"),
                ("is_whitelisted", "INTEGER DEFAULT 0"),  # Boolean as INTEGER
                ("is_blacklisted", "INTEGER DEFAULT 0"),
                ("allowed_categories", "TEXT DEFAULT '[]'"),  # JSON array
                ("muted_categories", "TEXT DEFAULT '[]'"),
                ("preferred_primary_category", "TEXT"),
            ]

            for col_name, col_type in sender_columns:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE sender_preferences
                        ADD COLUMN {col_name} {col_type}
                    """))
                    print(f"   ✅ Added column: {col_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"   ⚠️  Column {col_name} already exists, skipping")
                    else:
                        raise

            # Create indices
            try:
                conn.execute(text("""
                    CREATE INDEX idx_sender_preferences_trust_level
                    ON sender_preferences (trust_level)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_sender_preferences_is_whitelisted
                    ON sender_preferences (is_whitelisted)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_sender_preferences_is_blacklisted
                    ON sender_preferences (is_blacklisted)
                """))
                print("   ✅ Created indices on trust/whitelist/blacklist fields")
            except:
                print("   ⚠️  Indices already exist")

            print()

            # ================================================================
            # STEP 3: Create user_preference_rules table
            # ================================================================
            print("📋 [3/6] Creating user_preference_rules table...")

            try:
                conn.execute(text("""
                    CREATE TABLE user_preference_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id TEXT UNIQUE NOT NULL,
                        account_id TEXT NOT NULL,
                        priority INTEGER DEFAULT 100,
                        applies_to TEXT NOT NULL,
                        pattern TEXT NOT NULL,
                        if_primary_category TEXT,
                        if_has_secondary TEXT DEFAULT '[]',
                        if_sender_domain TEXT,
                        action TEXT NOT NULL,
                        action_params TEXT DEFAULT '{}',
                        created_via TEXT DEFAULT 'manual',
                        source_text TEXT,
                        active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_applied_at TIMESTAMP,
                        times_applied INTEGER DEFAULT 0,
                        extra_metadata TEXT DEFAULT '{}'
                    )
                """))
                print("   ✅ Table created")

                # Create indices
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_rule_id
                    ON user_preference_rules (rule_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_account_id
                    ON user_preference_rules (account_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_priority
                    ON user_preference_rules (priority)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_applies_to
                    ON user_preference_rules (applies_to)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_pattern
                    ON user_preference_rules (pattern)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_action
                    ON user_preference_rules (action)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_user_preference_rules_active
                    ON user_preference_rules (active)
                """))
                print("   ✅ Created indices")

            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ⚠️  Table already exists, skipping")
                else:
                    raise

            print()

            # ================================================================
            # STEP 4: Create nlp_intents table
            # ================================================================
            print("💬 [4/6] Creating nlp_intents table...")

            try:
                conn.execute(text("""
                    CREATE TABLE nlp_intents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        intent_id TEXT UNIQUE NOT NULL,
                        account_id TEXT NOT NULL,
                        source_text TEXT NOT NULL,
                        source_channel TEXT DEFAULT 'gui_chat',
                        parsed_intent TEXT NOT NULL,
                        intent_type TEXT,
                        confidence REAL,
                        rules_created TEXT DEFAULT '[]',
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        user_confirmed INTEGER DEFAULT 0,
                        user_feedback TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        executed_at TIMESTAMP,
                        extra_metadata TEXT DEFAULT '{}'
                    )
                """))
                print("   ✅ Table created")

                # Create indices
                conn.execute(text("""
                    CREATE INDEX idx_nlp_intents_intent_id
                    ON nlp_intents (intent_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_nlp_intents_account_id
                    ON nlp_intents (account_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_nlp_intents_intent_type
                    ON nlp_intents (intent_type)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_nlp_intents_status
                    ON nlp_intents (status)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_nlp_intents_created_at
                    ON nlp_intents (created_at)
                """))
                print("   ✅ Created indices")

            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ⚠️  Table already exists, skipping")
                else:
                    raise

            print()

            # ================================================================
            # STEP 5: Verify data integrity
            # ================================================================
            print("🔍 [5/6] Verifying migration...")

            # Count emails with new primary_category
            result = conn.execute(text("""
                SELECT COUNT(*) FROM processed_emails
                WHERE primary_category IS NOT NULL
            """))
            count = result.scalar()
            print(f"   ✅ {count} emails have primary_category set")

            # Count sender preferences
            result = conn.execute(text("""
                SELECT COUNT(*) FROM sender_preferences
            """))
            count = result.scalar()
            print(f"   ✅ {count} sender preferences with new fields")

            # Verify new tables exist
            result = conn.execute(text("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name IN ('user_preference_rules', 'nlp_intents')
            """))
            count = result.scalar()
            print(f"   ✅ {count}/2 new tables created")

            print()

            # ================================================================
            # STEP 6: Commit transaction
            # ================================================================
            print("💾 [6/6] Committing changes...")
            trans.commit()

            print()
            print("=" * 70)
            print("✅ Migration completed successfully!")
            print("=" * 70)
            print()
            print("📊 Summary:")
            print("  - ProcessedEmail: Added primary_category, secondary_categories, etc.")
            print("  - SenderPreference: Added trust_level, whitelist/blacklist, category prefs")
            print("  - Created user_preference_rules table")
            print("  - Created nlp_intents table")
            print(f"  - Migrated {count} emails to new category system")
            print()
            print("🔧 Next steps:")
            print("  1. Update classification code to use new primary/secondary categories")
            print("  2. Implement NLP intent parser")
            print("  3. Create GUI chat interface for preferences")
            print("  4. Test with real emails")
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
