"""
Unit Tests: Attachment Service (Phase 4)

Tests attachment downloading, deduplication, and storage:
1. Service initialization
2. Downloading attachments (with mocked Gmail API)
3. SHA-256 deduplication
4. Size limit enforcement (25MB default)
5. Metadata storage in database
6. File path generation
7. Retrieval operations (by ID, by email, by account)
8. Error handling and failed downloads
"""

import pytest
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
import base64

from agent_platform.attachments import (
    AttachmentService,
    AttachmentInfo,
    AttachmentDownloadResult,
    AttachmentMetadata,
)
from agent_platform.db.database import get_db
from agent_platform.db.models import Attachment


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    service = MagicMock()

    # Mock the chain: users().messages().attachments().get().execute()
    mock_attachment_data = {
        'data': base64.urlsafe_b64encode(b'Test file content').decode('utf-8')
    }

    service.users().messages().attachments().get().execute.return_value = mock_attachment_data

    return service


@pytest.fixture
def sample_attachment_info():
    """Sample attachment metadata."""
    return AttachmentInfo(
        filename="test_document.pdf",
        size_bytes=1024 * 100,  # 100KB
        mime_type="application/pdf",
        attachment_id="gmail_attachment_123",
        inline=False,
    )


@pytest.fixture
def large_attachment_info():
    """Large attachment that exceeds size limit."""
    return AttachmentInfo(
        filename="large_file.zip",
        size_bytes=30 * 1024 * 1024,  # 30MB (exceeds 25MB default)
        mime_type="application/zip",
        attachment_id="gmail_attachment_456",
        inline=False,
    )


# ============================================================================
# TEST CASES: INITIALIZATION
# ============================================================================

class TestAttachmentServiceInitialization:
    """Test AttachmentService initialization and configuration."""

    def test_default_initialization(self, temp_storage_dir):
        """Test service initialization with default parameters."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        assert service.storage_dir == Path(temp_storage_dir)
        assert service.max_size_bytes == 25 * 1024 * 1024  # 25MB default
        assert service.enable_deduplication is True
        assert service.storage_dir.exists()

    def test_custom_size_limit(self, temp_storage_dir):
        """Test service initialization with custom size limit."""
        service = AttachmentService(
            storage_dir=temp_storage_dir,
            max_size_mb=10.0,
        )

        assert service.max_size_bytes == 10 * 1024 * 1024

    def test_deduplication_disabled(self, temp_storage_dir):
        """Test service initialization with deduplication disabled."""
        service = AttachmentService(
            storage_dir=temp_storage_dir,
            enable_deduplication=False,
        )

        assert service.enable_deduplication is False

    def test_storage_directory_created(self, temp_storage_dir):
        """Test that storage directory is created if it doesn't exist."""
        new_dir = Path(temp_storage_dir) / "new_attachments"
        assert not new_dir.exists()

        service = AttachmentService(storage_dir=str(new_dir))

        assert new_dir.exists()


# ============================================================================
# TEST CASES: DOWNLOADING ATTACHMENTS
# ============================================================================

