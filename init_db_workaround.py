#!/usr/bin/env python
"""
Database Initialization Workaround Script

This script works around the naming conflict between the project's 'platform'
directory and Python's standard library 'platform' module.
"""

import sys
import os

# CRITICAL: Import stdlib platform BEFORE adding project to path
import platform as stdlib_platform
sys.modules['_stdlib_platform'] = stdlib_platform

# Now add project to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Monkey-patch: Ensure platform module references resolve correctly
original_platform = sys.modules.get('platform')

def safe_import():
    """Safely import project modules while preserving stdlib platform"""
    # Temporarily restore stdlib platform
    sys.modules['platform'] = stdlib_platform

    try:
        # Import SQLAlchemy first (it needs stdlib platform)
        import sqlalchemy

        # Now we can import our project's platform package
        import platform as project_platform
        sys.modules['platform'] = project_platform

        # Import database module
        from agent_platform.db.database import init_db
        return init_db
    except Exception as e:
        # Restore original state on error
        if original_platform:
            sys.modules['platform'] = original_platform
        raise e

if __name__ == "__main__":
    print("=" * 70)
    print("DATABASE INITIALIZATION (Workaround for naming conflict)")
    print("=" * 70)
    print("\nInitializing database with all tables...")
    print("This includes:")
    print("  - Core platform tables (modules, agents, runs, steps)")
    print("  - Email tables (accounts, processed_emails)")
    print("  - NEW: Importance classification tables:")
    print("    • sender_preferences")
    print("    • domain_preferences")
    print("    • feedback_events")
    print("    • review_queue")
    print("    • subject_patterns")
    print()

    try:
        init_db = safe_import()
        init_db()

        print("\n" + "=" * 70)
        print("✅ SUCCESS: Database initialized")
        print("=" * 70)
        print("\nAll tables created successfully!")
        print("You can now run the test suite.\n")
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR: Database initialization failed")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print()
        sys.exit(1)
