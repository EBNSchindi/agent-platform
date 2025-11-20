"""
Attachment Download and Storage Service
Handles downloading, deduplication, and storage of email attachments.
"""

import os
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from agent_platform.attachments.models import (
    AttachmentInfo,
    AttachmentDownloadResult,
    AttachmentMetadata,
)
from agent_platform.db.models import Attachment, ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.events import log_event, EventType

logger = logging.getLogger(__name__)


class AttachmentService:
    """
    Service for downloading and managing email attachments.

    Features:
    - Downloads attachments from Gmail API
    - Deduplication via SHA-256 hashing
    - Configurable size limits
    - Storage in organized directory structure
    - Database tracking
    """

    def __init__(
        self,
        storage_dir: str = "attachments",
        max_size_mb: float = 25.0,
        enable_deduplication: bool = True,
    ):
        """
        Initialize attachment service.

        Args:
            storage_dir: Base directory for storing attachments
            max_size_mb: Maximum file size in MB (default: 25MB)
            enable_deduplication: Whether to deduplicate files by hash
        """
        self.storage_dir = Path(storage_dir)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.enable_deduplication = enable_deduplication

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AttachmentService initialized: storage_dir={storage_dir}, max_size={max_size_mb}MB")

    def _compute_hash(self, file_data: bytes) -> str:
        """Compute SHA-256 hash of file data"""
        return hashlib.sha256(file_data).hexdigest()

    def _find_duplicate(self, file_hash: str, account_id: str) -> Optional[tuple]:
        """
        Find existing attachment with same hash in same account.

        Args:
            file_hash: SHA-256 hash of file
            account_id: Account ID

        Returns:
            Tuple of (attachment_id, stored_path) if found, None otherwise
        """
        if not self.enable_deduplication:
            return None

        with get_db() as db:
            result = db.query(Attachment).filter(
                Attachment.file_hash == file_hash,
                Attachment.account_id == account_id,
                Attachment.storage_status == 'downloaded'
            ).first()

            if result:
                # Extract values before session closes
                return (result.attachment_id, result.stored_path)
            return None

    def _get_storage_path(
        self,
        account_id: str,
        email_id: str,
        filename: str,
        attachment_id: str
    ) -> Path:
        """
        Generate organized storage path for attachment.

        Structure: attachments/{account_id}/{email_id}/{attachment_id}_{filename}

        Args:
            account_id: Account ID (e.g., gmail_1)
            email_id: Email message ID
            filename: Original filename
            attachment_id: Unique attachment ID

        Returns:
            Path object for storage location
        """
        # Sanitize filename (remove dangerous characters)
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        safe_filename = safe_filename.strip()

        # Remove path traversal patterns (consecutive dots)
        while ".." in safe_filename:
            safe_filename = safe_filename.replace("..", ".")

        # Create subdirectory structure
        email_dir = self.storage_dir / account_id / email_id
        email_dir.mkdir(parents=True, exist_ok=True)

        # Add attachment_id prefix to ensure uniqueness
        final_filename = f"{attachment_id}_{safe_filename}"

        return email_dir / final_filename

    async def download_attachment(
        self,
        gmail_service: Any,
        email_id: str,
        account_id: str,
        attachment_info: AttachmentInfo,
        processed_email_id: Optional[int] = None,
    ) -> AttachmentDownloadResult:
        """
        Download a single attachment from Gmail.

        Args:
            gmail_service: Gmail API service instance
            email_id: Gmail message ID
            account_id: Account ID (e.g., gmail_1)
            attachment_info: Attachment metadata
            processed_email_id: FK to processed_emails table

        Returns:
            AttachmentDownloadResult with success status and details
        """
        attachment_db_id = str(uuid.uuid4())

        try:
            # Check size limit
            if attachment_info.size_bytes > self.max_size_bytes:
                logger.warning(
                    f"Attachment too large: {attachment_info.filename} "
                    f"({attachment_info.size_formatted}) > {self.max_size_bytes / (1024 * 1024)}MB"
                )

                # Store metadata but mark as skipped
                with get_db() as db:
                    attachment_record = Attachment(
                        attachment_id=attachment_db_id,
                        email_id=email_id,
                        processed_email_id=processed_email_id,
                        account_id=account_id,
                        original_filename=attachment_info.filename,
                        file_size_bytes=attachment_info.size_bytes,
                        mime_type=attachment_info.mime_type,
                        storage_status='skipped_too_large',
                    )
                    db.add(attachment_record)

                log_event(
                    event_type=EventType.ATTACHMENT_SKIPPED,
                    account_id=account_id,
                    email_id=email_id,
                    payload={
                        'reason': 'too_large',
                        'size_bytes': attachment_info.size_bytes,
                        'max_size_bytes': self.max_size_bytes,
                        'filename': attachment_info.filename,
                    }
                )

                return AttachmentDownloadResult(
                    attachment_id=attachment_db_id,
                    success=False,
                    skipped_reason='too_large',
                )

            # Download from Gmail API
            if not attachment_info.attachment_id:
                raise ValueError("attachment_id is required for Gmail API download")

            attachment_data = gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=email_id,
                id=attachment_info.attachment_id,
            ).execute()

            import base64
            file_data = base64.urlsafe_b64decode(attachment_data['data'])

            # Compute hash for deduplication
            file_hash = self._compute_hash(file_data)

            # Check for duplicates
            duplicate = self._find_duplicate(file_hash, account_id)
            if duplicate:
                duplicate_id, duplicate_path = duplicate
                logger.info(
                    f"Attachment deduplicated: {attachment_info.filename} "
                    f"(hash={file_hash[:8]}..., existing={duplicate_id})"
                )

                # Create new record pointing to existing file
                with get_db() as db:
                    attachment_record = Attachment(
                        attachment_id=attachment_db_id,
                        email_id=email_id,
                        processed_email_id=processed_email_id,
                        account_id=account_id,
                        original_filename=attachment_info.filename,
                        file_size_bytes=attachment_info.size_bytes,
                        mime_type=attachment_info.mime_type,
                        stored_path=duplicate_path,  # Reuse existing path
                        storage_status='downloaded',
                        downloaded_at=datetime.utcnow(),
                        file_hash=file_hash,
                    )
                    db.add(attachment_record)

                log_event(
                    event_type=EventType.ATTACHMENT_DEDUPLICATED,
                    account_id=account_id,
                    email_id=email_id,
                    payload={
                        'filename': attachment_info.filename,
                        'file_hash': file_hash,
                        'existing_attachment_id': duplicate_id,
                    }
                )

                return AttachmentDownloadResult(
                    attachment_id=attachment_db_id,
                    success=True,
                    stored_path=duplicate_path,
                    file_hash=file_hash,
                    downloaded_at=datetime.utcnow(),
                    deduplicated=True,
                )

            # Store to filesystem
            storage_path = self._get_storage_path(
                account_id=account_id,
                email_id=email_id,
                filename=attachment_info.filename,
                attachment_id=attachment_db_id,
            )

            with open(storage_path, 'wb') as f:
                f.write(file_data)

            logger.info(
                f"Attachment downloaded: {attachment_info.filename} "
                f"({attachment_info.size_formatted}) -> {storage_path}"
            )

            # Store metadata in database
            with get_db() as db:
                attachment_record = Attachment(
                    attachment_id=attachment_db_id,
                    email_id=email_id,
                    processed_email_id=processed_email_id,
                    account_id=account_id,
                    original_filename=attachment_info.filename,
                    file_size_bytes=attachment_info.size_bytes,
                    mime_type=attachment_info.mime_type,
                    stored_path=str(storage_path),
                    storage_status='downloaded',
                    downloaded_at=datetime.utcnow(),
                    file_hash=file_hash,
                )
                db.add(attachment_record)

            log_event(
                event_type=EventType.ATTACHMENT_DOWNLOADED,
                account_id=account_id,
                email_id=email_id,
                payload={
                    'filename': attachment_info.filename,
                    'size_bytes': attachment_info.size_bytes,
                    'mime_type': attachment_info.mime_type,
                    'file_hash': file_hash,
                    'stored_path': str(storage_path),
                }
            )

            return AttachmentDownloadResult(
                attachment_id=attachment_db_id,
                success=True,
                stored_path=str(storage_path),
                file_hash=file_hash,
                downloaded_at=datetime.utcnow(),
                deduplicated=False,
            )

        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_info.filename}: {e}", exc_info=True)

            # Store failed record
            with get_db() as db:
                attachment_record = Attachment(
                    attachment_id=attachment_db_id,
                    email_id=email_id,
                    processed_email_id=processed_email_id,
                    account_id=account_id,
                    original_filename=attachment_info.filename,
                    file_size_bytes=attachment_info.size_bytes,
                    mime_type=attachment_info.mime_type,
                    storage_status='failed',
                    extra_metadata={'error': str(e)},
                )
                db.add(attachment_record)

            log_event(
                event_type=EventType.ATTACHMENT_DOWNLOAD_FAILED,
                account_id=account_id,
                email_id=email_id,
                payload={
                    'filename': attachment_info.filename,
                    'error': str(e),
                }
            )

            return AttachmentDownloadResult(
                attachment_id=attachment_db_id,
                success=False,
                error=str(e),
            )

    async def download_email_attachments(
        self,
        gmail_service: Any,
        email_id: str,
        account_id: str,
        attachments: List[AttachmentInfo],
        processed_email_id: Optional[int] = None,
    ) -> List[AttachmentDownloadResult]:
        """
        Download all attachments for an email.

        Args:
            gmail_service: Gmail API service instance
            email_id: Gmail message ID
            account_id: Account ID
            attachments: List of attachment info
            processed_email_id: FK to processed_emails table

        Returns:
            List of AttachmentDownloadResult
        """
        results = []

        for attachment_info in attachments:
            result = await self.download_attachment(
                gmail_service=gmail_service,
                email_id=email_id,
                account_id=account_id,
                attachment_info=attachment_info,
                processed_email_id=processed_email_id,
            )
            results.append(result)

        # Log summary
        successful = sum(1 for r in results if r.success)
        deduplicated = sum(1 for r in results if r.deduplicated)
        skipped = sum(1 for r in results if r.skipped_reason)
        failed = sum(1 for r in results if not r.success and not r.skipped_reason)

        logger.info(
            f"Email {email_id} attachments: "
            f"{successful} downloaded ({deduplicated} deduplicated), "
            f"{skipped} skipped, {failed} failed"
        )

        return results

    def get_attachments_for_email(
        self,
        email_id: str,
        account_id: Optional[str] = None,
    ) -> List[AttachmentMetadata]:
        """
        Get all attachments for a specific email.

        Args:
            email_id: Gmail message ID
            account_id: Optional account ID filter

        Returns:
            List of AttachmentMetadata
        """
        with get_db() as db:
            query = db.query(Attachment).filter(Attachment.email_id == email_id)

            if account_id:
                query = query.filter(Attachment.account_id == account_id)

            attachments = query.all()

            return [
                AttachmentMetadata.model_validate(att)
                for att in attachments
            ]

    def get_attachment_by_id(self, attachment_id: str) -> Optional[AttachmentMetadata]:
        """
        Get attachment metadata by ID.

        Args:
            attachment_id: Unique attachment ID

        Returns:
            AttachmentMetadata if found, None otherwise
        """
        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == attachment_id
            ).first()

            if attachment:
                return AttachmentMetadata.model_validate(attachment)
            return None

    def get_attachment_file_path(self, attachment_id: str) -> Optional[Path]:
        """
        Get filesystem path for attachment file.

        Args:
            attachment_id: Unique attachment ID

        Returns:
            Path object if attachment exists and is downloaded, None otherwise
        """
        attachment = self.get_attachment_by_id(attachment_id)

        if not attachment or not attachment.stored_path:
            return None

        if attachment.storage_status != 'downloaded':
            return None

        path = Path(attachment.stored_path)
        if not path.exists():
            logger.warning(f"Attachment file missing: {attachment.stored_path}")
            return None

        return path
