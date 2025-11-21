"""
IONOS Provider Handler (Phase 7)

Handles IONOS-specific operations with single-folder support.

IONOS (IMAP) only supports moving emails to ONE folder at a time, so we only use:
- Primary category → Single IMAP folder

Secondary categories are stored in DB but NOT applied to IMAP.

Example:
    Email about "Project meeting with invoice"
    → Primary: wichtig_todo
    → Secondary: [termine, finanzen] (stored in DB only)
    → IONOS Folder: Important/ToDo (only primary applied)
"""

from typing import List, Dict, Any, Optional
import logging
import imaplib

from agent_platform.db.models import ProcessedEmail
from agent_platform.events import log_event, EventType


logger = logging.getLogger(__name__)


# Category to IMAP Folder mapping
CATEGORY_TO_FOLDER_MAP = {
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


class IonosHandler:
    """
    IONOS-specific email handler with single-folder support.

    Features:
    - Move email to folder based on PRIMARY category only
    - Secondary categories stored in DB but NOT applied to IMAP
    - Create folders if they don't exist
    - Handle folder conflicts
    """

    def __init__(self, imap_connection=None):
        """
        Initialize IONOS handler.

        Args:
            imap_connection: IMAP connection object (optional, for testing)
        """
        self.imap_connection = imap_connection
        self.folder_cache = set()  # Cache existing folders

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
        Apply classification to IONOS email with single-folder support.

        Args:
            email_record: ProcessedEmail database record
            account_id: IONOS account ID (ionos_1, ionos_2, etc.)
            primary_category: Primary category (wichtig_todo, termine, etc.)
            secondary_categories: List of secondary categories (stored in DB only)
            importance_score: Importance score (0.0-1.0)
            confidence: Confidence score (0.0-1.0)

        Returns:
            Dict with:
            - folder_applied: str - Folder that was applied
            - folder_created: bool - Whether folder was created
            - secondary_ignored: List[str] - Secondary categories (not applied)
            - moved: bool - Whether email was moved
            - success: bool - Whether operation succeeded
            - error: Optional[str] - Error message if failed
        """
        try:
            # Map primary category to IMAP folder
            folder_name = CATEGORY_TO_FOLDER_MAP.get(primary_category, primary_category)

            # Create folder if doesn't exist
            folder_created = await self._create_folder_if_needed(
                account_id=account_id,
                folder_name=folder_name
            )

            # Move email to folder
            moved = await self._move_to_folder(
                account_id=account_id,
                message_id=email_record.email_id,
                folder_name=folder_name
            )

            # Update database record
            email_record.ionos_folder_applied = folder_name

            # Log event
            log_event(
                event_type=EventType.EMAIL_CLASSIFIED,
                account_id=account_id,
                email_id=email_record.email_id,
                payload={
                    'provider': 'ionos',
                    'primary_category': primary_category,
                    'secondary_categories': secondary_categories,
                    'folder_applied': folder_name,
                    'folder_created': folder_created,
                    'secondary_ignored': secondary_categories,  # IMAP doesn't support multi-folder
                    'moved': moved,
                    'importance_score': importance_score,
                    'confidence': confidence
                }
            )

            return {
                'folder_applied': folder_name,
                'folder_created': folder_created,
                'secondary_ignored': secondary_categories,
                'moved': moved,
                'success': True,
                'error': None
            }

        except Exception as e:
            logger.error(f"IONOS handler failed for {email_record.email_id}: {str(e)}")

            return {
                'folder_applied': None,
                'folder_created': False,
                'secondary_ignored': secondary_categories,
                'moved': False,
                'success': False,
                'error': str(e)
            }

    async def _create_folder_if_needed(
        self,
        account_id: str,
        folder_name: str
    ) -> bool:
        """
        Create IMAP folder if it doesn't exist.

        Args:
            account_id: IONOS account ID
            folder_name: Folder name to create

        Returns:
            True if folder was created, False if already existed
        """
        if not self.imap_connection:
            # Mock mode for testing
            logger.warning("IMAP connection not configured - using mock mode")
            return False

        # Check cache first
        if folder_name in self.folder_cache:
            return False

        try:
            # List existing folders
            status, folders = self.imap_connection.list()

            if status != 'OK':
                logger.error(f"Failed to list IMAP folders: {status}")
                return False

            # Parse folder names
            existing_folders = set()
            for folder in folders:
                # Parse folder name from IMAP LIST response
                # Format: (\\Flags) "/" "FolderName"
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    existing_folders.add(parts[-2])

            # Check if folder exists
            if folder_name in existing_folders:
                self.folder_cache.add(folder_name)
                return False

            # Create folder
            status, result = self.imap_connection.create(folder_name)

            if status != 'OK':
                logger.error(f"Failed to create folder {folder_name}: {status}")
                return False

            # Add to cache
            self.folder_cache.add(folder_name)
            return True

        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {str(e)}")
            return False

    async def _move_to_folder(
        self,
        account_id: str,
        message_id: str,
        folder_name: str
    ) -> bool:
        """
        Move email to IMAP folder.

        Args:
            account_id: IONOS account ID
            message_id: Email message ID (UID)
            folder_name: Target folder name

        Returns:
            True if moved successfully
        """
        if not self.imap_connection:
            # Mock mode
            logger.warning("IMAP connection not configured - mock moving email")
            return True

        try:
            # Copy message to target folder
            status, result = self.imap_connection.uid('COPY', message_id, folder_name)

            if status != 'OK':
                logger.error(f"Failed to copy {message_id} to {folder_name}: {status}")
                return False

            # Mark original as deleted
            status, result = self.imap_connection.uid('STORE', message_id, '+FLAGS', '(\\Deleted)')

            if status != 'OK':
                logger.error(f"Failed to delete original {message_id}: {status}")
                return False

            # Expunge deleted messages
            self.imap_connection.expunge()

            return True

        except Exception as e:
            logger.error(f"Failed to move {message_id} to {folder_name}: {str(e)}")
            return False

    def get_folder_mapping(self) -> Dict[str, str]:
        """
        Get category to IMAP folder mapping.

        Returns:
            Dict mapping category names to IMAP folder names
        """
        return CATEGORY_TO_FOLDER_MAP.copy()
