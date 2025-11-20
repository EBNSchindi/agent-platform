"""
Attachment API Routes
REST API endpoints for attachment management.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
import logging

from agent_platform.attachments import AttachmentService
from agent_platform.attachments.models import AttachmentMetadata, AttachmentListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])

# Initialize service
attachment_service = AttachmentService()


@router.get("", response_model=AttachmentListResponse)
async def list_attachments(
    email_id: Optional[str] = Query(None, description="Filter by email ID"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List attachments with optional filters.

    **Filters:**
    - email_id: Get attachments for specific email
    - account_id: Get attachments for specific account

    **Pagination:**
    - limit: Max items per page (1-200, default: 50)
    - offset: Skip N items (default: 0)
    """
    try:
        if email_id:
            attachments = attachment_service.get_attachments_for_email(
                email_id=email_id,
                account_id=account_id,
            )
        else:
            # Get all attachments (with pagination)
            # TODO: Implement full listing with pagination
            attachments = []

        # Apply pagination
        total = len(attachments)
        paginated_attachments = attachments[offset:offset + limit]

        return AttachmentListResponse(
            total=total,
            items=paginated_attachments,
            account_id=account_id,
            email_id=email_id,
        )

    except Exception as e:
        logger.error(f"Failed to list attachments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{attachment_id}", response_model=AttachmentMetadata)
async def get_attachment(attachment_id: str):
    """
    Get attachment metadata by ID.
    """
    try:
        attachment = attachment_service.get_attachment_by_id(attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        return attachment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attachment {attachment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{attachment_id}/download")
async def download_attachment(attachment_id: str):
    """
    Download attachment file.

    Returns the actual file with appropriate Content-Type and Content-Disposition headers.
    """
    try:
        # Get attachment metadata
        attachment = attachment_service.get_attachment_by_id(attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        if attachment.storage_status != 'downloaded':
            raise HTTPException(
                status_code=400,
                detail=f"Attachment not available for download (status: {attachment.storage_status})"
            )

        # Get file path
        file_path = attachment_service.get_attachment_file_path(attachment_id)

        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Attachment file not found on disk")

        # Return file
        return FileResponse(
            path=str(file_path),
            media_type=attachment.mime_type,
            filename=attachment.original_filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download attachment {attachment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
