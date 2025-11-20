"""
Unit Tests: Memory Service

Tests CRUD operations for Tasks, Decisions, Questions, and Journal Entries.
"""

import pytest
from datetime import datetime, timedelta

from agent_platform.memory import (
    create_task,
    get_task,
    get_pending_tasks,
    update_task_status,
    complete_task,
    create_decision,
    get_decision,
    get_pending_decisions,
    make_decision,
    create_question,
    get_question,
    get_pending_questions,
    answer_question,
    create_journal_entry,
    get_journal_for_date,
)


class TestTaskOperations:
    """Test Task CRUD operations."""

    def test_create_task(self):
        """Test creating a task."""
        task = create_task(
            account_id="test_account",
            email_id="test_email_1",
            description="Test task",
            priority="high",
            deadline=datetime(2025, 12, 1),
        )

        assert task is not None
        assert task.description == "Test task"
        assert task.priority == "high"
        assert task.status == "pending"
        assert task.task_id is not None

    def test_get_task(self):
        """Test retrieving a task by ID."""
        task = create_task(
            account_id="test_account",
            email_id="test_email_2",
            description="Another task",
        )

        retrieved = get_task(task.task_id)

        assert retrieved is not None
        assert retrieved.task_id == task.task_id
        assert retrieved.description == "Another task"

    def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        # Create test tasks
        create_task(
            account_id="test_account",
            email_id="test_email_3",
            description="Pending task 1",
            priority="high",
        )

        create_task(
            account_id="test_account",
            email_id="test_email_4",
            description="Pending task 2",
            priority="low",
        )

        pending = get_pending_tasks("test_account")

        assert len(pending) >= 2
        assert all(t.status == "pending" for t in pending)

    def test_update_task_status(self):
        """Test updating task status."""
        task = create_task(
            account_id="test_account",
            email_id="test_email_5",
            description="Task to update",
        )

        updated = update_task_status(task.task_id, "in_progress")

        assert updated is not None
        assert updated.status == "in_progress"

    def test_complete_task(self):
        """Test completing a task."""
        task = create_task(
            account_id="test_account",
            email_id="test_email_6",
            description="Task to complete",
        )

        completed = complete_task(task.task_id, "Done!")

        assert completed is not None
        assert completed.status == "completed"
        assert completed.completion_notes == "Done!"
        assert completed.completed_at is not None


class TestDecisionOperations:
    """Test Decision CRUD operations."""

    def test_create_decision(self):
        """Test creating a decision."""
        decision = create_decision(
            account_id="test_account",
            email_id="test_email_7",
            question="Should we approve the budget?",
            options=["Yes", "No", "Need more info"],
            urgency="high",
        )

        assert decision is not None
        assert decision.question == "Should we approve the budget?"
        assert len(decision.options) == 3
        assert decision.urgency == "high"
        assert decision.status == "pending"

    def test_get_decision(self):
        """Test retrieving a decision by ID."""
        decision = create_decision(
            account_id="test_account",
            email_id="test_email_8",
            question="Another decision?",
            options=["A", "B"],
        )

        retrieved = get_decision(decision.decision_id)

        assert retrieved is not None
        assert retrieved.decision_id == decision.decision_id

    def test_make_decision(self):
        """Test recording a decision."""
        decision = create_decision(
            account_id="test_account",
            email_id="test_email_9",
            question="Which option?",
            options=["Option 1", "Option 2"],
        )

        decided = make_decision(decision.decision_id, "Option 1", "Seems best")

        assert decided is not None
        assert decided.status == "decided"
        assert decided.chosen_option == "Option 1"
        assert decided.decision_notes == "Seems best"
        assert decided.decided_at is not None


class TestQuestionOperations:
    """Test Question CRUD operations."""

    def test_create_question(self):
        """Test creating a question."""
        question = create_question(
            account_id="test_account",
            email_id="test_email_10",
            question="What is the deadline?",
            question_type="information",
            urgency="medium",
        )

        assert question is not None
        assert question.question == "What is the deadline?"
        assert question.question_type == "information"
        assert question.status == "pending"

    def test_answer_question(self):
        """Test answering a question."""
        question = create_question(
            account_id="test_account",
            email_id="test_email_11",
            question="When is the meeting?",
        )

        answered = answer_question(question.question_id, "Friday at 2 PM")

        assert answered is not None
        assert answered.status == "answered"
        assert answered.answer == "Friday at 2 PM"
        assert answered.answered_at is not None


class TestJournalOperations:
    """Test Journal CRUD operations."""

    def test_create_journal_entry(self):
        """Test creating a journal entry."""
        journal = create_journal_entry(
            account_id="test_account",
            date=datetime(2025, 11, 20),
            title="Test Journal",
            content_markdown="# Test Journal\n\nSome content",
            summary="Test summary",
            total_emails_processed=10,
            total_tasks_created=3,
        )

        assert journal is not None
        assert journal.title == "Test Journal"
        assert journal.total_emails_processed == 10
        assert journal.status == "generated"

    def test_get_journal_for_date(self):
        """Test retrieving journal for a specific date."""
        date = datetime(2025, 11, 21, 10, 0)  # With time

        journal = create_journal_entry(
            account_id="test_account",
            date=date,
            title="Daily Journal",
            content_markdown="# Content",
        )

        # Retrieve using same date
        retrieved = get_journal_for_date("test_account", date)

        assert retrieved is not None
        assert retrieved.journal_id == journal.journal_id

    def test_journal_not_duplicate(self):
        """Test that journal creation checks for existing journal."""
        from agent_platform.journal import generate_daily_journal
        import asyncio

        async def run_test():
            # First journal
            journal1 = await generate_daily_journal("test_dup_account", datetime(2025, 11, 22))

            # Second attempt for same date should return existing
            journal2 = await generate_daily_journal("test_dup_account", datetime(2025, 11, 22))

            assert journal1.journal_id == journal2.journal_id

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
