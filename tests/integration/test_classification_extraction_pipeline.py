"""
Integration Test: Classification + Extraction Pipeline

Tests the complete email processing workflow:
1. Classification (Importance scoring)
2. Extraction (Tasks, Decisions, Questions)
"""

import asyncio
from datetime import datetime

from agent_platform.orchestration import ClassificationOrchestrator


async def test_complete_pipeline():
    """Test complete Classification + Extraction pipeline"""
    print("=" * 80)
    print("INTEGRATION TEST: Classification + Extraction Pipeline")
    print("=" * 80)
    print()

    # Create test emails
    test_emails = [
        {
            'id': 'test_pipeline_001',
            'subject': 'Project Update - Action Items Required',
            'sender': 'boss@company.com',
            'body': '''Hi Team,

Great progress on Phase 1! Here's what we need to do next:

1. Please review the Q4 report by Friday
2. Update the project timeline spreadsheet
3. Send me the vendor quotes when ready

We also need to decide: Should we extend the deadline by 2 weeks or keep it as-is?

Question: What's the current budget status?

Thanks!
Boss''',
            'received_at': datetime.utcnow(),
        },
        {
            'id': 'test_pipeline_002',
            'subject': 'Weekly Newsletter - January 2025',
            'sender': 'newsletter@tech.com',
            'body': '''Hi Subscriber,

Welcome to our weekly tech newsletter!

This week's highlights:
- AI breakthrough announced
- Cloud trends for 2025
- CEO interview

Enjoy reading!''',
            'received_at': datetime.utcnow(),
        },
        {
            'id': 'test_pipeline_003',
            'subject': 'Quick Question',
            'sender': 'colleague@company.com',
            'body': '''Hey,

When can we schedule the meeting to discuss the budget?

Also, do you have the latest numbers?

Thanks!''',
            'received_at': datetime.utcnow(),
        },
    ]

    # Initialize orchestrator
    orchestrator = ClassificationOrchestrator()

    # Process emails
    stats = await orchestrator.process_emails(
        emails=test_emails,
        account_id='gmail_test'
    )

    # Verify results
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    assert stats.total_processed == 3, f"Expected 3 emails processed, got {stats.total_processed}"
    print(f"✅ Processed {stats.total_processed} emails")

    assert stats.emails_with_extractions >= 2, f"Expected at least 2 emails with extractions, got {stats.emails_with_extractions}"
    print(f"✅ Found extractions in {stats.emails_with_extractions} emails")

    assert stats.total_tasks_extracted >= 3, f"Expected at least 3 tasks, got {stats.total_tasks_extracted}"
    print(f"✅ Extracted {stats.total_tasks_extracted} tasks")

    assert stats.total_decisions_extracted >= 1, f"Expected at least 1 decision, got {stats.total_decisions_extracted}"
    print(f"✅ Extracted {stats.total_decisions_extracted} decisions")

    assert stats.total_questions_extracted >= 2, f"Expected at least 2 questions, got {stats.total_questions_extracted}"
    print(f"✅ Extracted {stats.total_questions_extracted} questions")

    total_items = stats.total_tasks_extracted + stats.total_decisions_extracted + stats.total_questions_extracted
    print(f"✅ Total items extracted: {total_items}")

    print()
    print("=" * 80)
    print("✅ INTEGRATION TEST PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())