class TestAttachmentDownload:
    """Test attachment download functionality."""

    @pytest.mark.asyncio
    async def test_successful_download(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test successful attachment download."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_123",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        assert result.success is True
        assert result.stored_path is not None
        assert result.file_hash is not None
        assert result.downloaded_at is not None
        assert result.deduplicated is False
        assert result.error is None

        # Verify file exists
        assert Path(result.stored_path).exists()

        # Verify database record
        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == result.attachment_id
            ).first()

            assert attachment is not None
            assert attachment.original_filename == "test_document.pdf"
            assert attachment.storage_status == "downloaded"
            assert attachment.file_hash == result.file_hash

    @pytest.mark.asyncio
    async def test_download_with_processed_email_id(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test download with processed_email_id foreign key."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_456",
            account_id="test_account",
            attachment_info=sample_attachment_info,
            processed_email_id=42,
        )

        assert result.success is True

        # Verify FK is stored
        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == result.attachment_id
            ).first()

            assert attachment.processed_email_id == 42

    @pytest.mark.asyncio
    async def test_download_multiple_attachments(
        self,
        temp_storage_dir,
        mock_gmail_service,
    ):
        """Test downloading multiple attachments for one email."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        attachments = [
            AttachmentInfo(
                filename=f"file_{i}.pdf",
                size_bytes=1024 * 50,
                mime_type="application/pdf",
                attachment_id=f"att_{i}",
            )
            for i in range(3)
        ]

        results = await service.download_email_attachments(
            gmail_service=mock_gmail_service,
            email_id="msg_multi",
            account_id="test_account",
            attachments=attachments,
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(Path(r.stored_path).exists() for r in results)


# ============================================================================
# TEST CASES: SHA-256 DEDUPLICATION
# ============================================================================

class TestDeduplication:
    """Test SHA-256 deduplication logic."""

    @pytest.mark.asyncio
    async def test_duplicate_attachment_same_account(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test that duplicate attachments reuse existing file."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        # Download first attachment
        result1 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_001",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        assert result1.success is True
        assert result1.deduplicated is False
        original_path = result1.stored_path

        # Download duplicate attachment (same content, different email)
        result2 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_002",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        assert result2.success is True
        assert result2.deduplicated is True
        assert result2.stored_path == original_path  # Same file
        assert result2.file_hash == result1.file_hash

        # Verify both records exist in database
        with get_db() as db:
            attachments = db.query(Attachment).filter(
                Attachment.file_hash == result1.file_hash
            ).all()

            assert len(attachments) == 2
            assert attachments[0].stored_path == attachments[1].stored_path

    @pytest.mark.asyncio
    async def test_no_deduplication_across_accounts(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test that deduplication is per-account (same hash, different accounts)."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        # Download for account 1
        result1 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_001",
            account_id="account_1",
            attachment_info=sample_attachment_info,
        )

        # Download for account 2 (same content)
        result2 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_002",
            account_id="account_2",
            attachment_info=sample_attachment_info,
        )

        # Should have same hash but different storage
        assert result1.file_hash == result2.file_hash
        assert result1.stored_path != result2.stored_path  # Different paths
        assert result2.deduplicated is False  # Not deduplicated across accounts

    @pytest.mark.asyncio
    async def test_deduplication_disabled(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test that deduplication can be disabled."""
        service = AttachmentService(
            storage_dir=temp_storage_dir,
            enable_deduplication=False,
        )

        # Download twice
        result1 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_001",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        result2 = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_002",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        # Both should download fully
        assert result1.deduplicated is False
        assert result2.deduplicated is False
        assert result1.stored_path != result2.stored_path

    def test_hash_computation(self, temp_storage_dir):
        """Test SHA-256 hash computation."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        test_data = b"Test file content"
        hash1 = service._compute_hash(test_data)
        hash2 = service._compute_hash(test_data)

        # Same data = same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex string

        # Different data = different hash
        hash3 = service._compute_hash(b"Different content")
        assert hash1 != hash3


# ============================================================================
# TEST CASES: SIZE LIMIT ENFORCEMENT
# ============================================================================

class TestSizeLimits:
    """Test file size limit enforcement."""

    @pytest.mark.asyncio
    async def test_skip_oversized_attachment(
        self,
        temp_storage_dir,
        mock_gmail_service,
        large_attachment_info,
    ):
        """Test that attachments exceeding size limit are skipped."""
        service = AttachmentService(
            storage_dir=temp_storage_dir,
            max_size_mb=25.0,
        )

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_large",
            account_id="test_account",
            attachment_info=large_attachment_info,
        )

        assert result.success is False
        assert result.skipped_reason == "too_large"
        assert result.stored_path is None

        # Verify database record shows skipped
        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == result.attachment_id
            ).first()

            assert attachment is not None
            assert attachment.storage_status == "skipped_too_large"
            assert attachment.stored_path is None

    @pytest.mark.asyncio
    async def test_custom_size_limit(
        self,
        temp_storage_dir,
        mock_gmail_service,
    ):
        """Test custom size limit."""
        service = AttachmentService(
            storage_dir=temp_storage_dir,
            max_size_mb=0.1,  # Only 100KB allowed
        )

        large_file = AttachmentInfo(
            filename="too_big.pdf",
            size_bytes=200 * 1024,  # 200KB
            mime_type="application/pdf",
            attachment_id="att_large",
        )

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_test",
            account_id="test_account",
            attachment_info=large_file,
        )

        assert result.success is False
        assert result.skipped_reason == "too_large"


# ============================================================================
# TEST CASES: FILE PATH GENERATION
# ============================================================================

class TestFilePathGeneration:
    """Test storage path generation logic."""

    def test_path_structure(self, temp_storage_dir):
        """Test that paths follow expected structure."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        path = service._get_storage_path(
            account_id="gmail_1",
            email_id="msg_123",
            filename="document.pdf",
            attachment_id="att_456",
        )

        # Should be: storage_dir/gmail_1/msg_123/att_456_document.pdf
        assert path.parent.parent.name == "gmail_1"
        assert path.parent.name == "msg_123"
        assert "att_456" in path.name
        assert "document.pdf" in path.name

    def test_filename_sanitization(self, temp_storage_dir):
        """Test that dangerous characters are removed from filenames."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        path = service._get_storage_path(
            account_id="gmail_1",
            email_id="msg_123",
            filename="../../etc/passwd",  # Path traversal attempt
            attachment_id="att_789",
        )

        # Should strip dangerous characters
        assert ".." not in path.name
        assert "/" not in path.name
        assert "att_789" in path.name

    def test_unique_filenames(self, temp_storage_dir):
        """Test that attachment_id ensures unique filenames."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        path1 = service._get_storage_path(
            account_id="gmail_1",
            email_id="msg_123",
            filename="report.pdf",
            attachment_id="att_001",
        )

        path2 = service._get_storage_path(
            account_id="gmail_1",
            email_id="msg_123",
            filename="report.pdf",  # Same filename
            attachment_id="att_002",  # Different ID
        )

        # Should have different paths due to different attachment_ids
        assert path1 != path2
        assert "att_001" in str(path1)
        assert "att_002" in str(path2)


