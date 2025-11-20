"""
Test: Journal Generator

Tests the journal generation from events and memory-objects.
"""

import asyncio
from datetime import datetime

from agent_platform.journal import generate_daily_journal


async def main():
    """Test journal generator."""
    print("\n" + "=" * 80)
    print("JOURNAL GENERATOR TEST")
    print("=" * 80)

    # Generate journal for test account (should use data from previous integration test)
    print("\n📝 Generating daily journal for test_account...")

    journal = await generate_daily_journal("test_account", datetime.utcnow())

    print(f"\n📄 Journal Generated:")
    print(f"  Title: {journal.title}")
    print(f"  Date: {journal.date}")
    print(f"  Status: {journal.status}")

    print(f"\n📊 Statistics:")
    print(f"  Emails Processed: {journal.total_emails_processed}")
    print(f"  Tasks Created: {journal.total_tasks_created}")
    print(f"  Decisions Made: {journal.total_decisions_made}")
    print(f"  Questions Answered: {journal.total_questions_answered}")

    if journal.emails_by_category:
        print(f"\n  Email Breakdown:")
        for category, count in journal.emails_by_category.items():
            print(f"    - {category}: {count}")

    if journal.top_senders:
        print(f"\n👥 Top Senders:")
        for sender_info in journal.top_senders[:3]:
            print(f"  - {sender_info['sender']}: {sender_info['count']} email(s)")

    if journal.important_items:
        print(f"\n⚠️ Important Items: {len(journal.important_items)}")

    print(f"\n📝 Journal Content (Markdown):")
    print("=" * 80)
    print(journal.content_markdown)
    print("=" * 80)

    print(f"\n💡 Summary: {journal.summary}")

    print("\n" + "=" * 80)
    print("✅ JOURNAL GENERATOR TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
