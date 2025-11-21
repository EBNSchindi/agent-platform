"""
Gmail Provider Handler (Phase 7)

Handles Gmail-specific operations with multi-label support.

Gmail supports multiple labels per email, so we can apply:
- Primary category as main label
- Secondary categories (0-3) as additional labels

Example:
    Email about "Project meeting with invoice"
    → Primary: wichtig_todo
    → Secondary: [termine, finanzen]
    → Gmail Labels: wichtig_todo, termine, finanzen (all 3 applied)
"""

from typing import List, Dict, Any, Optional
import logging

from agent_platform.db.models import ProcessedEmail
from agent_platform.events import log_event, EventType


logger = logging.getLogger(__name__)


# Category to Gmail Label mapping
CATEGORY_TO_LABEL_MAP = {
    'wichtig_todo': 'Important/ToDo',
    'termine': 'Events/Appointments',
    'finanzen': 'Finance/Invoices',
    'bestellungen': 'Orders/Shipping',
    'job_projekte': 'Work/Projects',
    'vertraege': 'Contracts/Official',
    'persoenlich': 'Personal',
    'newsletter': 'Newsletter',
    'werbung': 'Marketing/Promo',
    'spam': 'SPAM',
}


class GmailHandler:
    """
    Gmail-specific email handler with multi-label support.

    Features:
    - Apply primary + secondary categories as Gmail labels
    - Create labels if they don't exist
    - Handle label conflicts
    - Archive low-importance emails
    """

    def __init__(self, gmail_service=None):
        """
        Initialize Gmail handler.

        Args:
            gmail_service: Google API service object (optional, for testing)
        """
        self.gmail_service = gmail_service
        self.label_cache = {}  # Cache label IDs to avoid repeated API calls

    async def apply_classification(
        self,
        email_record: ProcessedEmail,
        account_id: str,
        primary_category: str,
        secondary_categories: List[str],
        importance_score: float,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Apply classification to Gmail email with multi-label support.

        Args:
            email_record: ProcessedEmail database record
            account_id: Gmail account ID (gmail_1, gmail_2, etc.)
            primary_category: Primary category (wichtig_todo, termine, etc.)
            secondary_categories: List of secondary categories (0-3)
            importance_score: Importance score (0.0-1.0)
            confidence: Confidence score (0.0-1.0)

        Returns:
            Dict with:
            - labels_applied: List[str] - Labels that were applied
            - labels_created: List[str] - Labels that were created
            - archived: bool - Whether email was archived
            - success: bool - Whether operation succeeded
            - error: Optional[str] - Error message if failed
        """
        try:
            # Collect all categories to apply
            all_categories = [primary_category] + secondary_categories

            # Map categories to Gmail label names
            label_names = [
                CATEGORY_TO_LABEL_MAP.get(cat, cat)
                for cat in all_categories
            ]

            # Get or create label IDs
            label_ids, created_labels = await self._get_or_create_labels(
                account_id=account_id,
                label_names=label_names
            )

            # Apply labels to email
            applied_labels = await self._apply_labels(
                account_id=account_id,
                message_id=email_record.email_id,
                label_ids=label_ids
            )

            # Archive low-importance emails (importance < 0.4)
            archived = False
            if importance_score < 0.4:
                archived = await self._archive_email(
                    account_id=account_id,
                    message_id=email_record.email_id
                )

            # Update database record
            email_record.gmail_labels_applied = label_names

            # Log event
            log_event(
                event_type=EventType.EMAIL_CLASSIFIED,
                account_id=account_id,
                email_id=email_record.email_id,
                payload={
                    'provider': 'gmail',
                    'primary_category': primary_category,
                    'secondary_categories': secondary_categories,
                    'labels_applied': label_names,
                    'labels_created': created_labels,
                    'archived': archived,
                    'importance_score': importance_score,
                    'confidence': confidence
                }
            )

            return {
                'labels_applied': label_names,
                'labels_created': created_labels,
                'archived': archived,
                'success': True,
                'error': None
            }

        except Exception as e:
            logger.error(f"Gmail handler failed for {email_record.email_id}: {str(e)}")

            return {
                'labels_applied': [],
                'labels_created': [],
                'archived': False,
                'success': False,
                'error': str(e)
            }

    async def _get_or_create_labels(
        self,
        account_id: str,
        label_names: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Get or create Gmail labels.

        Args:
            account_id: Gmail account ID
            label_names: List of label names to get/create

        Returns:
            (label_ids, created_labels)
        """
        if not self.gmail_service:
            # Mock mode for testing
            logger.warning("Gmail service not configured - using mock mode")
            label_ids = [f"label_{name}" for name in label_names]
            return label_ids, []

        label_ids = []
        created_labels = []

        for label_name in label_names:
            # Check cache first
            cache_key = f"{account_id}:{label_name}"
            if cache_key in self.label_cache:
                label_ids.append(self.label_cache[cache_key])
                continue

            # Query existing labels
            try:
                results = self.gmail_service.users().labels().list(userId='me').execute()
                labels = results.get('labels', [])

                # Find matching label
                label_id = None
                for label in labels:
                    if label['name'] == label_name:
                        label_id = label['id']
                        break

                # Create label if not found
                if not label_id:
                    label_body = {
                        'name': label_name,
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show'
                    }
                    created = self.gmail_service.users().labels().create(
                        userId='me',
                        body=label_body
                    ).execute()

                    label_id = created['id']
                    created_labels.append(label_name)

                # Cache label ID
                self.label_cache[cache_key] = label_id
                label_ids.append(label_id)

            except Exception as e:
                logger.error(f"Failed to get/create label {label_name}: {str(e)}")
                continue

        return label_ids, created_labels

    async def _apply_labels(
        self,
        account_id: str,
        message_id: str,
        label_ids: List[str]
    ) -> List[str]:
        """
        Apply labels to Gmail message.

        Args:
            account_id: Gmail account ID
            message_id: Gmail message ID
            label_ids: List of label IDs to apply

        Returns:
            List of applied label IDs
        """
        if not self.gmail_service:
            # Mock mode
            logger.warning("Gmail service not configured - mock applying labels")
            return label_ids

        try:
            # Modify message with labels
            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()

            return label_ids

        except Exception as e:
            logger.error(f"Failed to apply labels to {message_id}: {str(e)}")
            return []

    async def _archive_email(
        self,
        account_id: str,
        message_id: str
    ) -> bool:
        """
        Archive Gmail email (remove from INBOX).

        Args:
            account_id: Gmail account ID
            message_id: Gmail message ID

        Returns:
            True if archived successfully
        """
        if not self.gmail_service:
            # Mock mode
            logger.warning("Gmail service not configured - mock archiving")
            return True

        try:
            # Remove INBOX label (= archive)
            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to archive {message_id}: {str(e)}")
            return False

    def get_label_mapping(self) -> Dict[str, str]:
        """
        Get category to Gmail label mapping.

        Returns:
            Dict mapping category names to Gmail label names
        """
        return CATEGORY_TO_LABEL_MAP.copy()
