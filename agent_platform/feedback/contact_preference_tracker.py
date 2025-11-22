"""
Contact Preference Tracker - Bidirectional Email Communication Tracking

Tracks both INCOMING (received) and OUTGOING (sent) emails for each contact
to calculate bidirectional importance and relationship type.

Key Metrics:
- Incoming: emails received, replies sent, reply rate, avg time to reply
- Outgoing: emails sent, threads initiated, sent with reply, initiation rate
- Combined: total exchanged, contact importance, relationship type

Relationship Types:
- proactive: I initiate frequently (>60% initiation rate)
- reactive: I mostly reply (>60% reply rate, <30% initiation)
- bidirectional: Balanced communication (30-60% both ways)
- one_way_outgoing: I send, they rarely reply (<20% sent_reply_rate)
- one_way_incoming: They send, I rarely reply (<20% reply_rate)
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from agent_platform.db.models import ContactPreference
from agent_platform.db.database import get_db


class ContactPreferenceTracker:
    """
    Track bidirectional contact preferences and calculate relationship importance.
    """

    def track_incoming_email(
        self,
        account_id: str,
        sender_email: str,
        sender_domain: str,
        sender_name: Optional[str] = None,
    ) -> ContactPreference:
        """
        Track an incoming email from a contact.

        Args:
            account_id: User's email account ID
            sender_email: Email address of sender
            sender_domain: Domain of sender
            sender_name: Display name of sender (optional)

        Returns:
            Updated ContactPreference object
        """
        with get_db() as db:
            contact = self._get_or_create_contact(
                db, account_id, sender_email, sender_domain, sender_name
            )

            # Update incoming stats
            contact.total_emails_received += 1
            contact.total_emails_exchanged = (
                contact.total_emails_received + contact.total_emails_sent
            )
            contact.last_email_received = datetime.utcnow()

            # Update contact timestamp
            if contact.last_contact_at is None or contact.last_email_received > contact.last_contact_at:
                contact.last_contact_at = contact.last_email_received

            # Recalculate metrics
            self._recalculate_metrics(contact)

            contact.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(contact)

            return contact

    def track_outgoing_email(
        self,
        account_id: str,
        recipient_email: str,
        recipient_domain: str,
        is_reply: bool = False,
        is_new_thread: bool = False,
        recipient_name: Optional[str] = None,
    ) -> ContactPreference:
        """
        Track an outgoing email to a contact.

        Args:
            account_id: User's email account ID
            recipient_email: Email address of recipient
            recipient_domain: Domain of recipient
            is_reply: Whether this email is a reply to their email
            is_new_thread: Whether this email starts a new thread (initiated by me)
            recipient_name: Display name of recipient (optional)

        Returns:
            Updated ContactPreference object
        """
        with get_db() as db:
            contact = self._get_or_create_contact(
                db, account_id, recipient_email, recipient_domain, recipient_name
            )

            # Update outgoing stats
            contact.total_emails_sent += 1
            contact.total_emails_exchanged = (
                contact.total_emails_received + contact.total_emails_sent
            )
            contact.last_email_sent = datetime.utcnow()

            # Track thread initiation
            if is_new_thread:
                contact.total_initiated_threads += 1

            # Track replies to their emails
            if is_reply:
                contact.total_replies_sent += 1

            # Update contact timestamp
            if contact.last_contact_at is None or contact.last_email_sent > contact.last_contact_at:
                contact.last_contact_at = contact.last_email_sent

            # Recalculate metrics
            self._recalculate_metrics(contact)

            contact.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(contact)

            return contact

    def track_reply_sent(
        self,
        account_id: str,
        recipient_email: str,
        recipient_domain: str,
        time_to_reply_hours: float,
        recipient_name: Optional[str] = None,
    ) -> ContactPreference:
        """
        Track a reply sent to a contact's email.

        Args:
            account_id: User's email account ID
            recipient_email: Email address we're replying to
            recipient_domain: Domain of recipient
            time_to_reply_hours: Hours between receiving and replying
            recipient_name: Display name of recipient (optional)

        Returns:
            Updated ContactPreference object
        """
        with get_db() as db:
            contact = self._get_or_create_contact(
                db, account_id, recipient_email, recipient_domain, recipient_name
            )

            # Update reply stats
            contact.total_replies_sent += 1

            # Update average time to reply (exponential moving average)
            if contact.avg_time_to_reply_hours is None:
                contact.avg_time_to_reply_hours = time_to_reply_hours
            else:
                # 30% new value, 70% historical average
                alpha = 0.3
                contact.avg_time_to_reply_hours = (
                    alpha * time_to_reply_hours
                    + (1 - alpha) * contact.avg_time_to_reply_hours
                )

            # Recalculate metrics
            self._recalculate_metrics(contact)

            contact.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(contact)

            return contact

    def track_sent_email_replied(
        self,
        account_id: str,
        recipient_email: str,
        recipient_domain: str,
        recipient_name: Optional[str] = None,
    ) -> ContactPreference:
        """
        Track when a contact replies to an email we sent.

        Args:
            account_id: User's email account ID
            recipient_email: Email address that replied
            recipient_domain: Domain of recipient
            recipient_name: Display name (optional)

        Returns:
            Updated ContactPreference object
        """
        with get_db() as db:
            contact = self._get_or_create_contact(
                db, account_id, recipient_email, recipient_domain, recipient_name
            )

            # Update sent-reply stats
            contact.total_sent_with_reply += 1

            # Recalculate metrics
            self._recalculate_metrics(contact)

            contact.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(contact)

            return contact

    def get_contact_preference(
        self, account_id: str, contact_email: str
    ) -> Optional[ContactPreference]:
        """
        Get contact preference for a specific email address.

        Args:
            account_id: User's email account ID
            contact_email: Email address to look up

        Returns:
            ContactPreference object or None if not found
        """
        with get_db() as db:
            return (
                db.query(ContactPreference)
                .filter(
                    ContactPreference.account_id == account_id,
                    ContactPreference.contact_email == contact_email,
                )
                .first()
            )

    def _get_or_create_contact(
        self,
        db: Session,
        account_id: str,
        contact_email: str,
        contact_domain: str,
        contact_name: Optional[str] = None,
    ) -> ContactPreference:
        """
        Get existing contact or create new one.

        Args:
            db: Database session
            account_id: User's email account ID
            contact_email: Email address
            contact_domain: Email domain
            contact_name: Display name (optional)

        Returns:
            ContactPreference object (existing or new)
        """
        contact = (
            db.query(ContactPreference)
            .filter(
                ContactPreference.account_id == account_id,
                ContactPreference.contact_email == contact_email,
            )
            .first()
        )

        if contact is None:
            now = datetime.utcnow()
            contact = ContactPreference(
                account_id=account_id,
                contact_email=contact_email,
                contact_domain=contact_domain,
                contact_name=contact_name,
                created_at=now,
                updated_at=now,
            )
            db.add(contact)
            db.flush()  # Get ID without committing

        elif contact_name and not contact.contact_name:
            # Update name if we didn't have it before
            contact.contact_name = contact_name

        return contact

    def _recalculate_metrics(self, contact: ContactPreference) -> None:
        """
        Recalculate all derived metrics for a contact.

        Updates:
        - reply_rate
        - initiation_rate
        - sent_reply_rate
        - avg_emails_sent_per_week
        - contact_importance
        - relationship_type

        Args:
            contact: ContactPreference object to update
        """
        # Reply rate (how often I reply to their emails)
        if contact.total_emails_received > 0:
            contact.reply_rate = contact.total_replies_sent / contact.total_emails_received
        else:
            contact.reply_rate = 0.0

        # Initiation rate (how often I start new threads)
        if contact.total_emails_sent > 0:
            contact.initiation_rate = contact.total_initiated_threads / contact.total_emails_sent
        else:
            contact.initiation_rate = 0.0

        # Sent reply rate (how often they reply to emails I send)
        if contact.total_emails_sent > 0:
            contact.sent_reply_rate = contact.total_sent_with_reply / contact.total_emails_sent
        else:
            contact.sent_reply_rate = 0.0

        # Average emails sent per week (based on time since first contact)
        if contact.created_at:
            weeks_since_first_contact = max(
                1, (datetime.utcnow() - contact.created_at).days / 7
            )
            contact.avg_emails_sent_per_week = (
                contact.total_emails_sent / weeks_since_first_contact
            )
        else:
            contact.avg_emails_sent_per_week = 0.0

        # Calculate contact importance (weighted combination)
        # Weights: 40% outgoing, 30% reply, 20% initiation, 10% incoming
        outgoing_score = min(1.0, contact.total_emails_sent / 50)  # Cap at 50 emails
        reply_score = contact.reply_rate
        initiation_score = contact.initiation_rate
        incoming_score = min(1.0, contact.total_emails_received / 50)

        contact.contact_importance = (
            0.40 * outgoing_score
            + 0.30 * reply_score
            + 0.20 * initiation_score
            + 0.10 * incoming_score
        )

        # Ensure importance is in valid range [0, 1]
        contact.contact_importance = max(0.0, min(1.0, contact.contact_importance))

        # Determine relationship type
        contact.relationship_type = self._calculate_relationship_type(contact)

    def _calculate_relationship_type(self, contact: ContactPreference) -> str:
        """
        Calculate relationship type based on communication patterns.

        Types:
        - proactive: I initiate frequently (>60% initiation rate)
        - reactive: I mostly reply (>60% reply rate, <30% initiation)
        - bidirectional: Balanced communication (30-60% both ways)
        - one_way_outgoing: I send, they rarely reply (<20% sent_reply_rate)
        - one_way_incoming: They send, I rarely reply (<20% reply_rate)

        Args:
            contact: ContactPreference object

        Returns:
            Relationship type string
        """
        # Check for one-way communication
        if contact.total_emails_sent >= 5 and contact.sent_reply_rate < 0.2:
            return "one_way_outgoing"

        if contact.total_emails_received >= 5 and contact.reply_rate < 0.2:
            return "one_way_incoming"

        # Check for proactive relationship
        if contact.initiation_rate > 0.6:
            return "proactive"

        # Check for reactive relationship
        if contact.reply_rate > 0.6 and contact.initiation_rate < 0.3:
            return "reactive"

        # Check for bidirectional
        if (
            0.3 <= contact.reply_rate <= 0.7
            or 0.3 <= contact.initiation_rate <= 0.7
        ):
            return "bidirectional"

        # Default to neutral
        return "neutral"
