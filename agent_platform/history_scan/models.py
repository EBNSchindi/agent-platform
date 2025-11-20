"""
Pydantic models for History Scan system
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    """Status of a history scan"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanConfig(BaseModel):
    """Configuration for a history scan"""
    account_id: str = Field(..., description="Gmail account ID to scan")
    batch_size: int = Field(default=50, ge=10, le=500, description="Number of emails per batch")
    max_results: Optional[int] = Field(default=None, description="Maximum emails to scan (None = all)")
    query: str = Field(default="", description="Gmail query filter (e.g., 'after:2023/01/01')")
    skip_already_processed: bool = Field(default=True, description="Skip emails already in processed_emails table")
    process_attachments: bool = Field(default=True, description="Download and process attachments")
    process_threads: bool = Field(default=True, description="Generate thread summaries")


class ScanProgress(BaseModel):
    """Progress tracking for a history scan"""
    scan_id: str = Field(..., description="Unique scan ID")
    account_id: str = Field(..., description="Account being scanned")
    status: ScanStatus = Field(..., description="Current scan status")

    # Progress counters
    total_found: int = Field(default=0, description="Total emails found in Gmail")
    processed: int = Field(default=0, description="Emails processed so far")
    skipped: int = Field(default=0, description="Emails skipped (already processed)")
    failed: int = Field(default=0, description="Emails that failed processing")

    # Classification breakdown
    classified_high: int = Field(default=0, description="High confidence classifications")
    classified_medium: int = Field(default=0, description="Medium confidence classifications")
    classified_low: int = Field(default=0, description="Low confidence classifications")

    # Extraction stats
    tasks_extracted: int = Field(default=0, description="Total tasks extracted")
    decisions_extracted: int = Field(default=0, description="Total decisions extracted")
    questions_extracted: int = Field(default=0, description="Total questions extracted")

    # Attachment & thread stats
    attachments_downloaded: int = Field(default=0, description="Attachments downloaded")
    threads_summarized: int = Field(default=0, description="Threads summarized")

    # Timing
    started_at: datetime = Field(default_factory=datetime.now, description="Scan start time")
    last_updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    completed_at: Optional[datetime] = Field(default=None, description="Scan completion time")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")

    # Resume capability
    last_processed_email_id: Optional[str] = Field(default=None, description="Last email ID processed (for resume)")
    next_page_token: Optional[str] = Field(default=None, description="Gmail API page token (for resume)")

    # Error tracking
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed error info")

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_found == 0:
            return 0.0
        return (self.processed / self.total_found) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate (excluding skipped)"""
        attempted = self.processed - self.skipped
        if attempted == 0:
            return 100.0
        successful = attempted - self.failed
        return (successful / attempted) * 100


class ScanResult(BaseModel):
    """Result of a completed scan"""
    scan_id: str
    account_id: str
    status: ScanStatus

    # Summary stats
    total_processed: int
    total_skipped: int
    total_failed: int

    # Time taken
    duration_seconds: float
    emails_per_second: float

    # Classification summary
    high_confidence: int
    medium_confidence: int
    low_confidence: int

    # Extraction summary
    total_tasks: int
    total_decisions: int
    total_questions: int

    # Attachment & thread summary
    total_attachments: int
    total_threads: int

    # Error summary
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors encountered")


class ScanCheckpoint(BaseModel):
    """Checkpoint for resuming a scan"""
    scan_id: str
    account_id: str
    batch_number: int
    last_email_id: str
    next_page_token: Optional[str] = None
    processed_count: int
    created_at: datetime = Field(default_factory=datetime.now)
