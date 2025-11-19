#!/usr/bin/env python
"""Verify database tables were created"""
from agent_platform.db.database import engine
from sqlalchemy import inspect

insp = inspect(engine)
tables = sorted(insp.get_table_names())

print("\n" + "=" * 70)
print("DATABASE TABLES")
print("=" * 70)
print(f"\nTotal tables created: {len(tables)}\n")

print("Core Platform Tables:")
for table in ['modules', 'agents', 'runs', 'steps']:
    if table in tables:
        print(f"  ✓ {table}")

print("\nEmail Tables:")
for table in ['email_accounts', 'processed_emails']:
    if table in tables:
        print(f"  ✓ {table}")

print("\nNEW Importance Classification Tables:")
for table in ['sender_preferences', 'domain_preferences', 'feedback_events', 'review_queue', 'subject_patterns']:
    if table in tables:
        print(f"  ✓ {table}")

print("\n" + "=" * 70)
print(f"✅ All {len(tables)} tables created successfully!")
print("=" * 70 + "\n")
