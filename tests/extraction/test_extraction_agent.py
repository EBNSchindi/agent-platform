"""
Tests for Extraction Agent

Tests the email extraction functionality including tasks, decisions,
questions, and summary generation.
"""

import asyncio
from datetime import datetime

from agent_platform.extraction import ExtractionAgent, EmailExtraction
from agent_platform.classification.models import EmailToClassify
from agent_platform.events import get_events, EventType


class TestExtractionAgent:
    """Test Extraction Agent functionality"""

    async def test_extract_with_tasks(self):
        """Test extraction of tasks from email"""
        email = EmailToClassify(
            email_id="test_extract_tasks_001",
            subject="Project Update - Action Items",
            sender="john@company.com",
            body="""Hi there,

Can you please review the attached document by Friday? We also need to schedule a meeting next week to discuss the budget.

Thanks!
John""",
            account_id="gmail_test",
            received_at=datetime.utcnow(),
            has_attachments=True,
            is_reply=False,
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Verify basic extraction
        assert isinstance(result, EmailExtraction)
        assert result.summary is not None
        assert len(result.summary) > 10
        assert result.main_topic is not None
        assert result.sentiment in ["positive", "neutral", "negative", "urgent"]

        # Verify tasks extracted
        assert result.task_count >= 1, "Should extract at least 1 task (review document)"

        # Check for specific task
        review_task = next((t for t in result.tasks if "review" in t.description.lower()), None)
        assert review_task is not None, "Should extract 'review document' task"
        assert review_task.requires_action_from_me == True
        assert review_task.priority in ["low", "medium", "high"]

        print(f"✅ Extracted {result.task_count} task(s)")
        for task in result.tasks:
            print(f"   - {task.description} (priority: {task.priority})")

    async def test_extract_with_decisions(self):
        """Test extraction of decisions from email"""
        email = EmailToClassify(
            email_id="test_extract_decisions_001",
            subject="Choice between Option A and B",
            sender="sarah@company.com",
            body="""Hi,

We need to decide whether to go with Option A (faster implementation, higher cost) or Option B (slower but cheaper).

I would recommend Option A given our tight timeline. What do you think?

Best,
Sarah""",
            account_id="gmail_test",
            received_at=datetime.utcnow(),
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Verify decisions extracted
        assert result.decision_count >= 1, "Should extract at least 1 decision"

        decision = result.decisions[0]
        assert decision.requires_my_input == True
        assert len(decision.options) >= 2 or "option" in decision.question.lower()
        assert decision.urgency in ["low", "medium", "high"]

        print(f"✅ Extracted {result.decision_count} decision(s)")
        for dec in result.decisions:
            print(f"   - {dec.question}")
            if dec.recommendation:
                print(f"     Recommendation: {dec.recommendation}")

    async def test_extract_with_questions(self):
        """Test extraction of questions from email"""
        email = EmailToClassify(
            email_id="test_extract_questions_001",
            subject="Quick Questions",
            sender="mike@company.com",
            body="""Hey,

I have a few questions:
1. When can we schedule the meeting?
2. What's your opinion on the new proposal?
3. Do you have the latest budget numbers?

Thanks!
Mike""",
            account_id="gmail_test",
            received_at=datetime.utcnow(),
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Verify questions extracted
        assert result.question_count >= 2, "Should extract at least 2 questions"

        # Check question types
        for question in result.questions:
            assert question.question_type in ["factual", "opinion", "scheduling", "confirmation", "other"]
            assert question.requires_response in [True, False]
            assert question.urgency in ["low", "medium", "high"]

        print(f"✅ Extracted {result.question_count} question(s)")
        for q in result.questions:
            print(f"   - {q.question} (type: {q.question_type})")

    async def test_extract_newsletter(self):
        """Test extraction from newsletter (should have minimal action items)"""
        email = EmailToClassify(
            email_id="test_extract_newsletter_001",
            subject="Weekly Tech Newsletter - January 2025",
            sender="newsletter@techblog.com",
            body="""Hi Subscriber,

Welcome to our weekly newsletter!

This week's highlights:
- New AI breakthrough announced
- Cloud computing trends for 2025
- Interview with tech CEO

Enjoy reading!

Team TechBlog""",
            account_id="gmail_test",
            received_at=datetime.utcnow(),
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Newsletters typically have few/no action items
        assert result.has_action_items == False or result.total_items <= 1
        assert result.summary is not None
        assert "newsletter" in result.summary.lower() or "highlight" in result.summary.lower() or "tech" in result.summary.lower()

        print(f"✅ Newsletter extraction:")
        print(f"   Summary: {result.summary}")
        print(f"   Has action items: {result.has_action_items}")
        print(f"   Total items: {result.total_items}")

    async def test_extract_complex_email(self):
        """Test extraction from complex email with multiple items"""
        email = EmailToClassify(
            email_id="test_extract_complex_001",
            subject="Project Status & Next Steps",
            sender="boss@company.com",
            body="""Hi Team,

Great work on Phase 1! Here's where we stand and what's next:

ACTION ITEMS:
1. Please review the Q4 report by EOD Thursday
2. Update the project timeline spreadsheet
3. Send me the vendor quotes when you have them

DECISIONS NEEDED:
- Should we extend the deadline by 2 weeks or keep it as-is?
- Do we need additional resources for Phase 2?

QUESTIONS:
- What's the current budget status?
- When can we schedule the stakeholder presentation?

Let's discuss this in our meeting tomorrow.

Thanks,
Boss""",
            account_id="gmail_test",
            received_at=datetime.utcnow(),
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Should extract multiple items
        assert result.total_items >= 5, f"Should extract at least 5 items, got {result.total_items}"
        assert result.task_count >= 2, "Should extract at least 2 tasks"
        assert result.decision_count >= 1, "Should extract at least 1 decision"
        assert result.question_count >= 1, "Should extract at least 1 question"
        assert result.has_action_items == True

        print(f"✅ Complex email extraction:")
        print(f"   Summary: {result.summary}")
        print(f"   Tasks: {result.task_count}")
        print(f"   Decisions: {result.decision_count}")
        print(f"   Questions: {result.question_count}")
        print(f"   Total items: {result.total_items}")

    async def test_event_logging(self):
        """Test that extraction events are properly logged"""
        from datetime import datetime, timedelta

        # Record start time for filtering events
        test_start_time = datetime.utcnow()

        email = EmailToClassify(
            email_id="test_event_logging_001",
            subject="Test Email for Event Logging",
            sender="test@example.com",
            body="Can you send me the report by tomorrow? Also, what's your opinion on the new design?",
            account_id="gmail_test",
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        # Wait a moment for events to be logged
        await asyncio.sleep(0.1)

        # Check EMAIL_ANALYZED event (filter by start_time to only get events from THIS test run)
        analyzed_events = get_events(
            event_type=EventType.EMAIL_ANALYZED,
            email_id="test_event_logging_001",
            start_time=test_start_time,
            limit=10
        )
        assert len(analyzed_events) >= 1, "Should log EMAIL_ANALYZED event"

        event = analyzed_events[0]
        assert event.payload['summary'] == result.summary
        assert event.payload['task_count'] == result.task_count
        assert event.payload['decision_count'] == result.decision_count
        assert event.payload['question_count'] == result.question_count

        # Check TASK_EXTRACTED events (filter by start_time)
        task_events = get_events(
            event_type=EventType.TASK_EXTRACTED,
            email_id="test_event_logging_001",
            start_time=test_start_time,
            limit=10
        )
        assert len(task_events) == result.task_count, f"Should log one event per task (expected {result.task_count}, got {len(task_events)})"

        # Check QUESTION_EXTRACTED events (filter by start_time)
        question_events = get_events(
            event_type=EventType.QUESTION_EXTRACTED,
            email_id="test_event_logging_001",
            start_time=test_start_time,
            limit=10
        )
        assert len(question_events) == result.question_count, f"Should log one event per question (expected {result.question_count}, got {len(question_events)})"

        print(f"✅ Event logging verified:")
        print(f"   EMAIL_ANALYZED events: {len(analyzed_events)}")
        print(f"   TASK_EXTRACTED events: {len(task_events)}")
        print(f"   QUESTION_EXTRACTED events: {len(question_events)}")

    async def test_to_summary_dict(self):
        """Test EmailExtraction.to_summary_dict() method"""
        email = EmailToClassify(
            email_id="test_summary_dict_001",
            subject="Test Email",
            sender="test@example.com",
            body="Please review the document and let me know your thoughts.",
            account_id="gmail_test",
        )

        agent = ExtractionAgent()
        result = await agent.extract(email)

        summary_dict = result.to_summary_dict()

        assert 'summary' in summary_dict
        assert 'main_topic' in summary_dict
        assert 'sentiment' in summary_dict
        assert 'has_action_items' in summary_dict
        assert 'counts' in summary_dict
        assert summary_dict['counts']['tasks'] == result.task_count
        assert summary_dict['counts']['decisions'] == result.decision_count
        assert summary_dict['counts']['questions'] == result.question_count
        assert summary_dict['counts']['total'] == result.total_items

        print(f"✅ Summary dict: {summary_dict}")


async def main():
    """Run all extraction tests"""
    print("=" * 80)
    print("EXTRACTION AGENT TESTS")
    print("=" * 80)
    print()

    test = TestExtractionAgent()

    tests = [
        ("Extract with Tasks", test.test_extract_with_tasks),
        ("Extract with Decisions", test.test_extract_with_decisions),
        ("Extract with Questions", test.test_extract_with_questions),
        ("Extract Newsletter", test.test_extract_newsletter),
        ("Extract Complex Email", test.test_extract_complex_email),
        ("Event Logging", test.test_event_logging),
        ("To Summary Dict", test.test_to_summary_dict),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"Running: {name}...")
            await test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            print()
            failed += 1

    print("=" * 80)
    print(f"Results: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {failed} tests failed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
