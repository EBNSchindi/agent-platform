"""
Simple migration runner for Event-Log System

Usage:
    python migrations/run_migration.py
"""

import sqlite3
import os

# Get database path from environment or use default
DB_PATH = os.getenv('DATABASE_PATH', 'platform.db')

def run_migration(sql_file: str):
    """Run a SQL migration file"""
    print(f"Running migration: {sql_file}")

    # Read SQL file
    with open(sql_file, 'r') as f:
        sql = f.read()

    # Execute migration
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()
        print(f"✅ Migration completed: {sql_file}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Run Event table migration
    migration_dir = os.path.dirname(__file__)
    migration_file = os.path.join(migration_dir, "001_create_events_table.sql")

    print("=" * 80)
    print("Event-Log System Migration")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print()

    run_migration(migration_file)

    print()
    print("=" * 80)
    print("✅ All migrations completed successfully!")
    print("=" * 80)
