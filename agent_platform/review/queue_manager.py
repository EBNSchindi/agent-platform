"""
Review Queue Manager

Manages items in the review queue - adding medium-confidence classifications,
retrieving pending reviews, and cleaning up old items.

This is used by the classification system to route emails that need human review
(confidence between 0.6 and 0.85).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from agent_platform.db.models import ReviewQueueItem, ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.classification.models import ClassificationResult


class ReviewQueueManager:
    """
    Manages the review queue for medium-confidence email classifications.

    Responsibilities:
    - Add emails to review queue when confidence is medium (0.6-0.85)
    - Retrieve pending items for review
    - Update review status
    - Clean up old reviewed items
    """

    # Configuration
    DEFAULT_CONFIDENCE_THRESHOLD_MIN = 0.6
    DEFAULT_CONFIDENCE_THRESHOLD_MAX = 0.85
    MAX_ITEMS_PER_DIGEST = 20
    DAYS_TO_KEEP_REVIEWED = 30  # Keep reviewed items for 30 days

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize review queue manager.

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
    # ADDING TO QUEUE
    # ========================================================================

    def add_to_queue(
        self,
        email_id: str,
        account_id: str,
        subject: str,
        sender: str,
        snippet: str,
        classification: ClassificationResult,
        processed_email_id: Optional[int] = None,
    ) -> ReviewQueueItem:
        """
        Add an email to the review queue.

        Args:
            email_id: Email identifier
            account_id: Account ID (e.g., gmail_1)
            subject: Email subject
            sender: Sender email address
            snippet: Email preview/snippet
            classification: Classification result from system
            processed_email_id: Optional ID of ProcessedEmail record

        Returns:
            Created ReviewQueueItem
        """
        # Create review queue item
        queue_item = ReviewQueueItem(
            account_id=account_id,
            email_id=email_id,
            processed_email_id=processed_email_id,
            subject=subject,
            sender=sender,
            snippet=snippet,
            suggested_category=classification.category,
            importance_score=classification.importance,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            status="pending",
            extra_metadata={
                "layer_used": classification.layer_used,
                "added_by": "classification_system",
            }
        )

        self.db.add(queue_item)
        self.db.commit()

        return queue_item

    def should_add_to_review_queue(
        self,
        classification: ClassificationResult,
        min_threshold: Optional[float] = None,
        max_threshold: Optional[float] = None,
    ) -> bool:
        """
        Check if a classification should be added to review queue.

        Args:
            classification: Classification result
            min_threshold: Minimum confidence threshold (default: 0.6)
            max_threshold: Maximum confidence threshold (default: 0.85)

        Returns:
            True if should be added to queue
        """
        min_threshold = min_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD_MIN
        max_threshold = max_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD_MAX

        return min_threshold <= classification.confidence < max_threshold

    # ========================================================================
    # RETRIEVING FROM QUEUE
    # ========================================================================

    def get_pending_items(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ReviewQueueItem]:
        """
        Get pending review items.

        Args:
            account_id: Optional account ID to filter by
            limit: Maximum number of items to return

        Returns:
            List of pending ReviewQueueItems
        """
        query = self.db.query(ReviewQueueItem).filter(
            ReviewQueueItem.status == "pending"
        )

        if account_id:
            query = query.filter(ReviewQueueItem.account_id == account_id)

        # Order by importance (descending) and then by time added
        query = query.order_by(
            ReviewQueueItem.importance_score.desc(),
            ReviewQueueItem.added_to_queue_at.asc()
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_items_for_digest(
        self,
        account_id: Optional[str] = None,
        hours_back: int = 24,
        limit: Optional[int] = None,
    ) -> List[ReviewQueueItem]:
        """
        Get items for daily digest email.

        Args:
            account_id: Optional account ID to filter by
            hours_back: Only include items from last N hours (default: 24)
            limit: Maximum number of items (default: MAX_ITEMS_PER_DIGEST)

        Returns:
            List of ReviewQueueItems for digest
        """
        limit = limit or self.MAX_ITEMS_PER_DIGEST

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        query = self.db.query(ReviewQueueItem).filter(
            ReviewQueueItem.status == "pending",
            ReviewQueueItem.added_to_queue_at >= cutoff_time,
        )

        if account_id:
            query = query.filter(ReviewQueueItem.account_id == account_id)

        # Order by importance (descending)
        query = query.order_by(
            ReviewQueueItem.importance_score.desc(),
            ReviewQueueItem.added_to_queue_at.desc()
        )

        return query.limit(limit).all()

    def get_item_by_id(self, item_id: int) -> Optional[ReviewQueueItem]:
        """Get a specific review queue item by ID."""
        return self.db.query(ReviewQueueItem).filter(
            ReviewQueueItem.id == item_id
        ).first()

    # ========================================================================
    # UPDATING STATUS
    # ========================================================================

    def mark_as_reviewed(
        self,
        item_id: int,
        user_approved: bool,
        user_corrected_category: Optional[str] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[ReviewQueueItem]:
        """
        Mark an item as reviewed by user.

        Args:
            item_id: Review queue item ID
            user_approved: True if user approved, False if rejected
            user_corrected_category: Optional corrected category
            user_feedback: Optional user feedback text

        Returns:
            Updated ReviewQueueItem or None if not found
        """
        item = self.get_item_by_id(item_id)

        if not item:
            return None

        # Determine status
        if user_corrected_category and user_corrected_category != item.suggested_category:
            status = "modified"
        elif user_approved:
            status = "approved"
        else:
            status = "rejected"

        # Update item
        item.status = status
        item.user_approved = user_approved
        item.user_corrected_category = user_corrected_category
        item.user_feedback = user_feedback
        item.reviewed_at = datetime.utcnow()

        self.db.commit()

        return item

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_queue_statistics(
        self,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about the review queue.

        Args:
            account_id: Optional account ID to filter by

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(ReviewQueueItem)

        if account_id:
            query = query.filter(ReviewQueueItem.account_id == account_id)

        all_items = query.all()

        # Count by status
        pending_count = sum(1 for item in all_items if item.status == "pending")
        approved_count = sum(1 for item in all_items if item.status == "approved")
        rejected_count = sum(1 for item in all_items if item.status == "rejected")
        modified_count = sum(1 for item in all_items if item.status == "modified")

        # Count by category (for pending items)
        pending_items = [item for item in all_items if item.status == "pending"]
        by_category = {}
        for item in pending_items:
            by_category[item.suggested_category] = by_category.get(item.suggested_category, 0) + 1

        # Average age of pending items
        if pending_items:
            avg_age_hours = sum(
                (datetime.utcnow() - item.added_to_queue_at).total_seconds() / 3600
                for item in pending_items
            ) / len(pending_items)
        else:
            avg_age_hours = 0

        return {
            "total_items": len(all_items),
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "modified": modified_count,
            "by_category": by_category,
            "avg_age_hours": avg_age_hours,
        }

    def print_queue_summary(self, account_id: Optional[str] = None):
        """Print a summary of the review queue."""
        stats = self.get_queue_statistics(account_id)

        print("\n" + "=" * 70)
        print("REVIEW QUEUE SUMMARY")
        if account_id:
            print(f"Account: {account_id}")
        print("=" * 70)
        print(f"Total Items: {stats['total_items']}")
        print(f"\nStatus Breakdown:")
        print(f"  Pending....: {stats['pending']:>4}")
        print(f"  Approved...: {stats['approved']:>4}")
        print(f"  Rejected...: {stats['rejected']:>4}")
        print(f"  Modified...: {stats['modified']:>4}")

        if stats['by_category']:
            print(f"\nPending Items by Category:")
            for category, count in sorted(
                stats['by_category'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  {category:20s}: {count:>4}")

        if stats['pending'] > 0:
            print(f"\nAverage Age of Pending Items: {stats['avg_age_hours']:.1f} hours")

        print("=" * 70 + "\n")

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup_old_reviewed_items(
        self,
        days_to_keep: Optional[int] = None,
    ) -> int:
        """
        Delete old reviewed items to keep database clean.

        Args:
            days_to_keep: Days to keep reviewed items (default: DAYS_TO_KEEP_REVIEWED)

        Returns:
            Number of items deleted
        """
        days_to_keep = days_to_keep or self.DAYS_TO_KEEP_REVIEWED
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Delete items that are reviewed and older than cutoff
        deleted_count = self.db.query(ReviewQueueItem).filter(
            ReviewQueueItem.status.in_(["approved", "rejected", "modified"]),
            ReviewQueueItem.reviewed_at < cutoff_date,
        ).delete()

        self.db.commit()

        return deleted_count
