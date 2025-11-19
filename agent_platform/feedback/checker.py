"""
Feedback Checker - Automatically Detects User Actions

Periodically checks email accounts for user actions on previously
classified emails:
- Replied: Email has a reply in the thread
- Archived: Email removed from inbox but not deleted
- Deleted: Email in trash
- Starred: Email has star/flag
- Moved: Email in different folder/label

This runs as a background job (typically every hour) to detect
actions and feed them to the FeedbackTracker for learning.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from agent_platform.db.models import ProcessedEmail, FeedbackEvent
from agent_platform.db.database import get_db
from agent_platform.feedback.tracker import FeedbackTracker, ActionType


class FeedbackChecker:
    """
    Checks for user actions on processed emails and tracks feedback.

    This class is designed to run periodically (e.g., hourly) to detect
    user actions and update preferences automatically.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize feedback checker.

        Args:
            db: Optional database session
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        self.tracker = FeedbackTracker(db=self.db)

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN CHECK METHODS
    # ========================================================================

    def check_account_for_feedback(
        self,
        account_id: str,
        hours_back: int = 24,
    ) -> Dict[str, Any]:
        """
        Check an account for user actions on processed emails.

        Args:
            account_id: Account ID to check (e.g., gmail_1)
            hours_back: How many hours back to check (default: 24)

        Returns:
            Dictionary with statistics:
            - emails_checked: Number of emails checked
            - actions_detected: Number of new actions detected
            - actions_by_type: Breakdown by action type
        """
        # Get emails processed in the last N hours
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        processed_emails = (
            self.db.query(ProcessedEmail)
            .filter(
                ProcessedEmail.account_id == account_id,
                ProcessedEmail.processed_at >= cutoff_time,
            )
            .all()
        )

        stats = {
            "emails_checked": len(processed_emails),
            "actions_detected": 0,
            "actions_by_type": {},
        }

        # Check each processed email for actions
        for email in processed_emails:
            # Check if we've already tracked feedback for this email
            existing_feedback = (
                self.db.query(FeedbackEvent)
                .filter(FeedbackEvent.email_id == email.email_id)
                .first()
            )

            if existing_feedback:
                # Already tracked - skip
                continue

            # Detect action (this would need to be implemented per email provider)
            # For now, this is a placeholder that shows the structure
            action = self._detect_action_on_email(account_id, email)

            if action:
                # Track the action
                self.tracker.track_action(
                    email_id=email.email_id,
                    sender_email=email.sender,
                    account_id=account_id,
                    action_type=action["type"],
                    action_details=action.get("details"),
                    email_received_at=email.received_at,
                    original_classification={
                        "category": email.category,
                        "confidence": email.confidence,
                        "importance": email.importance_score,
                    }
                    if email.category
                    else None,
                )

                stats["actions_detected"] += 1
                stats["actions_by_type"][action["type"]] = (
                    stats["actions_by_type"].get(action["type"], 0) + 1
                )

        return stats

    def _detect_action_on_email(
        self, account_id: str, email: ProcessedEmail
    ) -> Optional[Dict[str, Any]]:
        """
        Detect what action (if any) the user took on this email.

        This is a placeholder method that should be implemented
        per email provider (Gmail, Ionos, etc.).

        Args:
            account_id: Account ID
            email: ProcessedEmail record

        Returns:
            Dictionary with action info, or None if no action detected
            {
                "type": "replied" | "archived" | "deleted" | "starred" | "moved_folder",
                "details": {...}  # Optional additional details
            }
        """
        # This would need to be implemented by:
        # 1. For Gmail: Use Gmail API to check:
        #    - Thread has reply from user
        #    - Message has star
        #    - Message not in INBOX (archived)
        #    - Message in TRASH (deleted)
        #    - Message has specific labels (moved to folder)
        #
        # 2. For IMAP (Ionos): Use IMAP to check:
        #    - Search for replies in thread
        #    - Check flags (\Flagged, \Deleted, \Seen)
        #    - Check which folder email is in

        # Placeholder implementation
        # In real implementation, this would call Gmail/IMAP APIs

        # Example Gmail implementation (commented out):
        """
        if account_id.startswith("gmail_"):
            from modules.email.tools.gmail_tools import get_gmail_service

            service = get_gmail_service(account_id)
            message = service.users().messages().get(
                userId='me',
                id=email.email_id,
                format='metadata'
            ).execute()

            # Check for reply
            if 'SENT' in message.get('labelIds', []):
                return {"type": "replied"}

            # Check for star
            if 'STARRED' in message.get('labelIds', []):
                return {"type": "starred"}

            # Check for archive (not in INBOX)
            if 'INBOX' not in message.get('labelIds', []):
                if 'TRASH' in message.get('labelIds', []):
                    return {"type": "deleted"}
                else:
                    return {"type": "archived"}
        """

        return None  # No action detected (or not implemented yet)

    # ========================================================================
    # BATCH CHECKING
    # ========================================================================

    def check_all_accounts(
        self, hours_back: int = 24
    ) -> Dict[str, Dict[str, Any]]:
        """
        Check all active accounts for feedback.

        Args:
            hours_back: How many hours back to check

        Returns:
            Dictionary mapping account_id to stats
        """
        from agent_platform.core.config import Config

        results = {}

        # Check all Gmail accounts
        for account_key in ["gmail_1", "gmail_2", "gmail_3"]:
            account_config = Config.GMAIL_ACCOUNTS.get(account_key, {})
            if account_config.get("email"):
                try:
                    stats = self.check_account_for_feedback(account_key, hours_back)
                    results[account_key] = stats
                except Exception as e:
                    results[account_key] = {"error": str(e)}

        # Check Ionos account
        if Config.IONOS_ACCOUNT.get("email"):
            try:
                stats = self.check_account_for_feedback("ionos", hours_back)
                results["ionos"] = stats
            except Exception as e:
                results["ionos"] = {"error": str(e)}

        return results

    # ========================================================================
    # MANUAL TRACKING HELPERS
    # ========================================================================

    def manually_track_reply(
        self,
        email_id: str,
        account_id: str,
    ) -> Optional[FeedbackEvent]:
        """
        Manually track that user replied to an email.

        Useful for immediate tracking when reply is detected
        (e.g., from email sending logic).

        Args:
            email_id: Email ID
            account_id: Account ID

        Returns:
            FeedbackEvent if tracked, None if email not found
        """
        # Get the processed email
        email = (
            self.db.query(ProcessedEmail)
            .filter(
                ProcessedEmail.email_id == email_id,
                ProcessedEmail.account_id == account_id,
            )
            .first()
        )

        if not email:
            return None

        # Track the reply
        return self.tracker.track_reply(
            email_id=email.email_id,
            sender_email=email.sender,
            account_id=account_id,
            email_received_at=email.received_at,
        )

    def manually_track_action(
        self,
        email_id: str,
        account_id: str,
        action_type: ActionType,
        action_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[FeedbackEvent]:
        """
        Manually track a specific action on an email.

        Args:
            email_id: Email ID
            account_id: Account ID
            action_type: Type of action
            action_details: Optional action details

        Returns:
            FeedbackEvent if tracked, None if email not found
        """
        # Get the processed email
        email = (
            self.db.query(ProcessedEmail)
            .filter(
                ProcessedEmail.email_id == email_id,
                ProcessedEmail.account_id == account_id,
            )
            .first()
        )

        if not email:
            return None

        # Track the action
        return self.tracker.track_action(
            email_id=email.email_id,
            sender_email=email.sender,
            account_id=account_id,
            action_type=action_type,
            action_details=action_details,
            email_received_at=email.received_at,
            original_classification={
                "category": email.category,
                "confidence": email.confidence,
                "importance": email.importance_score,
            }
            if email.category
            else None,
        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_feedback_statistics(
        self, account_id: Optional[str] = None, days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Args:
            account_id: Optional account ID to filter by
            days_back: Number of days to look back

        Returns:
            Dictionary with statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)

        query = self.db.query(FeedbackEvent).filter(
            FeedbackEvent.action_taken_at >= cutoff_time
        )

        if account_id:
            query = query.filter(FeedbackEvent.account_id == account_id)

        events = query.all()

        # Count by action type
        by_action = {}
        for event in events:
            by_action[event.action_type] = by_action.get(event.action_type, 0) + 1

        # Count unique senders
        unique_senders = len(set(e.sender_email for e in events))

        return {
            "total_events": len(events),
            "unique_senders": unique_senders,
            "by_action_type": by_action,
            "days_back": days_back,
        }

    def print_feedback_summary(self, account_id: Optional[str] = None):
        """Print a summary of feedback activity."""
        stats = self.get_feedback_statistics(account_id, days_back=30)

        print("\n" + "=" * 70)
        print("FEEDBACK TRACKING SUMMARY (Last 30 Days)")
        print("=" * 70)
        print(f"Total Feedback Events: {stats['total_events']}")
        print(f"Unique Senders: {stats['unique_senders']}")
        print(f"\nActions by Type:")

        for action_type, count in sorted(
            stats["by_action_type"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {action_type:20s}: {count:>4}")

        print("=" * 70 + "\n")
