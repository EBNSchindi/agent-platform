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
    import sys
    import glob

    migration_dir = os.path.dirname(__file__) or '.'

    print("=" * 80)
    print("Database Migration Runner")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print()

    # If specific migration file provided, run only that one
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
        if not os.path.isabs(migration_file):
            migration_file = os.path.join(migration_dir, migration_file)

        if not os.path.exists(migration_file):
            print(f"❌ Migration file not found: {migration_file}")
            sys.exit(1)

        run_migration(migration_file)
    else:
        # Run all migrations in order
        migration_files = sorted(glob.glob(os.path.join(migration_dir, "*.sql")))

        if not migration_files:
            print("⚠️  No migration files found")
            sys.exit(0)

        for migration_file in migration_files:
            run_migration(migration_file)
            print()

    print("=" * 80)
    print("✅ All migrations completed successfully!")
    print("=" * 80)
