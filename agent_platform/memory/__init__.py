"""
Memory Service Layer

Provides CRUD operations for Memory-Objects (Tasks, Decisions, Questions, Journal Entries).
Memory-Objects are derived from extraction events following Event-First principles.

Usage:
    from agent_platform.memory import (
        MemoryService,
        create_task, get_pending_tasks, update_task_status,
        create_decision, get_pending_decisions,
        create_question, get_pending_questions,
        create_journal_entry, get_journal_for_date
    )

    # Create task from extraction
    task = create_task(
        account_id="gmail_1",
        email_id="msg_123",
        description="Review Q4 report",
        deadline=datetime(2025, 11, 25),
        priority="high"
    )

    # Get pending tasks
    tasks = get_pending_tasks("gmail_1")

    # Update task status
    update_task_status(task.task_id, "completed")
"""

from agent_platform.memory.service import (
    MemoryService,
    # Task operations
    create_task,
    get_task,
    get_pending_tasks,
    get_tasks_by_email,
    update_task_status,
    complete_task,
    # Decision operations
    create_decision,
    get_decision,
    get_pending_decisions,
    get_decisions_by_email,
    make_decision,
    # Question operations
    create_question,
    get_question,
    get_pending_questions,
    get_questions_by_email,
    answer_question,
    # Journal operations
    create_journal_entry,
    get_journal_entry,
    get_journal_for_date,
    get_recent_journals,
    mark_journal_reviewed,
)

__all__ = [
    'MemoryService',
    # Task operations
    'create_task',
    'get_task',
    'get_pending_tasks',
    'get_tasks_by_email',
    'update_task_status',
    'complete_task',
    # Decision operations
    'create_decision',
    'get_decision',
    'get_pending_decisions',
    'get_decisions_by_email',
    'make_decision',
    # Question operations
    'create_question',
    'get_question',
    'get_pending_questions',
    'get_questions_by_email',
    'answer_question',
    # Journal operations
    'create_journal_entry',
    'get_journal_entry',
    'get_journal_for_date',
    'get_recent_journals',
    'mark_journal_reviewed',
]