# ============================================================================
# TEST CASES: RETRIEVAL OPERATIONS
# ============================================================================

class TestRetrievalOperations:
    """Test attachment retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_attachment_by_id(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test retrieving attachment by ID."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        # Download attachment
        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_123",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        # Retrieve by ID
        attachment = service.get_attachment_by_id(result.attachment_id)

        assert attachment is not None
        assert attachment.attachment_id == result.attachment_id
        assert attachment.original_filename == "test_document.pdf"
        assert attachment.storage_status == "downloaded"

    @pytest.mark.asyncio
    async def test_get_attachments_for_email(
        self,
        temp_storage_dir,
        mock_gmail_service,
    ):
        """Test retrieving all attachments for a specific email."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        # Download multiple attachments for same email
        for i in range(3):
            await service.download_attachment(
                gmail_service=mock_gmail_service,
                email_id="msg_multi",
                account_id="test_account",
                attachment_info=AttachmentInfo(
                    filename=f"file_{i}.pdf",
                    size_bytes=1024 * 50,
                    mime_type="application/pdf",
                    attachment_id=f"att_{i}",
                ),
            )

        # Retrieve all attachments for email
        attachments = service.get_attachments_for_email("msg_multi")

        assert len(attachments) == 3
        assert all(att.email_id == "msg_multi" for att in attachments)

    @pytest.mark.asyncio
    async def test_get_attachment_file_path(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test getting filesystem path for attachment."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_123",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        # Get file path
        file_path = service.get_attachment_file_path(result.attachment_id)

        assert file_path is not None
        assert file_path.exists()
        assert str(file_path) == result.stored_path

    def test_get_nonexistent_attachment(self, temp_storage_dir):
        """Test retrieving non-existent attachment."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        attachment = service.get_attachment_by_id("nonexistent_id")

        assert attachment is None


# ============================================================================
# TEST CASES: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test error handling and failed downloads."""

    @pytest.mark.asyncio
    async def test_gmail_api_error(self, temp_storage_dir, sample_attachment_info):
        """Test handling of Gmail API errors."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        # Mock Gmail service that raises error
        mock_service = MagicMock()
        mock_service.users().messages().attachments().get().execute.side_effect = Exception(
            "Gmail API error"
        )

        result = await service.download_attachment(
            gmail_service=mock_service,
            email_id="msg_error",
            account_id="test_account",
            attachment_info=sample_attachment_info,
        )

        assert result.success is False
        assert result.error is not None
        assert "Gmail API error" in result.error

        # Verify failed record in database
        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == result.attachment_id
            ).first()

            assert attachment is not None
            assert attachment.storage_status == "failed"

    @pytest.mark.asyncio
    async def test_missing_attachment_id(self, temp_storage_dir, mock_gmail_service):
        """Test handling of missing attachment_id."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        attachment_info = AttachmentInfo(
            filename="test.pdf",
            size_bytes=1024,
            mime_type="application/pdf",
            attachment_id=None,  # Missing
        )

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_test",
            account_id="test_account",
            attachment_info=attachment_info,
        )

        assert result.success is False
        assert result.error is not None


# ============================================================================
# TEST CASES: METADATA STORAGE
# ============================================================================

class TestMetadataStorage:
    """Test database metadata storage."""

    @pytest.mark.asyncio
    async def test_metadata_fields(
        self,
        temp_storage_dir,
        mock_gmail_service,
        sample_attachment_info,
    ):
        """Test that all metadata fields are stored correctly."""
        service = AttachmentService(storage_dir=temp_storage_dir)

        result = await service.download_attachment(
            gmail_service=mock_gmail_service,
            email_id="msg_123",
            account_id="gmail_1",
            attachment_info=sample_attachment_info,
        )

        with get_db() as db:
            attachment = db.query(Attachment).filter(
                Attachment.attachment_id == result.attachment_id
            ).first()

            # Verify all fields
            assert attachment.email_id == "msg_123"
            assert attachment.account_id == "gmail_1"
            assert attachment.original_filename == "test_document.pdf"
            assert attachment.file_size_bytes == 1024 * 100
            assert attachment.mime_type == "application/pdf"
            assert attachment.stored_path is not None
            assert attachment.storage_status == "downloaded"
            assert attachment.downloaded_at is not None
            assert attachment.file_hash is not None
            assert len(attachment.file_hash) == 64  # SHA-256


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
