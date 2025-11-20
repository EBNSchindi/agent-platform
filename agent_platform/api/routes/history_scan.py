"""
API Routes for History Scan operations
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional

from agent_platform.history_scan import (
    HistoryScanService,
    ScanConfig,
    ScanProgress,
    ScanStatus,
)
from agent_platform.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/history-scan", tags=["history-scan"])

# Singleton service instance (in production, use dependency injection)
_scan_service: Optional[HistoryScanService] = None


def get_scan_service() -> HistoryScanService:
    """Get or create scan service instance"""
    global _scan_service
    if _scan_service is None:
        _scan_service = HistoryScanService()
    return _scan_service


@router.post("/start", response_model=ScanProgress)
async def start_scan(
    config: ScanConfig,
    background_tasks: BackgroundTasks,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Start a new history scan

    Initiates a background scan of the Gmail account history with the provided configuration.

    **Parameters:**
    - account_id: Gmail account to scan
    - batch_size: Number of emails per batch (10-500, default 50)
    - max_results: Maximum emails to scan (None = all)
    - query: Gmail query filter (e.g., 'after:2023/01/01')
    - skip_already_processed: Skip emails already processed
    - process_attachments: Download attachments
    - process_threads: Generate thread summaries

    **Returns:**
    - ScanProgress object with scan_id and initial status
    """
    try:
        # Note: In a real implementation, we'd need to pass the gmail_service
        # For now, we return a mock response. Full integration requires Gmail OAuth.
        logger.info(f"Starting scan for account {config.account_id}")

        # In production, get gmail_service from auth system
        # gmail_service = get_gmail_service(config.account_id)
        # progress = await scan_service.start_scan(gmail_service, config)

        # For now, return mock progress
        from agent_platform.history_scan.models import ScanProgress
        import uuid
        from datetime import datetime

        progress = ScanProgress(
            scan_id=str(uuid.uuid4()),
            account_id=config.account_id,
            status=ScanStatus.IN_PROGRESS,
            total_found=0,
            processed=0,
            started_at=datetime.now(),
            last_updated_at=datetime.now(),
        )

        # Store in service
        scan_service._active_scans[progress.scan_id] = progress

        return progress

    except Exception as e:
        logger.error(f"Failed to start scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.get("/{scan_id}", response_model=ScanProgress)
async def get_scan_progress(
    scan_id: str,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Get progress of a specific scan

    **Parameters:**
    - scan_id: Unique scan identifier

    **Returns:**
    - ScanProgress with current status and statistics
    """
    progress = scan_service.get_scan_progress(scan_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return progress


@router.get("/", response_model=List[ScanProgress])
async def list_active_scans(
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    List all active scans

    **Returns:**
    - List of ScanProgress objects for all active/paused scans
    """
    return scan_service.list_active_scans()


@router.post("/{scan_id}/pause")
async def pause_scan(
    scan_id: str,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Pause an active scan

    **Parameters:**
    - scan_id: Unique scan identifier

    **Returns:**
    - Success message
    """
    success = await scan_service.pause_scan(scan_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause scan {scan_id} (not found or not in progress)",
        )

    return {"status": "paused", "scan_id": scan_id}


@router.post("/{scan_id}/resume")
async def resume_scan(
    scan_id: str,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Resume a paused scan

    **Parameters:**
    - scan_id: Unique scan identifier

    **Returns:**
    - Success message

    **Note:** Requires gmail_service to be passed (not implemented in mock)
    """
    # In production: gmail_service = get_gmail_service(account_id)
    # success = await scan_service.resume_scan(scan_id, gmail_service)

    # For now, mock implementation
    progress = scan_service.get_scan_progress(scan_id)
    if not progress or progress.status != ScanStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume scan {scan_id} (not found or not paused)",
        )

    progress.status = ScanStatus.IN_PROGRESS
    return {"status": "resumed", "scan_id": scan_id}


@router.post("/{scan_id}/cancel")
async def cancel_scan(
    scan_id: str,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Cancel an active or paused scan

    **Parameters:**
    - scan_id: Unique scan identifier

    **Returns:**
    - Success message
    """
    success = await scan_service.cancel_scan(scan_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return {"status": "cancelled", "scan_id": scan_id}


@router.get("/{scan_id}/stats")
async def get_scan_stats(
    scan_id: str,
    scan_service: HistoryScanService = Depends(get_scan_service),
):
    """
    Get detailed statistics for a scan

    **Parameters:**
    - scan_id: Unique scan identifier

    **Returns:**
    - Detailed statistics including breakdowns by category, confidence, etc.
    """
    progress = scan_service.get_scan_progress(scan_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    return {
        "scan_id": scan_id,
        "account_id": progress.account_id,
        "status": progress.status,
        "progress": {
            "total_found": progress.total_found,
            "processed": progress.processed,
            "skipped": progress.skipped,
            "failed": progress.failed,
            "percent": progress.progress_percent,
        },
        "classification": {
            "high": progress.classified_high,
            "medium": progress.classified_medium,
            "low": progress.classified_low,
        },
        "extraction": {
            "tasks": progress.tasks_extracted,
            "decisions": progress.decisions_extracted,
            "questions": progress.questions_extracted,
        },
        "resources": {
            "attachments": progress.attachments_downloaded,
            "threads": progress.threads_summarized,
        },
        "timing": {
            "started_at": progress.started_at,
            "last_updated_at": progress.last_updated_at,
            "completed_at": progress.completed_at,
            "estimated_completion": progress.estimated_completion,
        },
        "error": {
            "message": progress.error_message,
            "details": progress.error_details,
        } if progress.error_message else None,
    }
