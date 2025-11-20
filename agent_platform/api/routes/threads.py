"""
Thread API Routes
REST API endpoints for email thread management and summarization.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from agent_platform.threads import ThreadService
from agent_platform.threads.models import ThreadSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/threads", tags=["threads"])

# Initialize service
thread_service = ThreadService()


@router.get("/{thread_id}/summary", response_model=ThreadSummary)
async def get_thread_summary(
    thread_id: str,
    account_id: str = Query(..., description="Account ID (e.g., gmail_1)"),
    force_regenerate: bool = Query(False, description="Force regenerate summary even if exists"),
):
    """
    Get or generate thread summary.

    **Parameters:**
    - thread_id: Gmail thread ID
    - account_id: Account ID (gmail_1, gmail_2, etc.)
    - force_regenerate: If true, regenerate summary using LLM even if one exists

    **Returns:**
    - ThreadSummary with LLM-generated summary, key points, and email list
    """
    try:
        summary = await thread_service.summarize_thread(
            thread_id=thread_id,
            account_id=account_id,
            force_regenerate=force_regenerate,
        )

        return summary

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get thread summary {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/emails")
async def get_thread_emails(
    thread_id: str,
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
):
    """
    Get all emails in a thread (without summary generation).

    **Parameters:**
    - thread_id: Gmail thread ID
    - account_id: Optional account ID filter

    **Returns:**
    - List of email metadata in chronological order
    """
    try:
        emails = thread_service.get_thread_emails(
            thread_id=thread_id,
            account_id=account_id,
        )

        if not emails:
            raise HTTPException(status_code=404, detail=f"No emails found for thread {thread_id}")

        # Convert to dict for JSON response
        return {
            "thread_id": thread_id,
            "email_count": len(emails),
            "emails": [
                {
                    "email_id": email.email_id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "received_at": email.received_at,
                    "category": email.category,
                    "thread_position": email.thread_position,
                    "is_thread_start": email.is_thread_start,
                }
                for email in emails
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread emails {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
