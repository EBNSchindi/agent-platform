"""
Quick Test: Memory-Objects Integration

Tests the complete flow from extraction to memory-object persistence.
"""

import asyncio
from datetime import datetime

from agent_platform.classification import EmailToClassify
from agent_platform.extraction import ExtractionAgent
from agent_platform.memory import get_pending_tasks, get_pending_decisions, get_pending_questions


async def main():
    """Test memory-objects integration."""
    print("\n" + "=" * 80)
    print("MEMORY-OBJECTS INTEGRATION TEST")
    print("=" * 80)

    # Create test email with tasks, decisions, and questions
    test_email = EmailToClassify(
        email_id="test_memory_123",
        account_id="test_account",
        sender="boss@company.com",
        subject="Q4 Planning Meeting - Action Required",
        body="""
        Hi Team,

        We need to finalize our Q4 strategy. Here's what we need to discuss:

        1. Review the Q4 budget proposal by Friday and send me your feedback
        2. Decide whether we should hire 2 new developers or 1 senior + 1 junior
        3. Can you provide the customer retention metrics from last quarter?

        Please prepare your thoughts before the meeting on Monday at 10 AM.

        Best,
        Sarah
        """,
        received_at=datetime(2025, 11, 20, 9, 0),
    )

    # Extract and persist
    print("\n📧 Test Email:")
    print(f"  From: {test_email.sender}")
    print(f"  Subject: {test_email.subject}")

    extraction_agent = ExtractionAgent()

    print("\n🤖 Extracting and persisting to database...")
    result = await extraction_agent.extract_and_persist(test_email)

    print(f"\n📊 Extraction Results:")
    print(f"  Summary: {result.summary}")
    print(f"  Tasks: {result.task_count}")
    print(f"  Decisions: {result.decision_count}")
    print(f"  Questions: {result.question_count}")

    # Verify persistence by querying memory-objects
    print("\n💾 Querying Memory-Objects from Database:")

    tasks = get_pending_tasks("test_account")
    print(f"\n  Pending Tasks ({len(tasks)}):")
    for task in tasks:
        print(f"    - {task.description[:60]}...")
        print(f"      Priority: {task.priority}, Deadline: {task.deadline}")

    decisions = get_pending_decisions("test_account")
    print(f"\n  Pending Decisions ({len(decisions)}):")
    for decision in decisions:
        print(f"    - {decision.question[:60]}...")
        print(f"      Options: {', '.join(decision.options[:2])}...")
        print(f"      Urgency: {decision.urgency}")

    questions = get_pending_questions("test_account")
    print(f"\n  Pending Questions ({len(questions)}):")
    for question in questions:
        print(f"    - {question.question[:60]}...")
        print(f"      Type: {question.question_type}, Urgency: {question.urgency}")

    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
