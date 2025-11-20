"""
Journal Generator

Aggregates daily events and memory-objects into a human-readable journal.
Generates markdown summaries for daily review.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from agent_platform.events import get_events, EventType
from agent_platform.memory import (
    MemoryService,
    create_journal_entry,
    get_journal_for_date,
)
from agent_platform.db.database import get_db
from agent_platform.db.models import JournalEntry, ProcessedEmail, Task, Decision, Question
from agent_platform.monitoring import SystemLogger


class JournalGenerator:
    """
    Generates daily summary journals from events and memory-objects.

    Uses Event-First architecture to aggregate all daily activities
    into a human-readable markdown journal.
    """

    def __init__(self):
        """Initialize journal generator."""
        self.logger = SystemLogger.get_logger("journal")
        self.memory_service = MemoryService()

    async def generate_daily_journal(
        self,
        account_id: str,
        date: Optional[datetime] = None,
    ) -> JournalEntry:
        """
        Generate daily journal for a specific date.

        Args:
            account_id: Account ID (e.g., gmail_1)
            date: Date to generate journal for (default: today)

        Returns:
            Generated JournalEntry

        Example:
            generator = JournalGenerator()
            journal = await generator.generate_daily_journal("gmail_1")
            print(journal.content_markdown)
        """
        # Default to today
        if date is None:
            date = datetime.utcnow()

        # Convert to start/end of day
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        self.logger.info(f"📝 Generating daily journal for {account_id} on {date_start.date()}")

        # Check if journal already exists
        existing_journal = get_journal_for_date(account_id, date_start)
        if existing_journal:
            self.logger.info(f"📄 Journal already exists for {date_start.date()}")
            return existing_journal

        # Gather statistics
        stats = await self._gather_statistics(account_id, date_start, date_end)

        # Gather highlights
        highlights = await self._gather_highlights(account_id, date_start, date_end)

        # Generate markdown content
        content_markdown = self._generate_markdown(
            account_id=account_id,
            date=date_start,
            stats=stats,
            highlights=highlights,
        )

        # Generate title
        title = self._generate_title(date_start, stats)

        # Generate summary
        summary = self._generate_summary(stats, highlights)

        # Create journal entry
        journal = create_journal_entry(
            account_id=account_id,
            date=date_start,
            title=title,
            content_markdown=content_markdown,
            summary=summary,
            period_type="daily",
            total_emails_processed=stats['total_emails'],
            total_tasks_created=stats['total_tasks'],
            total_decisions_made=stats['total_decisions'],
            total_questions_answered=stats['total_questions'],
            emails_by_category=stats['emails_by_category'],
            top_senders=highlights['top_senders'],
            important_items=highlights['important_items'],
        )

        self.logger.info(f"✅ Daily journal generated: {title}")

        return journal

    async def _gather_statistics(
        self,
        account_id: str,
        date_start: datetime,
        date_end: datetime,
    ) -> Dict[str, Any]:
        """
        Gather statistics for the day.

        Args:
            account_id: Account ID
            date_start: Start of day
            date_end: End of day

        Returns:
            Dictionary with statistics
        """
        with get_db() as db:
            # Count tasks created today
            total_tasks = db.query(Task).filter(
                Task.account_id == account_id,
                Task.created_at >= date_start,
                Task.created_at < date_end,
            ).count()

            # Get all tasks to count emails (deduplicated by email_id)
            tasks_today = db.query(Task).filter(
                Task.account_id == account_id,
                Task.created_at >= date_start,
                Task.created_at < date_end,
            ).all()

            decisions_today = db.query(Decision).filter(
                Decision.account_id == account_id,
                Decision.created_at >= date_start,
                Decision.created_at < date_end,
            ).all()

            questions_today = db.query(Question).filter(
                Question.account_id == account_id,
                Question.created_at >= date_start,
                Question.created_at < date_end,
            ).all()

            # Deduplicate email IDs to count unique emails processed
            all_email_ids = set()
            for task in tasks_today:
                if task.email_id:
                    all_email_ids.add(task.email_id)
            for decision in decisions_today:
                if decision.email_id:
                    all_email_ids.add(decision.email_id)
            for question in questions_today:
                if question.email_id:
                    all_email_ids.add(question.email_id)

            total_emails = len(all_email_ids)

            # Count decisions made today (status = 'decided')
            total_decisions = db.query(Decision).filter(
                Decision.account_id == account_id,
                Decision.decided_at >= date_start,
                Decision.decided_at < date_end,
            ).count()

            # Count questions answered today (status = 'answered')
            total_questions = db.query(Question).filter(
                Question.account_id == account_id,
                Question.answered_at >= date_start,
                Question.answered_at < date_end,
            ).count()

            # For now, we don't have category breakdown from ProcessedEmail
            # (due to FK inconsistency), so we'll use empty dict
            emails_by_category = {}

            return {
                'total_emails': total_emails,
                'total_tasks': total_tasks,
                'total_decisions': total_decisions,
                'total_questions': total_questions,
                'emails_by_category': emails_by_category,
            }

    async def _gather_highlights(
        self,
        account_id: str,
        date_start: datetime,
        date_end: datetime,
    ) -> Dict[str, Any]:
        """
        Gather highlights for the day.

        Args:
            account_id: Account ID
            date_start: Start of day
            date_end: End of day

        Returns:
            Dictionary with highlights
        """
        with get_db() as db:
            # Top senders from tasks/decisions/questions
            # (since ProcessedEmail FK is inconsistent with our string account_ids)
            tasks_today = db.query(Task).filter(
                Task.account_id == account_id,
                Task.created_at >= date_start,
                Task.created_at < date_end,
            ).all()

            decisions_today = db.query(Decision).filter(
                Decision.account_id == account_id,
                Decision.created_at >= date_start,
                Decision.created_at < date_end,
            ).all()

            questions_today = db.query(Question).filter(
                Question.account_id == account_id,
                Question.created_at >= date_start,
                Question.created_at < date_end,
            ).all()

            sender_counts = defaultdict(int)
            for task in tasks_today:
                if task.email_sender:
                    sender_counts[task.email_sender] += 1
            for decision in decisions_today:
                if decision.email_sender:
                    sender_counts[decision.email_sender] += 1
            for question in questions_today:
                if question.email_sender:
                    sender_counts[question.email_sender] += 1

            # Sort by count and take top 5
            top_senders = [
                {'sender': sender, 'count': count}
                for sender, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

            # Important items (high priority tasks, urgent decisions/questions)
            important_items = []

            # High priority tasks
            high_priority_tasks = db.query(Task).filter(
                Task.account_id == account_id,
                Task.created_at >= date_start,
                Task.created_at < date_end,
                Task.priority.in_(['high', 'urgent']),
            ).all()

            for task in high_priority_tasks:
                important_items.append({
                    'type': 'task',
                    'description': task.description,
                    'priority': task.priority,
                    'deadline': task.deadline.isoformat() if task.deadline else None,
                })

            # Urgent decisions
            urgent_decisions = db.query(Decision).filter(
                Decision.account_id == account_id,
                Decision.created_at >= date_start,
                Decision.created_at < date_end,
                Decision.urgency.in_(['high', 'urgent']),
            ).all()

            for decision in urgent_decisions:
                important_items.append({
                    'type': 'decision',
                    'question': decision.question,
                    'urgency': decision.urgency,
                })

            # Urgent questions
            urgent_questions = db.query(Question).filter(
                Question.account_id == account_id,
                Question.created_at >= date_start,
                Question.created_at < date_end,
                Question.urgency.in_(['high', 'urgent']),
            ).all()

            for question in urgent_questions:
                important_items.append({
                    'type': 'question',
                    'question': question.question,
                    'urgency': question.urgency,
                })

            return {
                'top_senders': top_senders,
                'important_items': important_items,
            }

    def _generate_markdown(
        self,
        account_id: str,
        date: datetime,
        stats: Dict[str, Any],
        highlights: Dict[str, Any],
    ) -> str:
        """
        Generate markdown content for journal.

        Args:
            account_id: Account ID
            date: Journal date
            stats: Statistics dictionary
            highlights: Highlights dictionary

        Returns:
            Markdown content
        """
        lines = []

        # Header
        lines.append(f"# Daily Email Journal - {date.strftime('%A, %B %d, %Y')}")
        lines.append("")
        lines.append(f"**Account:** {account_id}")
        lines.append("")

        # Summary section
        lines.append("## 📊 Daily Summary")
        lines.append("")
        lines.append(f"- **Emails Processed:** {stats['total_emails']}")
        lines.append(f"- **Tasks Created:** {stats['total_tasks']}")
        lines.append(f"- **Decisions Made:** {stats['total_decisions']}")
        lines.append(f"- **Questions Answered:** {stats['total_questions']}")
        lines.append("")

        # Email breakdown by category
        if stats['emails_by_category']:
            lines.append("### Email Breakdown by Category")
            lines.append("")
            for category, count in sorted(stats['emails_by_category'].items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{category}:** {count}")
            lines.append("")

        # Top senders
        if highlights['top_senders']:
            lines.append("## 👥 Top Senders")
            lines.append("")
            for item in highlights['top_senders']:
                lines.append(f"- **{item['sender']}:** {item['count']} email(s)")
            lines.append("")

        # Important items
        if highlights['important_items']:
            lines.append("## ⚠️ Important Items")
            lines.append("")

            # Group by type
            tasks = [item for item in highlights['important_items'] if item['type'] == 'task']
            decisions = [item for item in highlights['important_items'] if item['type'] == 'decision']
            questions = [item for item in highlights['important_items'] if item['type'] == 'question']

            if tasks:
                lines.append("### 📋 High Priority Tasks")
                lines.append("")
                for task in tasks:
                    deadline_str = f" (Due: {task['deadline'][:10]})" if task['deadline'] else ""
                    lines.append(f"- **[{task['priority'].upper()}]** {task['description']}{deadline_str}")
                lines.append("")

            if decisions:
                lines.append("### 🤔 Urgent Decisions")
                lines.append("")
                for decision in decisions:
                    lines.append(f"- **[{decision['urgency'].upper()}]** {decision['question']}")
                lines.append("")

            if questions:
                lines.append("### ❓ Urgent Questions")
                lines.append("")
                for question in questions:
                    lines.append(f"- **[{question['urgency'].upper()}]** {question['question']}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")

        return "\n".join(lines)

    def _generate_title(self, date: datetime, stats: Dict[str, Any]) -> str:
        """
        Generate journal title.

        Args:
            date: Journal date
            stats: Statistics dictionary

        Returns:
            Journal title
        """
        return f"Daily Email Journal - {date.strftime('%Y-%m-%d')} ({stats['total_emails']} emails)"

    def _generate_summary(self, stats: Dict[str, Any], highlights: Dict[str, Any]) -> str:
        """
        Generate brief summary.

        Args:
            stats: Statistics dictionary
            highlights: Highlights dictionary

        Returns:
            Brief summary
        """
        summary_parts = []

        summary_parts.append(f"Processed {stats['total_emails']} emails")

        if stats['total_tasks'] > 0:
            summary_parts.append(f"created {stats['total_tasks']} tasks")

        if stats['total_decisions'] > 0:
            summary_parts.append(f"made {stats['total_decisions']} decisions")

        if stats['total_questions'] > 0:
            summary_parts.append(f"answered {stats['total_questions']} questions")

        if highlights['important_items']:
            summary_parts.append(f"{len(highlights['important_items'])} important items requiring attention")

        return ", ".join(summary_parts) + "."


# ============================================================================
# CONVENIENCE FUNCTION (Module-level API)
# ============================================================================

_generator: Optional[JournalGenerator] = None


def _get_generator() -> JournalGenerator:
    """Get or create singleton generator instance."""
    global _generator
    if _generator is None:
        _generator = JournalGenerator()
    return _generator


async def generate_daily_journal(
    account_id: str,
    date: Optional[datetime] = None,
) -> JournalEntry:
    """
    Generate daily journal for a specific date.

    Args:
        account_id: Account ID (e.g., gmail_1)
        date: Date to generate journal for (default: today)

    Returns:
        Generated JournalEntry
    """
    return await _get_generator().generate_daily_journal(account_id, date)
