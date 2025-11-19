#!/usr/bin/env python
"""
Database Initialization Script
Creates all tables for the agent platform including the new importance classification tables.
"""

import sys
import os

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from agent_platform.db.database import init_db

    print("=" * 70)
    print("DATABASE INITIALIZATION")
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

    try:
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
        print(f"\nError: {e}\n")
        sys.exit(1)
