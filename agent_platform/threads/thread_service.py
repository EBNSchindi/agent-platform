"""
Thread Summarization Service
Handles email thread tracking and LLM-based summarization.
"""

import logging
from typing import List, Optional
from datetime import datetime

from agent_platform.threads.models import ThreadSummary, ThreadEmail, ThreadSummarizationPrompt
from agent_platform.db.models import ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.llm import get_llm_provider
from agent_platform.events import log_event, EventType

logger = logging.getLogger(__name__)


class ThreadService:
    """
    Service for managing email threads and generating summaries.

    Features:
    - Track emails by thread_id
    - Generate LLM-based thread summaries
    - Store thread metadata in database
    """

    def __init__(self):
        self.llm = get_llm_provider()

    def get_thread_emails(
        self,
        thread_id: str,
        account_id: Optional[str] = None,
    ) -> List[ProcessedEmail]:
        """
        Get all emails in a thread, ordered by received_at.

        Args:
            thread_id: Gmail thread ID
            account_id: Optional account ID filter

        Returns:
            List of ProcessedEmail records in chronological order
        """
        with get_db() as db:
            query = db.query(ProcessedEmail).filter(
                ProcessedEmail.thread_id == thread_id
            )

            if account_id:
                query = query.join(ProcessedEmail.account).filter(
                    ProcessedEmail.account.has(account_id=account_id)
                )

            emails = query.order_by(ProcessedEmail.received_at).all()

            # Force load all attributes before session closes
            for email in emails:
                # Access all attributes that will be needed outside session
                # This loads them into the object's __dict__ before detachment
                _ = (email.id, email.email_id, email.subject, email.sender,
                     email.received_at, email.body_text, email.summary,
                     email.thread_summary, email.thread_position, email.is_thread_start,
                     email.thread_id, email.account_id)

            # Expunge objects from session so they can be used outside session
            for email in emails:
                db.expunge(email)

            return emails

    async def summarize_thread(
        self,
        thread_id: str,
        account_id: str,
        force_regenerate: bool = False,
    ) -> ThreadSummary:
        """
        Generate or retrieve thread summary.

        Args:
            thread_id: Gmail thread ID
            account_id: Account ID
            force_regenerate: If True, regenerate even if summary exists

        Returns:
            ThreadSummary with LLM-generated summary and key points
        """
        # Get all emails in thread
        thread_emails = self.get_thread_emails(thread_id, account_id)

        if not thread_emails:
            raise ValueError(f"No emails found for thread {thread_id}")

        # Check if first email already has thread summary
        first_email = thread_emails[0]
        if first_email.thread_summary and not force_regenerate:
            logger.info(f"Using existing thread summary for {thread_id}")
            return self._build_thread_summary(thread_emails, first_email.thread_summary)

        # Generate new summary with LLM
        logger.info(f"Generating thread summary for {thread_id} ({len(thread_emails)} emails)")

        prompt_data = ThreadSummarizationPrompt(
            thread_id=thread_id,
            emails=[
                {
                    'sender': email.sender,
                    'subject': email.subject,
                    'received_at': str(email.received_at),
                    'body_text': email.body_text or email.summary or '',
                }
                for email in thread_emails
            ]
        )

        # Call LLM
        llm_summary = await self.llm.generate_text(
            prompt=prompt_data.format_for_llm(),
            max_tokens=300,
        )

        # Store summary in first email record
        with get_db() as db:
            email_record = db.query(ProcessedEmail).filter(
                ProcessedEmail.id == first_email.id
            ).first()

            if email_record:
                email_record.thread_summary = llm_summary
                email_record.is_thread_start = True
                email_record.thread_position = 1

            # Update positions for all emails in thread
            for i, email in enumerate(thread_emails, 1):
                email_obj = db.query(ProcessedEmail).filter(
                    ProcessedEmail.id == email.id
                ).first()
                if email_obj:
                    email_obj.thread_position = i
                    email_obj.is_thread_start = (i == 1)

        # Log event
        log_event(
            event_type=EventType.EMAIL_SUMMARIZED,
            account_id=account_id,
            email_id=first_email.email_id,
            payload={
                'thread_id': thread_id,
                'email_count': len(thread_emails),
                'summary': llm_summary,
            }
        )

        logger.info(f"Thread summary generated for {thread_id}")

        return self._build_thread_summary(thread_emails, llm_summary)

    def _build_thread_summary(
        self,
        thread_emails: List[ProcessedEmail],
        summary_text: str,
    ) -> ThreadSummary:
        """Build ThreadSummary model from database records"""
        if not thread_emails:
            raise ValueError("Cannot build thread summary from empty list")

        first_email = thread_emails[0]
        last_email = thread_emails[-1]

        # Extract participants
        participants = list(set(email.sender for email in thread_emails if email.sender))

        # Build ThreadEmail objects
        emails = [
            ThreadEmail(
                email_id=email.email_id,
                subject=email.subject or "No subject",
                sender=email.sender or "Unknown",
                received_at=email.received_at or datetime.utcnow(),
                summary=email.summary,
                position=email.thread_position or (i + 1),
                is_thread_start=email.is_thread_start or (i == 0),
            )
            for i, email in enumerate(thread_emails)
        ]

        return ThreadSummary(
            thread_id=first_email.thread_id,
            account_id=str(first_email.account_id),
            email_count=len(thread_emails),
            participants=participants,
            subject=first_email.subject or "No subject",
            started_at=first_email.received_at or datetime.utcnow(),
            last_email_at=last_email.received_at or datetime.utcnow(),
            summary=summary_text,
            key_points=[],  # Could extract key points in future
            emails=emails,
        )
