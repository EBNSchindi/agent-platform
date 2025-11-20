"""
Memory Service Implementation

Provides CRUD operations for Memory-Objects following Event-First principles.
All memory objects are derived from extraction events.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from agent_platform.db.database import get_db
from agent_platform.db.models import Task, Decision, Question, JournalEntry, ProcessedEmail
from agent_platform.events import log_event, EventType


class MemoryService:
    """
    Service for managing Memory-Objects.

    Provides CRUD operations for Tasks, Decisions, Questions, and Journal Entries.
    All operations follow Event-First principles.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize memory service.

        Args:
            db: Optional database session
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # TASK OPERATIONS
    # ========================================================================

    def create_task(
        self,
        account_id: str,
        email_id: str,
        description: str,
        priority: str = "medium",
        deadline: Optional[datetime] = None,
        context: Optional[str] = None,
        assignee: Optional[str] = None,
        requires_action_from_me: bool = True,
        email_subject: Optional[str] = None,
        email_sender: Optional[str] = None,
        email_received_at: Optional[datetime] = None,
        processed_email_id: Optional[int] = None,
        extraction_event_id: Optional[str] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            account_id: Account ID (e.g., gmail_1)
            email_id: Email message ID
            description: What needs to be done
            priority: Task priority (low, medium, high, urgent)
            deadline: When task needs to be completed
            context: Additional context
            assignee: Who should do it
            requires_action_from_me: Does user need to act?
            email_subject: Email subject for context
            email_sender: Email sender for context
            email_received_at: When email was received
            processed_email_id: Optional FK to ProcessedEmail
            extraction_event_id: Optional FK to extraction event

        Returns:
            Created Task object
        """
        task = Task(
            account_id=account_id,
            email_id=email_id,
            description=description,
            priority=priority,
            deadline=deadline,
            context=context,
            assignee=assignee,
            requires_action_from_me=requires_action_from_me,
            email_subject=email_subject,
            email_sender=email_sender,
            email_received_at=email_received_at,
            processed_email_id=processed_email_id,
            extraction_event_id=extraction_event_id,
            status="pending",
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # Log event (Event-First)
        log_event(
            event_type=EventType.TASK_CREATED,
            account_id=account_id,
            email_id=email_id,
            payload={
                'task_id': task.task_id,
                'description': description,
                'priority': priority,
                'deadline': deadline.isoformat() if deadline else None,
                'requires_action_from_me': requires_action_from_me,
            }
        )

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def get_pending_tasks(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Task]:
        """
        Get pending tasks.

        Args:
            account_id: Optional account filter
            limit: Maximum number of tasks

        Returns:
            List of pending tasks, ordered by deadline
        """
        query = self.db.query(Task).filter(Task.status == "pending")

        if account_id:
            query = query.filter(Task.account_id == account_id)

        # Order by deadline (nulls last), then by created_at
        query = query.order_by(
            Task.deadline.asc().nullslast(),
            Task.created_at.asc()
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_tasks_by_email(self, email_id: str) -> List[Task]:
        """Get all tasks extracted from a specific email."""
        return self.db.query(Task).filter(Task.email_id == email_id).all()

    def update_task_status(
        self,
        task_id: str,
        new_status: str,
        completion_notes: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Update task status.

        Args:
            task_id: Task ID
            new_status: New status (pending, in_progress, completed, cancelled, waiting)
            completion_notes: Optional notes

        Returns:
            Updated Task or None if not found
        """
        task = self.get_task(task_id)

        if not task:
            return None

        old_status = task.status
        task.status = new_status

        if new_status == "completed" and not task.completed_at:
            task.completed_at = datetime.utcnow()

        if completion_notes:
            task.completion_notes = completion_notes

        self.db.commit()

        # Log event (Event-First)
        log_event(
            event_type=EventType.TASK_STATUS_CHANGED,
            account_id=task.account_id,
            email_id=task.email_id,
            payload={
                'task_id': task_id,
                'old_status': old_status,
                'new_status': new_status,
                'completion_notes': completion_notes,
            }
        )

        return task

    def complete_task(
        self,
        task_id: str,
        completion_notes: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            completion_notes: Optional notes

        Returns:
            Updated Task or None if not found
        """
        return self.update_task_status(task_id, "completed", completion_notes)

    # ========================================================================
    # DECISION OPERATIONS
    # ========================================================================

    def create_decision(
        self,
        account_id: str,
        email_id: str,
        question: str,
        options: List[str],
        urgency: str = "medium",
        context: Optional[str] = None,
        recommendation: Optional[str] = None,
        requires_my_input: bool = True,
        email_subject: Optional[str] = None,
        email_sender: Optional[str] = None,
        email_received_at: Optional[datetime] = None,
        processed_email_id: Optional[int] = None,
        extraction_event_id: Optional[str] = None,
    ) -> Decision:
        """
        Create a new decision.

        Args:
            account_id: Account ID
            email_id: Email message ID
            question: The decision to be made
            options: Available options
            urgency: Decision urgency (low, medium, high, urgent)
            context: Additional context
            recommendation: System/sender recommendation
            requires_my_input: Does user need to decide?
            email_subject: Email subject for context
            email_sender: Email sender for context
            email_received_at: When email was received
            processed_email_id: Optional FK to ProcessedEmail
            extraction_event_id: Optional FK to extraction event

        Returns:
            Created Decision object
        """
        decision = Decision(
            account_id=account_id,
            email_id=email_id,
            question=question,
            options=options,
            urgency=urgency,
            context=context,
            recommendation=recommendation,
            requires_my_input=requires_my_input,
            email_subject=email_subject,
            email_sender=email_sender,
            email_received_at=email_received_at,
            processed_email_id=processed_email_id,
            extraction_event_id=extraction_event_id,
            status="pending",
        )

        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)

        # Log event (Event-First)
        log_event(
            event_type=EventType.DECISION_CREATED,
            account_id=account_id,
            email_id=email_id,
            payload={
                'decision_id': decision.decision_id,
                'question': question,
                'options': options,
                'urgency': urgency,
            }
        )

        return decision

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self.db.query(Decision).filter(Decision.decision_id == decision_id).first()

    def get_pending_decisions(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Decision]:
        """
        Get pending decisions.

        Args:
            account_id: Optional account filter
            limit: Maximum number of decisions

        Returns:
            List of pending decisions, ordered by urgency
        """
        query = self.db.query(Decision).filter(Decision.status == "pending")

        if account_id:
            query = query.filter(Decision.account_id == account_id)

        # Order by urgency (high priority first) and creation time
        urgency_order = {
            'urgent': 0,
            'high': 1,
            'medium': 2,
            'low': 3,
        }

        decisions = query.all()
        decisions.sort(key=lambda d: (urgency_order.get(d.urgency, 2), d.created_at))

        if limit:
            decisions = decisions[:limit]

        return decisions

    def get_decisions_by_email(self, email_id: str) -> List[Decision]:
        """Get all decisions extracted from a specific email."""
        return self.db.query(Decision).filter(Decision.email_id == email_id).all()

    def make_decision(
        self,
        decision_id: str,
        chosen_option: str,
        decision_notes: Optional[str] = None,
    ) -> Optional[Decision]:
        """
        Record user's decision.

        Args:
            decision_id: Decision ID
            chosen_option: Option chosen by user
            decision_notes: Optional notes

        Returns:
            Updated Decision or None if not found
        """
        decision = self.get_decision(decision_id)

        if not decision:
            return None

        decision.status = "decided"
        decision.chosen_option = chosen_option
        decision.decision_notes = decision_notes
        decision.decided_at = datetime.utcnow()

        self.db.commit()

        # Log event (Event-First)
        log_event(
            event_type=EventType.DECISION_MADE,
            account_id=decision.account_id,
            email_id=decision.email_id,
            payload={
                'decision_id': decision_id,
                'question': decision.question,
                'chosen_option': chosen_option,
                'decision_notes': decision_notes,
            }
        )

        return decision

    # ========================================================================
    # QUESTION OPERATIONS
    # ========================================================================

    def create_question(
        self,
        account_id: str,
        email_id: str,
        question: str,
        question_type: str = "information",
        urgency: str = "medium",
        context: Optional[str] = None,
        requires_response: bool = True,
        email_subject: Optional[str] = None,
        email_sender: Optional[str] = None,
        email_received_at: Optional[datetime] = None,
        processed_email_id: Optional[int] = None,
        extraction_event_id: Optional[str] = None,
    ) -> Question:
        """
        Create a new question.

        Args:
            account_id: Account ID
            email_id: Email message ID
            question: The question being asked
            question_type: Type (yes_no, information, clarification, decision, opinion)
            urgency: Question urgency (low, medium, high, urgent)
            context: Additional context
            requires_response: Does it need a response?
            email_subject: Email subject for context
            email_sender: Email sender for context
            email_received_at: When email was received
            processed_email_id: Optional FK to ProcessedEmail
            extraction_event_id: Optional FK to extraction event

        Returns:
            Created Question object
        """
        question_obj = Question(
            account_id=account_id,
            email_id=email_id,
            question=question,
            question_type=question_type,
            urgency=urgency,
            context=context,
            requires_response=requires_response,
            email_subject=email_subject,
            email_sender=email_sender,
            email_received_at=email_received_at,
            processed_email_id=processed_email_id,
            extraction_event_id=extraction_event_id,
            status="pending",
        )

        self.db.add(question_obj)
        self.db.commit()
        self.db.refresh(question_obj)

        # Log event (Event-First)
        log_event(
            event_type=EventType.QUESTION_CREATED,
            account_id=account_id,
            email_id=email_id,
            payload={
                'question_id': question_obj.question_id,
                'question': question,
                'question_type': question_type,
                'urgency': urgency,
                'requires_response': requires_response,
            }
        )

        return question_obj

    def get_question(self, question_id: str) -> Optional[Question]:
        """Get a question by ID."""
        return self.db.query(Question).filter(Question.question_id == question_id).first()

    def get_pending_questions(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Question]:
        """
        Get pending questions.

        Args:
            account_id: Optional account filter
            limit: Maximum number of questions

        Returns:
            List of pending questions, ordered by urgency
        """
        query = self.db.query(Question).filter(Question.status == "pending")

        if account_id:
            query = query.filter(Question.account_id == account_id)

        # Order by urgency and creation time
        urgency_order = {
            'urgent': 0,
            'high': 1,
            'medium': 2,
            'low': 3,
        }

        questions = query.all()
        questions.sort(key=lambda q: (urgency_order.get(q.urgency, 2), q.created_at))

        if limit:
            questions = questions[:limit]

        return questions

    def get_questions_by_email(self, email_id: str) -> List[Question]:
        """Get all questions extracted from a specific email."""
        return self.db.query(Question).filter(Question.email_id == email_id).all()

    def answer_question(
        self,
        question_id: str,
        answer: str,
    ) -> Optional[Question]:
        """
        Record answer to a question.

        Args:
            question_id: Question ID
            answer: The answer

        Returns:
            Updated Question or None if not found
        """
        question = self.get_question(question_id)

        if not question:
            return None

        question.status = "answered"
        question.answer = answer
        question.answered_at = datetime.utcnow()

        self.db.commit()

        # Log event (Event-First)
        log_event(
            event_type=EventType.QUESTION_ANSWERED,
            account_id=question.account_id,
            email_id=question.email_id,
            payload={
                'question_id': question_id,
                'question': question.question,
                'answer': answer,
            }
        )

        return question

    # ========================================================================
    # JOURNAL OPERATIONS
    # ========================================================================

    def create_journal_entry(
        self,
        account_id: str,
        date: datetime,
        title: str,
        content_markdown: str,
        summary: Optional[str] = None,
        period_type: str = "daily",
        total_emails_processed: int = 0,
        total_tasks_created: int = 0,
        total_decisions_made: int = 0,
        total_questions_answered: int = 0,
        emails_by_category: Optional[Dict[str, int]] = None,
        top_senders: Optional[List[Dict[str, Any]]] = None,
        important_items: Optional[List[Dict[str, Any]]] = None,
        generation_event_id: Optional[str] = None,
    ) -> JournalEntry:
        """
        Create a new journal entry.

        Args:
            account_id: Account ID
            date: Date this journal covers
            title: Journal title
            content_markdown: Full journal content in Markdown
            summary: Brief summary
            period_type: Type (daily, weekly, monthly)
            total_emails_processed: Email count
            total_tasks_created: Task count
            total_decisions_made: Decision count
            total_questions_answered: Question count
            emails_by_category: Category breakdown
            top_senders: Top senders list
            important_items: Important items list
            generation_event_id: Optional FK to generation event

        Returns:
            Created JournalEntry object
        """
        journal = JournalEntry(
            account_id=account_id,
            date=date,
            title=title,
            content_markdown=content_markdown,
            summary=summary,
            period_type=period_type,
            total_emails_processed=total_emails_processed,
            total_tasks_created=total_tasks_created,
            total_decisions_made=total_decisions_made,
            total_questions_answered=total_questions_answered,
            emails_by_category=emails_by_category or {},
            top_senders=top_senders or [],
            important_items=important_items or [],
            generation_event_id=generation_event_id,
            status="generated",
        )

        self.db.add(journal)
        self.db.commit()
        self.db.refresh(journal)

        # Log event (Event-First)
        log_event(
            event_type=EventType.JOURNAL_GENERATED,
            account_id=account_id,
            payload={
                'journal_id': journal.journal_id,
                'date': date.isoformat(),
                'period_type': period_type,
                'total_emails_processed': total_emails_processed,
            }
        )

        return journal

    def get_journal_entry(self, journal_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID."""
        return self.db.query(JournalEntry).filter(JournalEntry.journal_id == journal_id).first()

    def get_journal_for_date(
        self,
        account_id: str,
        date: datetime,
    ) -> Optional[JournalEntry]:
        """
        Get journal entry for a specific date.

        Args:
            account_id: Account ID
            date: Date to find journal for

        Returns:
            JournalEntry or None if not found
        """
        # Convert to date only (no time)
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)

        return self.db.query(JournalEntry).filter(
            JournalEntry.account_id == account_id,
            JournalEntry.date >= date_only,
            JournalEntry.date < date_only + timedelta(days=1),
        ).first()

    def get_recent_journals(
        self,
        account_id: str,
        days: int = 7,
        limit: Optional[int] = None,
    ) -> List[JournalEntry]:
        """
        Get recent journal entries.

        Args:
            account_id: Account ID
            days: Number of days back to look
            limit: Maximum number of journals

        Returns:
            List of JournalEntries, ordered by date descending
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(JournalEntry).filter(
            JournalEntry.account_id == account_id,
            JournalEntry.date >= cutoff_date,
        ).order_by(JournalEntry.date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def mark_journal_reviewed(
        self,
        journal_id: str,
        user_notes: Optional[str] = None,
    ) -> Optional[JournalEntry]:
        """
        Mark journal as reviewed by user.

        Args:
            journal_id: Journal ID
            user_notes: Optional user notes

        Returns:
            Updated JournalEntry or None if not found
        """
        journal = self.get_journal_entry(journal_id)

        if not journal:
            return None

        journal.status = "reviewed"
        journal.reviewed_at = datetime.utcnow()

        if user_notes:
            journal.user_notes = user_notes

        self.db.commit()

        return journal


# ============================================================================
# CONVENIENCE FUNCTIONS (Module-level API)
# ============================================================================

# Singleton service instance
_service: Optional[MemoryService] = None


def _get_service() -> MemoryService:
    """Get or create singleton service instance."""
    global _service
    if _service is None:
        _service = MemoryService()
    return _service


# Task operations
def create_task(*args, **kwargs) -> Task:
    """Create a new task. See MemoryService.create_task for details."""
    return _get_service().create_task(*args, **kwargs)


def get_task(task_id: str) -> Optional[Task]:
    """Get a task by ID."""
    return _get_service().get_task(task_id)


def get_pending_tasks(account_id: Optional[str] = None, limit: Optional[int] = None) -> List[Task]:
    """Get pending tasks."""
    return _get_service().get_pending_tasks(account_id, limit)


def get_tasks_by_email(email_id: str) -> List[Task]:
    """Get all tasks extracted from a specific email."""
    return _get_service().get_tasks_by_email(email_id)


def update_task_status(task_id: str, new_status: str, completion_notes: Optional[str] = None) -> Optional[Task]:
    """Update task status."""
    return _get_service().update_task_status(task_id, new_status, completion_notes)


def complete_task(task_id: str, completion_notes: Optional[str] = None) -> Optional[Task]:
    """Mark task as completed."""
    return _get_service().complete_task(task_id, completion_notes)


# Decision operations
def create_decision(*args, **kwargs) -> Decision:
    """Create a new decision. See MemoryService.create_decision for details."""
    return _get_service().create_decision(*args, **kwargs)


def get_decision(decision_id: str) -> Optional[Decision]:
    """Get a decision by ID."""
    return _get_service().get_decision(decision_id)


def get_pending_decisions(account_id: Optional[str] = None, limit: Optional[int] = None) -> List[Decision]:
    """Get pending decisions."""
    return _get_service().get_pending_decisions(account_id, limit)


def get_decisions_by_email(email_id: str) -> List[Decision]:
    """Get all decisions extracted from a specific email."""
    return _get_service().get_decisions_by_email(email_id)


def make_decision(decision_id: str, chosen_option: str, decision_notes: Optional[str] = None) -> Optional[Decision]:
    """Record user's decision."""
    return _get_service().make_decision(decision_id, chosen_option, decision_notes)


# Question operations
def create_question(*args, **kwargs) -> Question:
    """Create a new question. See MemoryService.create_question for details."""
    return _get_service().create_question(*args, **kwargs)


def get_question(question_id: str) -> Optional[Question]:
    """Get a question by ID."""
    return _get_service().get_question(question_id)


def get_pending_questions(account_id: Optional[str] = None, limit: Optional[int] = None) -> List[Question]:
    """Get pending questions."""
    return _get_service().get_pending_questions(account_id, limit)


def get_questions_by_email(email_id: str) -> List[Question]:
    """Get all questions extracted from a specific email."""
    return _get_service().get_questions_by_email(email_id)


def answer_question(question_id: str, answer: str) -> Optional[Question]:
    """Record answer to a question."""
    return _get_service().answer_question(question_id, answer)


# Journal operations
def create_journal_entry(*args, **kwargs) -> JournalEntry:
    """Create a new journal entry. See MemoryService.create_journal_entry for details."""
    return _get_service().create_journal_entry(*args, **kwargs)


def get_journal_entry(journal_id: str) -> Optional[JournalEntry]:
    """Get a journal entry by ID."""
    return _get_service().get_journal_entry(journal_id)


def get_journal_for_date(account_id: str, date: datetime) -> Optional[JournalEntry]:
    """Get journal entry for a specific date."""
    return _get_service().get_journal_for_date(account_id, date)


def get_recent_journals(account_id: str, days: int = 7, limit: Optional[int] = None) -> List[JournalEntry]:
    """Get recent journal entries."""
    return _get_service().get_recent_journals(account_id, days, limit)


def mark_journal_reviewed(journal_id: str, user_notes: Optional[str] = None) -> Optional[JournalEntry]:
    """Mark journal as reviewed by user."""
    return _get_service().mark_journal_reviewed(journal_id, user_notes)
