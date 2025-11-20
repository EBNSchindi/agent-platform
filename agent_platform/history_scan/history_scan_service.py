"""
History Scan Service - Batch processing of historical Gmail emails

This service scans a Gmail account's history and processes emails through the
classification and extraction pipeline. It supports:
- Batch processing to avoid memory/rate limit issues
- Resume capability via checkpoints
- Progress tracking
- Configurable filters and batch sizes
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncIterator
from googleapiclient.discovery import Resource

from agent_platform.history_scan.models import (
    ScanConfig,
    ScanProgress,
    ScanResult,
    ScanStatus,
    ScanCheckpoint,
)
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail
from agent_platform.events import log_event, EventType
from agent_platform.core.logger import get_logger

logger = get_logger(__name__)


class HistoryScanService:
    """Service for scanning historical emails from Gmail"""

    def __init__(self, orchestrator: Optional[ClassificationOrchestrator] = None):
        """
        Initialize history scan service

        Args:
            orchestrator: Classification orchestrator (creates new if None)
        """
        self.orchestrator = orchestrator or ClassificationOrchestrator()
        self._active_scans: Dict[str, ScanProgress] = {}

    def get_scan_progress(self, scan_id: str) -> Optional[ScanProgress]:
        """Get progress of an active scan"""
        return self._active_scans.get(scan_id)

    def list_active_scans(self) -> List[ScanProgress]:
        """List all active scans"""
        return list(self._active_scans.values())

    async def start_scan(
        self,
        gmail_service: Resource,
        config: ScanConfig,
        resume_from: Optional[str] = None,
    ) -> ScanProgress:
        """
        Start a new history scan

        Args:
            gmail_service: Gmail API service object
            config: Scan configuration
            resume_from: Optional scan_id to resume from

        Returns:
            ScanProgress object
        """
        # Create or resume scan
        if resume_from and resume_from in self._active_scans:
            progress = self._active_scans[resume_from]
            progress.status = ScanStatus.IN_PROGRESS
            logger.info(f"Resuming scan {resume_from} from email {progress.last_processed_email_id}")
        else:
            scan_id = str(uuid.uuid4())
            progress = ScanProgress(
                scan_id=scan_id,
                account_id=config.account_id,
                status=ScanStatus.IN_PROGRESS,
            )
            self._active_scans[scan_id] = progress
            logger.info(f"Starting new scan {scan_id} for account {config.account_id}")

        # Log scan start event
        log_event(
            event_type=EventType.CUSTOM,
            account_id=config.account_id,
            payload={
                'scan_id': progress.scan_id,
                'scan_type': 'history_scan',
                'action': 'started',
                'config': config.model_dump(),
            },
        )

        # Start processing in background
        asyncio.create_task(self._process_scan(gmail_service, config, progress))

        return progress

    async def pause_scan(self, scan_id: str) -> bool:
        """
        Pause an active scan

        Args:
            scan_id: ID of scan to pause

        Returns:
            True if paused successfully
        """
        progress = self._active_scans.get(scan_id)
        if not progress or progress.status != ScanStatus.IN_PROGRESS:
            return False

        progress.status = ScanStatus.PAUSED
        progress.last_updated_at = datetime.now()

        log_event(
            event_type=EventType.CUSTOM,
            account_id=progress.account_id,
            payload={'scan_id': scan_id, 'action': 'paused'},
        )

        logger.info(f"Scan {scan_id} paused at {progress.processed}/{progress.total_found} emails")
        return True

    async def resume_scan(self, scan_id: str, gmail_service: Resource) -> bool:
        """
        Resume a paused scan

        Args:
            scan_id: ID of scan to resume
            gmail_service: Gmail API service object

        Returns:
            True if resumed successfully
        """
        progress = self._active_scans.get(scan_id)
        if not progress or progress.status != ScanStatus.PAUSED:
            return False

        progress.status = ScanStatus.IN_PROGRESS
        progress.last_updated_at = datetime.now()

        log_event(
            event_type=EventType.CUSTOM,
            account_id=progress.account_id,
            payload={'scan_id': scan_id, 'action': 'resumed'},
        )

        # Reconstruct config from progress (simplified - in production, store full config)
        config = ScanConfig(account_id=progress.account_id)

        # Continue processing
        asyncio.create_task(self._process_scan(gmail_service, config, progress))

        logger.info(f"Scan {scan_id} resumed from {progress.processed}/{progress.total_found} emails")
        return True

    async def cancel_scan(self, scan_id: str) -> bool:
        """
        Cancel an active or paused scan

        Args:
            scan_id: ID of scan to cancel

        Returns:
            True if cancelled successfully
        """
        progress = self._active_scans.get(scan_id)
        if not progress:
            return False

        progress.status = ScanStatus.FAILED
        progress.error_message = "Scan cancelled by user"
        progress.completed_at = datetime.now()
        progress.last_updated_at = datetime.now()

        log_event(
            event_type=EventType.CUSTOM,
            account_id=progress.account_id,
            payload={'scan_id': scan_id, 'action': 'cancelled'},
        )

        logger.info(f"Scan {scan_id} cancelled")
        return True

    async def _process_scan(
        self,
        gmail_service: Resource,
        config: ScanConfig,
        progress: ScanProgress,
    ) -> ScanResult:
        """
        Internal method to process the scan

        Args:
            gmail_service: Gmail API service object
            config: Scan configuration
            progress: Progress tracker

        Returns:
            ScanResult with summary
        """
        try:
            # Fetch email list from Gmail
            async for batch in self._fetch_email_batches(gmail_service, config, progress):
                if progress.status == ScanStatus.PAUSED:
                    logger.info(f"Scan {progress.scan_id} paused, waiting...")
                    break

                # Process batch
                await self._process_batch(gmail_service, batch, config, progress)

                # Update progress
                progress.last_updated_at = datetime.now()
                self._update_eta(progress)

                # Save checkpoint
                self._save_checkpoint(progress)

            # Mark as completed
            if progress.status == ScanStatus.IN_PROGRESS:
                progress.status = ScanStatus.COMPLETED
                progress.completed_at = datetime.now()
                progress.last_updated_at = datetime.now()

                logger.info(
                    f"Scan {progress.scan_id} completed: "
                    f"{progress.processed} processed, {progress.skipped} skipped, {progress.failed} failed"
                )

                # Log completion event
                log_event(
                    event_type=EventType.CUSTOM,
                    account_id=config.account_id,
                    payload={
                        'scan_id': progress.scan_id,
                        'action': 'completed',
                        'stats': {
                            'processed': progress.processed,
                            'skipped': progress.skipped,
                            'failed': progress.failed,
                            'tasks': progress.tasks_extracted,
                            'decisions': progress.decisions_extracted,
                            'questions': progress.questions_extracted,
                        },
                    },
                )

            # Build result
            duration = (datetime.now() - progress.started_at).total_seconds()
            result = ScanResult(
                scan_id=progress.scan_id,
                account_id=config.account_id,
                status=progress.status,
                total_processed=progress.processed,
                total_skipped=progress.skipped,
                total_failed=progress.failed,
                duration_seconds=duration,
                emails_per_second=progress.processed / duration if duration > 0 else 0,
                high_confidence=progress.classified_high,
                medium_confidence=progress.classified_medium,
                low_confidence=progress.classified_low,
                total_tasks=progress.tasks_extracted,
                total_decisions=progress.decisions_extracted,
                total_questions=progress.questions_extracted,
                total_attachments=progress.attachments_downloaded,
                total_threads=progress.threads_summarized,
            )

            return result

        except Exception as e:
            logger.error(f"Scan {progress.scan_id} failed: {e}", exc_info=True)
            progress.status = ScanStatus.FAILED
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
            progress.last_updated_at = datetime.now()

            log_event(
                event_type=EventType.CUSTOM,
                account_id=config.account_id,
                payload={
                    'scan_id': progress.scan_id,
                    'action': 'failed',
                    'error': str(e),
                },
            )

            raise

    async def _fetch_email_batches(
        self,
        gmail_service: Resource,
        config: ScanConfig,
        progress: ScanProgress,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """
        Fetch emails from Gmail in batches

        Yields:
            Batches of email metadata
        """
        page_token = progress.next_page_token
        total_fetched = 0

        while True:
            # Check if paused
            if progress.status == ScanStatus.PAUSED:
                break

            # Check max results limit
            if config.max_results and total_fetched >= config.max_results:
                break

            # Fetch page from Gmail API
            request_params = {
                'userId': 'me',
                'maxResults': min(config.batch_size, config.max_results - total_fetched if config.max_results else config.batch_size),
                'q': config.query,
            }
            if page_token:
                request_params['pageToken'] = page_token

            result = gmail_service.users().messages().list(**request_params).execute()

            messages = result.get('messages', [])
            if not messages:
                break

            # Update total found (first iteration only)
            if progress.total_found == 0:
                # Estimate total (Gmail doesn't provide exact count)
                progress.total_found = result.get('resultSizeEstimate', len(messages))

            # Filter already processed emails if configured
            if config.skip_already_processed:
                messages = self._filter_already_processed(messages, config.account_id)

            yield messages

            total_fetched += len(messages)
            page_token = result.get('nextPageToken')
            progress.next_page_token = page_token

            if not page_token:
                break

    def _filter_already_processed(
        self,
        messages: List[Dict[str, Any]],
        account_id: str,
    ) -> List[Dict[str, Any]]:
        """Filter out emails that are already in processed_emails table"""
        email_ids = [msg['id'] for msg in messages]

        with get_db() as db:
            processed_ids = set(
                row[0] for row in db.query(ProcessedEmail.email_id)
                .filter(
                    ProcessedEmail.account_id == account_id,
                    ProcessedEmail.email_id.in_(email_ids),
                )
                .all()
            )

        return [msg for msg in messages if msg['id'] not in processed_ids]

    async def _process_batch(
        self,
        gmail_service: Resource,
        batch: List[Dict[str, Any]],
        config: ScanConfig,
        progress: ScanProgress,
    ):
        """Process a batch of emails through classification orchestrator"""
        for msg_metadata in batch:
            try:
                email_id = msg_metadata['id']

                # Fetch full email
                email_data = gmail_service.users().messages().get(
                    userId='me',
                    id=email_id,
                    format='full',
                ).execute()

                # Convert to orchestrator format
                email_dict = self._convert_gmail_to_dict(email_data)

                # Process through orchestrator
                stats = await self.orchestrator.process_emails([email_dict], config.account_id)

                # Update progress counters
                progress.processed += 1
                progress.classified_high += stats.get('high_confidence', 0)
                progress.classified_medium += stats.get('medium_confidence', 0)
                progress.classified_low += stats.get('low_confidence', 0)
                progress.tasks_extracted += stats.get('tasks_extracted', 0)
                progress.decisions_extracted += stats.get('decisions_extracted', 0)
                progress.questions_extracted += stats.get('questions_extracted', 0)

                progress.last_processed_email_id = email_id

            except Exception as e:
                logger.error(f"Failed to process email {msg_metadata.get('id')}: {e}")
                progress.failed += 1

    def _convert_gmail_to_dict(self, gmail_message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Gmail API message format to orchestrator format"""
        headers = {h['name']: h['value'] for h in gmail_message['payload']['headers']}

        return {
            'id': gmail_message['id'],
            'subject': headers.get('Subject', ''),
            'sender': headers.get('From', ''),
            'body': self._extract_body(gmail_message['payload']),
            'received_at': headers.get('Date', ''),
            'thread_id': gmail_message.get('threadId'),
        }

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from Gmail message payload"""
        if 'body' in payload and payload['body'].get('data'):
            import base64
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    import base64
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

        return ""

    def _update_eta(self, progress: ScanProgress):
        """Update estimated completion time"""
        if progress.processed == 0 or progress.total_found == 0:
            return

        elapsed = (datetime.now() - progress.started_at).total_seconds()
        rate = progress.processed / elapsed  # emails per second
        remaining = progress.total_found - progress.processed
        eta_seconds = remaining / rate if rate > 0 else 0

        progress.estimated_completion = datetime.now() + timedelta(seconds=eta_seconds)

    def _save_checkpoint(self, progress: ScanProgress):
        """Save checkpoint for resume capability"""
        checkpoint = ScanCheckpoint(
            scan_id=progress.scan_id,
            account_id=progress.account_id,
            batch_number=progress.processed // 50,  # Assuming batch size 50
            last_email_id=progress.last_processed_email_id or "",
            next_page_token=progress.next_page_token,
            processed_count=progress.processed,
        )

        # In production, save to database or file
        logger.debug(f"Checkpoint saved: {checkpoint.model_dump()}")
