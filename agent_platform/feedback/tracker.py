"""
Feedback Tracker - Learns from User Actions

Tracks user actions on emails and updates sender/domain preferences
to improve future classifications. Uses exponential moving average
for adaptive learning.

Actions Tracked:
- replied: User replied to email → High importance
- archived: User archived without reply → Medium/Low importance
- deleted: User deleted email → Very low importance / spam
- starred: User starred email → High importance
- moved_folder: User moved to specific folder → Context-dependent
- marked_important: User manually marked as important → High importance
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from sqlalchemy.orm import Session

from agent_platform.db.models import (
    SenderPreference,
    DomainPreference,
    FeedbackEvent,
    ProcessedEmail,
)
from agent_platform.db.database import get_db


# Action types that can be tracked
ActionType = Literal[
    "replied",
    "archived",
    "deleted",
    "starred",
    "moved_folder",
    "marked_important",
    "marked_spam",
]


class FeedbackTracker:
    """
    Tracks user actions and updates preferences for learning.

    Uses exponential moving average (EMA) to adapt to changing behavior
    patterns while still considering historical data.
    """

    # Learning rate for exponential moving average (0.0-1.0)
    # Higher = more weight to recent actions, Lower = more weight to history
    LEARNING_RATE = 0.15  # 15% weight to new action, 85% to history

    # Minimum emails before applying EMA (use simple average until threshold)
    MIN_EMAILS_FOR_EMA = 3

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize feedback tracker.

        Args:
            db: Optional database session (will create one if not provided)
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
    # MAIN TRACKING METHODS
    # ========================================================================

    def track_action(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
        action_type: ActionType,
        action_details: Optional[Dict[str, Any]] = None,
        email_received_at: Optional[datetime] = None,
        original_classification: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEvent:
        """
        Track a user action on an email.

        This is the main entry point for recording feedback. It:
        1. Creates a FeedbackEvent record
        2. Updates SenderPreference
        3. Updates DomainPreference
        4. Returns the created FeedbackEvent

        Args:
            email_id: Email identifier
            sender_email: Sender's email address
            account_id: Account ID (e.g., gmail_1)
            action_type: Type of action taken
            action_details: Optional additional details (e.g., folder name, time to action)
            email_received_at: When email was received
            original_classification: Original classification from system

        Returns:
            Created FeedbackEvent record
        """
        sender_domain = self._extract_domain(sender_email)

        # Infer importance and category from action
        inferred_importance, inferred_category = self._infer_from_action(
            action_type, action_details
        )

        # Calculate time to action if available
        time_to_action_hours = None
        if email_received_at:
            time_to_action_hours = (datetime.utcnow() - email_received_at).total_seconds() / 3600

        # Create feedback event
        feedback_event = FeedbackEvent(
            account_id=account_id,
            email_id=email_id,
            sender_email=sender_email.lower(),
            sender_domain=sender_domain,
            action_type=action_type,
            action_details=action_details or {},
            inferred_importance=inferred_importance,
            inferred_category=inferred_category,
            email_received_at=email_received_at,
            action_taken_at=datetime.utcnow(),
            original_category=original_classification.get("category") if original_classification else None,
            original_importance=original_classification.get("importance") if original_classification else None,
            original_confidence=original_classification.get("confidence") if original_classification else None,
        )

        self.db.add(feedback_event)

        # Update sender preference
        self._update_sender_preference(
            account_id=account_id,
            sender_email=sender_email.lower(),
            sender_domain=sender_domain,
            action_type=action_type,
            time_to_action_hours=time_to_action_hours,
            inferred_importance=inferred_importance,
            inferred_category=inferred_category,
        )

        # Update domain preference
        self._update_domain_preference(
            account_id=account_id,
            domain=sender_domain,
            action_type=action_type,
            inferred_importance=inferred_importance,
            inferred_category=inferred_category,
        )

        # Commit changes
        self.db.commit()

        return feedback_event

    # ========================================================================
    # CONVENIENCE METHODS FOR SPECIFIC ACTIONS
    # ========================================================================

    def track_reply(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
        email_received_at: Optional[datetime] = None,
    ) -> FeedbackEvent:
        """Track that user replied to an email."""
        return self.track_action(
            email_id=email_id,
            sender_email=sender_email,
            account_id=account_id,
            action_type="replied",
            email_received_at=email_received_at,
        )

    def track_archive(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
    ) -> FeedbackEvent:
        """Track that user archived an email without replying."""
        return self.track_action(
            email_id=email_id,
            sender_email=sender_email,
            account_id=account_id,
            action_type="archived",
        )

    def track_delete(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
    ) -> FeedbackEvent:
        """Track that user deleted an email."""
        return self.track_action(
            email_id=email_id,
            sender_email=sender_email,
            account_id=account_id,
            action_type="deleted",
        )

    def track_star(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
    ) -> FeedbackEvent:
        """Track that user starred an email."""
        return self.track_action(
            email_id=email_id,
            sender_email=sender_email,
            account_id=account_id,
            action_type="starred",
        )

    def track_folder_move(
        self,
        email_id: str,
        sender_email: str,
        account_id: str,
        folder_name: str,
    ) -> FeedbackEvent:
        """Track that user moved email to a specific folder."""
        return self.track_action(
            email_id=email_id,
            sender_email=sender_email,
            account_id=account_id,
            action_type="moved_folder",
            action_details={"folder": folder_name},
        )

    # ========================================================================
    # PREFERENCE UPDATE METHODS
    # ========================================================================

    def _update_sender_preference(
        self,
        account_id: str,
        sender_email: str,
        sender_domain: str,
        action_type: ActionType,
        time_to_action_hours: Optional[float],
        inferred_importance: float,
        inferred_category: str,
    ):
        """Update sender preference based on action."""
        # Get or create sender preference
        pref = (
            self.db.query(SenderPreference)
            .filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email,
            )
            .first()
        )

        if not pref:
            # Create new preference
            pref = SenderPreference(
                account_id=account_id,
                sender_email=sender_email,
                sender_domain=sender_domain,
                total_emails_received=0,
                total_replies=0,
                total_archived=0,
                total_deleted=0,
                total_moved_to_folder=0,
                reply_rate=0.0,
                archive_rate=0.0,
                delete_rate=0.0,
                average_importance=0.5,
            )
            self.db.add(pref)

        # Update counters
        pref.total_emails_received += 1

        if action_type == "replied":
            pref.total_replies += 1
        elif action_type == "archived":
            pref.total_archived += 1
        elif action_type == "deleted":
            pref.total_deleted += 1
        elif action_type == "moved_folder":
            pref.total_moved_to_folder += 1

        # Update rates
        total = pref.total_emails_received
        pref.reply_rate = pref.total_replies / total if total > 0 else 0.0
        pref.archive_rate = pref.total_archived / total if total > 0 else 0.0
        pref.delete_rate = pref.total_deleted / total if total > 0 else 0.0

        # Update average importance using EMA
        if pref.total_emails_received >= self.MIN_EMAILS_FOR_EMA:
            # Exponential moving average: new_avg = α * new_value + (1-α) * old_avg
            pref.average_importance = (
                self.LEARNING_RATE * inferred_importance
                + (1 - self.LEARNING_RATE) * pref.average_importance
            )
        else:
            # Simple average for first few emails
            # Calculate cumulative average
            old_sum = pref.average_importance * (pref.total_emails_received - 1)
            pref.average_importance = (old_sum + inferred_importance) / pref.total_emails_received

        # Update time to reply (only for replies)
        if action_type == "replied" and time_to_action_hours is not None:
            if pref.avg_time_to_reply_hours is None:
                pref.avg_time_to_reply_hours = time_to_action_hours
            else:
                # EMA for response time
                pref.avg_time_to_reply_hours = (
                    self.LEARNING_RATE * time_to_action_hours
                    + (1 - self.LEARNING_RATE) * pref.avg_time_to_reply_hours
                )

        # Update category (most common)
        pref.preferred_category = self._determine_preferred_category(pref)

        # Update timestamps
        pref.last_email_received = datetime.utcnow()
        pref.last_user_action = datetime.utcnow()
        pref.updated_at = datetime.utcnow()

    def _update_domain_preference(
        self,
        account_id: str,
        domain: str,
        action_type: ActionType,
        inferred_importance: float,
        inferred_category: str,
    ):
        """Update domain preference based on action."""
        # Get or create domain preference
        pref = (
            self.db.query(DomainPreference)
            .filter(
                DomainPreference.account_id == account_id,
                DomainPreference.domain == domain,
            )
            .first()
        )

        if not pref:
            # Create new preference
            pref = DomainPreference(
                account_id=account_id,
                domain=domain,
                total_emails_received=0,
                reply_rate=0.0,
                archive_rate=0.0,
                average_importance=0.5,
            )
            self.db.add(pref)

        # Update counters (simplified for domain level)
        pref.total_emails_received += 1

        # Update average importance using EMA
        if pref.total_emails_received >= self.MIN_EMAILS_FOR_EMA:
            pref.average_importance = (
                self.LEARNING_RATE * inferred_importance
                + (1 - self.LEARNING_RATE) * pref.average_importance
            )
        else:
            old_sum = pref.average_importance * (pref.total_emails_received - 1)
            pref.average_importance = (old_sum + inferred_importance) / pref.total_emails_received

        # Update preferred category
        pref.preferred_category = inferred_category

        # Update timestamp
        pref.last_updated = datetime.utcnow()

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _infer_from_action(
        self, action_type: ActionType, action_details: Optional[Dict[str, Any]] = None
    ) -> tuple[float, str]:
        """
        Infer importance and category from user action.

        Returns:
            (importance_score, category)
        """
        if action_type == "replied":
            # User replied → High importance
            return (0.85, "wichtig")

        elif action_type == "starred":
            # User starred → Very high importance
            return (0.95, "action_required")

        elif action_type == "marked_important":
            # User manually marked important → High importance
            return (0.90, "wichtig")

        elif action_type == "archived":
            # User archived without reply → Medium importance (informational)
            return (0.40, "nice_to_know")

        elif action_type == "deleted":
            # User deleted → Very low importance / spam
            return (0.05, "spam")

        elif action_type == "marked_spam":
            # User marked as spam → Spam
            return (0.0, "spam")

        elif action_type == "moved_folder":
            # Folder-specific inference
            folder = action_details.get("folder", "").lower() if action_details else ""

            if "important" in folder or "urgent" in folder:
                return (0.90, "wichtig")
            elif "work" in folder or "project" in folder:
                return (0.75, "action_required")
            elif "newsletter" in folder or "marketing" in folder:
                return (0.30, "newsletter")
            elif "archive" in folder:
                return (0.40, "nice_to_know")
            else:
                # Unknown folder → Medium importance
                return (0.50, "nice_to_know")

        # Default
        return (0.50, "nice_to_know")

    def _determine_preferred_category(self, pref: SenderPreference) -> str:
        """
        Determine preferred category based on action patterns.

        Uses reply/archive/delete rates to infer category.
        """
        if pref.reply_rate >= 0.7:
            # High reply rate → wichtig or action_required
            if pref.avg_time_to_reply_hours and pref.avg_time_to_reply_hours < 2.0:
                return "action_required"  # Quick responses
            return "wichtig"

        elif pref.archive_rate >= 0.8:
            # High archive rate without replies → newsletter
            return "newsletter"

        elif pref.delete_rate >= 0.5:
            # High delete rate → spam
            return "spam"

        else:
            # Medium engagement → nice_to_know
            return "nice_to_know"

    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if "@" in email:
            return email.split("@")[1].lower()
        return email.lower()

    # ========================================================================
    # QUERY METHODS
    # ========================================================================

    def get_sender_feedback_summary(
        self, account_id: str, sender_email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get feedback summary for a specific sender.

        Returns dictionary with:
        - total_emails: Total emails from sender
        - reply_rate: Percentage replied to
        - archive_rate: Percentage archived
        - delete_rate: Percentage deleted
        - average_importance: Learned importance (0.0-1.0)
        - preferred_category: Most common category
        - avg_time_to_reply_hours: Average response time
        """
        pref = (
            self.db.query(SenderPreference)
            .filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email.lower(),
            )
            .first()
        )

        if not pref:
            return None

        return {
            "total_emails": pref.total_emails_received,
            "reply_rate": pref.reply_rate,
            "archive_rate": pref.archive_rate,
            "delete_rate": pref.delete_rate,
            "average_importance": pref.average_importance,
            "preferred_category": pref.preferred_category,
            "avg_time_to_reply_hours": pref.avg_time_to_reply_hours,
        }

    def get_recent_feedback_events(
        self, account_id: str, limit: int = 10
    ) -> list[FeedbackEvent]:
        """Get recent feedback events for an account."""
        return (
            self.db.query(FeedbackEvent)
            .filter(FeedbackEvent.account_id == account_id)
            .order_by(FeedbackEvent.action_taken_at.desc())
            .limit(limit)
            .all()
        )
