"""
Integration Test: Complete Journal Generation Flow

Tests the full flow from extraction → memory-objects → journal generation.
"""

import pytest
from datetime import datetime

from agent_platform.classification import EmailToClassify
from agent_platform.extraction import ExtractionAgent
from agent_platform.journal import generate_daily_journal


@pytest.mark.asyncio
async def test_complete_journal_flow():
    """
    Test complete flow: Email → Extraction → Memory-Objects → Journal.

    This integration test validates:
    1. Email extraction creates memory-objects
    2. Journal generator aggregates memory-objects
    3. Journal contains correct statistics and content
    """
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Complete Journal Generation Flow")
    print("=" * 80)

    account_id = "journal_test_account"

    # Step 1: Create test email
    test_email = EmailToClassify(
        email_id="journal_test_email_1",
        account_id=account_id,
        sender="manager@company.com",
        subject="Weekly Tasks & Decisions",
        body="""
        Hi Team,

        Please complete the following by end of week:
        1. Review and approve the Q4 budget proposal
        2. Decide on the new office location (options: Downtown, Suburban Campus)
        3. Can you send me the updated customer satisfaction scores?

        Thanks,
        Manager
        """,
        received_at=datetime.utcnow(),
    )

    print(f"\n📧 Step 1: Test Email")
    print(f"  Subject: {test_email.subject}")
    print(f"  From: {test_email.sender}")

    # Step 2: Extract and persist
    extraction_agent = ExtractionAgent()

    print(f"\n🔍 Step 2: Extracting and persisting...")
    extraction_result = await extraction_agent.extract_and_persist(test_email)

    print(f"  ✓ Extracted:")
    print(f"    - {extraction_result.task_count} tasks")
    print(f"    - {extraction_result.decision_count} decisions")
    print(f"    - {extraction_result.question_count} questions")

    # Validate extraction created memory-objects
    # Note: LLM may classify items differently (question could be task or decision)
    total_items = (
        extraction_result.task_count
        + extraction_result.decision_count
        + extraction_result.question_count
    )
    assert total_items >= 2, f"Should extract at least 2 items total, got {total_items}"
    assert extraction_result.task_count >= 1, "Should extract at least 1 task"

    # Step 3: Generate journal
    print(f"\n📝 Step 3: Generating daily journal...")
    journal = await generate_daily_journal(account_id, datetime.utcnow())

    print(f"  ✓ Journal Generated:")
    print(f"    - Title: {journal.title}")
    print(f"    - Emails Processed: {journal.total_emails_processed}")
    print(f"    - Tasks Created: {journal.total_tasks_created}")

    # Validate journal contains our data
    assert journal.total_emails_processed >= 1, "Journal should count the test email"
    assert journal.total_tasks_created >= 1, "Journal should count extracted tasks"

    # Step 4: Verify journal content
    print(f"\n✓ Step 4: Validating journal content...")

    assert "Daily Email Journal" in journal.content_markdown
    assert account_id in journal.content_markdown
    assert str(journal.total_emails_processed) in journal.content_markdown

    if journal.top_senders:
        print(f"  ✓ Top senders: {journal.top_senders[0]['sender']}")
        assert test_email.sender in [s['sender'] for s in journal.top_senders]

    print(f"\n📄 Journal Preview:")
    print("=" * 80)
    print(journal.content_markdown[:500] + "...")
    print("=" * 80)

    print(f"\n✅ INTEGRATION TEST PASSED")
    print("=" * 80 + "\n")


@pytest.mark.asyncio
async def test_journal_idempotency():
    """
    Test that generating journal twice for same date returns same journal.
    """
    account_id = "idempotency_test"
    test_date = datetime(2025, 11, 23, 10, 0)

    # Generate once
    journal1 = await generate_daily_journal(account_id, test_date)

    # Generate again for same date
    journal2 = await generate_daily_journal(account_id, test_date)

    # Should be the same journal (idempotent)
    assert journal1.journal_id == journal2.journal_id
    assert journal1.title == journal2.title


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
