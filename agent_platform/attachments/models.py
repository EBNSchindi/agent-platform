"""
Pydantic models for attachment handling
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AttachmentInfo(BaseModel):
    """Information about an email attachment"""
    filename: str = Field(..., description="Original filename from email")
    size_bytes: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type (e.g., application/pdf)")
    attachment_id: Optional[str] = Field(None, description="Gmail attachment ID")
    inline: bool = Field(False, description="True if inline/embedded image")

    @property
    def size_mb(self) -> float:
        """Return size in megabytes"""
        return self.size_bytes / (1024 * 1024)

    @property
    def size_formatted(self) -> str:
        """Return human-readable size"""
        if self.size_bytes < 1024:
            return f"{self.size_bytes}B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f}KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f}GB"


class AttachmentDownloadResult(BaseModel):
    """Result of downloading an attachment"""
    attachment_id: str = Field(..., description="Unique attachment ID")
    success: bool = Field(..., description="True if download succeeded")
    stored_path: Optional[str] = Field(None, description="Local filesystem path")
    file_hash: Optional[str] = Field(None, description="SHA-256 hash of file")
    error: Optional[str] = Field(None, description="Error message if failed")
    skipped_reason: Optional[str] = Field(None, description="Reason for skipping (e.g., 'too_large')")
    downloaded_at: Optional[datetime] = Field(None, description="Timestamp of download")
    deduplicated: bool = Field(False, description="True if file already existed (deduplicated)")


class AttachmentMetadata(BaseModel):
    """Full metadata for stored attachment (database model representation)"""
    id: int
    attachment_id: str
    email_id: str
    account_id: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    stored_path: Optional[str]
    storage_status: str  # pending, downloaded, failed, skipped_too_large
    downloaded_at: Optional[datetime]
    file_hash: Optional[str]
    extracted_text: Optional[str]
    extraction_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentListResponse(BaseModel):
    """Response for listing attachments"""
    total: int
    items: List[AttachmentMetadata]
    account_id: Optional[str] = None
    email_id: Optional[str] = None
