"""
Review Handler

Handles user approval/rejection of review queue items and integrates
with the feedback tracking system to learn from user corrections.

When a user approves/rejects/modifies a classification:
1. Update review queue item status
2. Track feedback event
3. Update sender/domain preferences
4. Optionally apply action to email (label, archive, etc.)
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from agent_platform.db.models import ReviewQueueItem, ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.review.queue_manager import ReviewQueueManager
from agent_platform.feedback.tracker import FeedbackTracker, ActionType


class ReviewHandler:
    """
    Handles user review actions and integrates with feedback tracking.

    Workflow:
    1. User reviews email via digest
    2. User approves/rejects/modifies classification
    3. ReviewHandler:
       - Updates review queue status
       - Tracks feedback event
       - Updates preferences for learning
       - Optionally applies action to email
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize review handler.

        Args:
            db: Optional database session
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        self.queue_manager = ReviewQueueManager(db=self.db)
        self.feedback_tracker = FeedbackTracker(db=self.db)

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN REVIEW METHODS
    # ========================================================================

    def approve_classification(
        self,
        item_id: int,
        user_feedback: Optional[str] = None,
        apply_action: bool = False,
    ) -> Dict[str, Any]:
        """
        User approves the suggested classification.

        Args:
            item_id: Review queue item ID
            user_feedback: Optional user feedback text
            apply_action: Whether to apply action to email (label, archive, etc.)

        Returns:
            Dictionary with:
            - success: bool
            - item: Updated ReviewQueueItem
            - feedback_event: Created FeedbackEvent
            - action_applied: Optional action details
        """
        # Get item
        item = self.queue_manager.get_item_by_id(item_id)

        if not item:
            return {
                "success": False,
                "error": "Review item not found",
            }

        # Update review queue status
        updated_item = self.queue_manager.mark_as_reviewed(
            item_id=item_id,
            user_approved=True,
            user_feedback=user_feedback,
        )

        # Infer action type from approval
        # If user approved, it means they found it relevant enough to act on
        action_type = self._infer_action_from_approval(item)

        # Track feedback
        feedback_event = self.feedback_tracker.track_action(
            email_id=item.email_id,
            sender_email=item.sender,
            account_id=item.account_id,
            action_type=action_type,
            action_details={
                "review_item_id": item.id,
                "suggested_category": item.suggested_category,
                "user_approved": True,
            },
            original_classification={
                "category": item.suggested_category,
                "importance": item.importance_score,
                "confidence": item.confidence,
            },
        )

        result = {
            "success": True,
            "item": updated_item,
            "feedback_event": feedback_event,
        }

        # Optionally apply action to email
        if apply_action:
            action_result = self._apply_action_to_email(item)
            result["action_applied"] = action_result

        return result

    def reject_classification(
        self,
        item_id: int,
        corrected_category: Optional[str] = None,
        user_feedback: Optional[str] = None,
        apply_action: bool = False,
    ) -> Dict[str, Any]:
        """
        User rejects the suggested classification.

        Args:
            item_id: Review queue item ID
            corrected_category: Optional corrected category from user
            user_feedback: Optional user feedback text
            apply_action: Whether to apply corrected action to email

        Returns:
            Dictionary with:
            - success: bool
            - item: Updated ReviewQueueItem
            - feedback_event: Created FeedbackEvent
            - action_applied: Optional action details
        """
        # Get item
        item = self.queue_manager.get_item_by_id(item_id)

        if not item:
            return {
                "success": False,
                "error": "Review item not found",
            }

        # Update review queue status
        updated_item = self.queue_manager.mark_as_reviewed(
            item_id=item_id,
            user_approved=False,
            user_corrected_category=corrected_category,
            user_feedback=user_feedback,
        )

        # Infer action type from rejection
        # If user rejected, they likely don't want to see similar emails
        action_type = self._infer_action_from_rejection(item, corrected_category)

        # Track feedback
        feedback_event = self.feedback_tracker.track_action(
            email_id=item.email_id,
            sender_email=item.sender,
            account_id=item.account_id,
            action_type=action_type,
            action_details={
                "review_item_id": item.id,
                "suggested_category": item.suggested_category,
                "corrected_category": corrected_category,
                "user_approved": False,
            },
            original_classification={
                "category": item.suggested_category,
                "importance": item.importance_score,
                "confidence": item.confidence,
            },
        )

        result = {
            "success": True,
            "item": updated_item,
            "feedback_event": feedback_event,
        }

        # Optionally apply action to email
        if apply_action:
            action_result = self._apply_action_to_email(item, corrected_category)
            result["action_applied"] = action_result

        return result

    def modify_classification(
        self,
        item_id: int,
        corrected_category: str,
        user_feedback: Optional[str] = None,
        apply_action: bool = True,
    ) -> Dict[str, Any]:
        """
        User modifies the suggested classification.

        Args:
            item_id: Review queue item ID
            corrected_category: Corrected category from user
            user_feedback: Optional user feedback text
            apply_action: Whether to apply corrected action to email (default: True)

        Returns:
            Dictionary with:
            - success: bool
            - item: Updated ReviewQueueItem
            - feedback_event: Created FeedbackEvent
            - action_applied: Optional action details
        """
        # Get item
        item = self.queue_manager.get_item_by_id(item_id)

        if not item:
            return {
                "success": False,
                "error": "Review item not found",
            }

        # Update review queue status
        updated_item = self.queue_manager.mark_as_reviewed(
            item_id=item_id,
            user_approved=True,  # Modified is still approved
            user_corrected_category=corrected_category,
            user_feedback=user_feedback,
        )

        # Infer action type from corrected category
        action_type = self._infer_action_from_category(corrected_category)

        # Track feedback
        feedback_event = self.feedback_tracker.track_action(
            email_id=item.email_id,
            sender_email=item.sender,
            account_id=item.account_id,
            action_type=action_type,
            action_details={
                "review_item_id": item.id,
                "suggested_category": item.suggested_category,
                "corrected_category": corrected_category,
                "user_modified": True,
            },
            original_classification={
                "category": item.suggested_category,
                "importance": item.importance_score,
                "confidence": item.confidence,
            },
        )

        result = {
            "success": True,
            "item": updated_item,
            "feedback_event": feedback_event,
        }

        # Apply action to email with corrected category
        if apply_action:
            action_result = self._apply_action_to_email(item, corrected_category)
            result["action_applied"] = action_result

        return result

    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================

    def process_batch_reviews(
        self,
        reviews: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Process multiple review actions at once.

        Args:
            reviews: List of review actions, each with:
                - item_id: int
                - action: "approve" | "reject" | "modify"
                - corrected_category: Optional[str]
                - user_feedback: Optional[str]
                - apply_action: Optional[bool]

        Returns:
            Dictionary with:
            - total: Total reviews processed
            - successful: Number of successful reviews
            - failed: Number of failed reviews
            - results: List of individual results
        """
        results = []
        successful = 0
        failed = 0

        for review in reviews:
            item_id = review.get("item_id")
            action = review.get("action")
            corrected_category = review.get("corrected_category")
            user_feedback = review.get("user_feedback")
            apply_action = review.get("apply_action", False)

            try:
                if action == "approve":
                    result = self.approve_classification(
                        item_id=item_id,
                        user_feedback=user_feedback,
                        apply_action=apply_action,
                    )
                elif action == "reject":
                    result = self.reject_classification(
                        item_id=item_id,
                        corrected_category=corrected_category,
                        user_feedback=user_feedback,
                        apply_action=apply_action,
                    )
                elif action == "modify":
                    result = self.modify_classification(
                        item_id=item_id,
                        corrected_category=corrected_category,
                        user_feedback=user_feedback,
                        apply_action=apply_action,
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown action: {action}",
                    }

                if result.get("success"):
                    successful += 1
                else:
                    failed += 1

                results.append(result)

            except Exception as e:
                failed += 1
                results.append({
                    "success": False,
                    "error": str(e),
                    "item_id": item_id,
                })

        return {
            "total": len(reviews),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _infer_action_from_approval(self, item: ReviewQueueItem) -> ActionType:
        """
        Infer action type from user approval.

        If user approved the classification, we infer they found it relevant.
        Map category to likely action.
        """
        category = item.suggested_category

        # Map category to action type
        if category in ["wichtig", "action_required"]:
            # User likely replied or will reply
            return "replied"
        elif category == "newsletter":
            # User likely archived to read later
            return "archived"
        elif category == "nice_to_know":
            # User likely archived
            return "archived"
        elif category == "spam":
            # If user approved spam classification, they likely deleted it
            return "deleted"
        elif category == "system_notifications":
            # System notifications are typically archived
            return "archived"
        else:
            # Default to archived
            return "archived"

    def _infer_action_from_rejection(
        self,
        item: ReviewQueueItem,
        corrected_category: Optional[str],
    ) -> ActionType:
        """
        Infer action type from user rejection.

        If user rejected the classification, infer what they actually did.
        """
        # If they provided corrected category, use that
        if corrected_category:
            return self._infer_action_from_category(corrected_category)

        # Otherwise, infer based on what was suggested
        # If system said "wichtig" but user rejected, they likely archived it
        suggested = item.suggested_category

        if suggested in ["wichtig", "action_required"]:
            # User disagreed - likely archived without reply
            return "archived"
        elif suggested == "spam":
            # User disagreed with spam - likely archived as legit
            return "archived"
        elif suggested == "newsletter":
            # User disagreed - maybe deleted or marked spam
            return "deleted"
        else:
            # Default to archived
            return "archived"

    def _infer_action_from_category(self, category: str) -> ActionType:
        """Infer action type from category."""
        if category in ["wichtig", "action_required"]:
            return "replied"
        elif category == "spam":
            return "deleted"
        elif category == "newsletter":
            return "archived"
        else:
            return "archived"

    def _apply_action_to_email(
        self,
        item: ReviewQueueItem,
        corrected_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply action to the actual email (label, archive, etc.).

        This is a placeholder - actual implementation would use
        Gmail/IMAP tools to apply labels/move emails.

        Args:
            item: Review queue item
            corrected_category: Optional corrected category

        Returns:
            Dictionary with action details
        """
        # Determine category to apply
        category = corrected_category or item.suggested_category

        # This would integrate with email tools
        # Example pseudo-code:
        """
        if item.account_id.startswith("gmail_"):
            from modules.email.tools.gmail_tools import apply_label

            # Map category to label
            label_map = {
                "wichtig": "Important",
                "action_required": "Action Required",
                "newsletter": "Newsletters",
                "spam": "Spam",
                "nice_to_know": "Low Priority",
                "system_notifications": "System",
            }

            label = label_map.get(category, "Uncategorized")
            apply_label(item.account_id, item.email_id, label)
        """

        # Placeholder implementation
        return {
            "applied": False,
            "reason": "Email action application not yet implemented",
            "category": category,
            "email_id": item.email_id,
            "account_id": item.account_id,
        }

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_review_statistics(
        self,
        account_id: Optional[str] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get statistics about user reviews.

        Args:
            account_id: Optional account ID to filter by
            days_back: Number of days to look back

        Returns:
            Dictionary with statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = self.db.query(ReviewQueueItem).filter(
            ReviewQueueItem.reviewed_at >= cutoff_date
        )

        if account_id:
            query = query.filter(ReviewQueueItem.account_id == account_id)

        reviewed_items = query.all()

        # Calculate statistics
        total_reviewed = len(reviewed_items)
        approved = sum(1 for item in reviewed_items if item.user_approved is True)
        rejected = sum(1 for item in reviewed_items if item.user_approved is False)
        modified = sum(
            1 for item in reviewed_items
            if item.user_corrected_category and item.user_corrected_category != item.suggested_category
        )

        # Accuracy by category
        accuracy_by_category = {}
        for item in reviewed_items:
            category = item.suggested_category
            if category not in accuracy_by_category:
                accuracy_by_category[category] = {"total": 0, "correct": 0}

            accuracy_by_category[category]["total"] += 1

            # Correct if approved and not modified
            if item.user_approved and (
                not item.user_corrected_category
                or item.user_corrected_category == item.suggested_category
            ):
                accuracy_by_category[category]["correct"] += 1

        # Calculate accuracy percentages
        for category, stats in accuracy_by_category.items():
            stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0

        return {
            "total_reviewed": total_reviewed,
            "approved": approved,
            "rejected": rejected,
            "modified": modified,
            "approval_rate": approved / total_reviewed if total_reviewed > 0 else 0,
            "modification_rate": modified / total_reviewed if total_reviewed > 0 else 0,
            "accuracy_by_category": accuracy_by_category,
            "days_back": days_back,
        }

    def print_review_summary(self, account_id: Optional[str] = None):
        """Print a summary of review statistics."""
        stats = self.get_review_statistics(account_id, days_back=30)

        print("\n" + "=" * 70)
        print("REVIEW STATISTICS (Last 30 Days)")
        if account_id:
            print(f"Account: {account_id}")
        print("=" * 70)
        print(f"Total Reviewed: {stats['total_reviewed']}")
        print(f"\nStatus Breakdown:")
        print(f"  Approved...: {stats['approved']:>4} ({stats['approval_rate']:>6.1%})")
        print(f"  Rejected...: {stats['rejected']:>4}")
        print(f"  Modified...: {stats['modified']:>4} ({stats['modification_rate']:>6.1%})")

        if stats['accuracy_by_category']:
            print(f"\nAccuracy by Category:")
            for category, category_stats in sorted(
                stats['accuracy_by_category'].items(),
                key=lambda x: x[1]['accuracy'],
                reverse=True
            ):
                print(
                    f"  {category:20s}: {category_stats['accuracy']:>6.1%} "
                    f"({category_stats['correct']}/{category_stats['total']})"
                )

        print("=" * 70 + "\n")
