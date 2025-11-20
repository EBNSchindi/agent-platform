"""
Attachment Management System
Handles downloading, storage, and retrieval of email attachments.
"""

from agent_platform.attachments.attachment_service import AttachmentService
from agent_platform.attachments.models import (
    AttachmentInfo,
    AttachmentDownloadResult,
    AttachmentMetadata,
    AttachmentListResponse,
)

__all__ = [
    'AttachmentService',
    'AttachmentInfo',
    'AttachmentDownloadResult',
    'AttachmentMetadata',
    'AttachmentListResponse',
]
