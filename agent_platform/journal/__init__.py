"""
Journal Generator Module

Generates daily summary journals from events and memory-objects.
Provides human-readable overview of the day's email activities.

Usage:
    from agent_platform.journal import JournalGenerator, generate_daily_journal

    # Generate journal for today
    journal = await generate_daily_journal("gmail_1")

    # Print journal
    print(journal.title)
    print(journal.content_markdown)

    # Get journal statistics
    print(f"Emails processed: {journal.total_emails_processed}")
    print(f"Tasks created: {journal.total_tasks_created}")
"""

from agent_platform.journal.generator import JournalGenerator, generate_daily_journal

__all__ = [
    "JournalGenerator",
    "generate_daily_journal",
]
