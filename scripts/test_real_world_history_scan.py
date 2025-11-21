#!/usr/bin/env python3
"""
Real-World History Scan Test Script

Tests the History Scan service with real Gmail accounts for the last 14 days.
This script verifies:
- OAuth authentication
- Email retrieval
- Classification pipeline
- Extraction pipeline
- Storage level enforcement (REQ-001: all emails → 'full')
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_platform.core.logger import get_logger
from agent_platform.email_module.email_service import EmailService
from agent_platform.history_scan.history_scan_service import HistoryScanService
from agent_platform.history_scan.models import ScanConfig
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail, EmailAccount

logger = get_logger(__name__)

# Gmail account configurations from .env
GMAIL_ACCOUNTS = [
    {
        'account_id': 'gmail_1',
        'email': 'daniel.schindler1992@gmail.com',
        'credentials_path': 'credentials/gmail_account_1.json',
        'token_path': 'tokens/gmail_account_1_token.json',
    },
    {
        'account_id': 'gmail_2',
        'email': 'danischin92@gmail.com',
        'credentials_path': 'credentials/gmail_account_2.json',
        'token_path': 'tokens/gmail_account_2_token.json',
    },
    {
        'account_id': 'gmail_3',
        'email': 'ebn.veranstaltungen.consulting@gmail.com',
        'credentials_path': 'credentials/gmail_account_3.json',
        'token_path': 'tokens/gmail_account_3_token.json',
    },
]


async def test_account(account_config: dict):
    """Test history scan for a single Gmail account."""
    account_id = account_config['account_id']
    email_address = account_config['email']

    print(f"\n{'='*80}")
    print(f"Testing Account: {account_id}")
    print(f"Email: {email_address}")
    print(f"{'='*80}\n")

    # Step 1: Authenticate and get Gmail service
    print(f"[1/5] Authenticating with Gmail...")
    try:
        email_service = EmailService(
            account_id=account_id,
            credentials_path=account_config['credentials_path'],
            token_path=account_config['token_path'],
        )
        gmail_service = email_service.get_gmail_service()
        print(f"✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

    # Step 2: Setup scan configuration (last 14 days)
    print(f"\n[2/5] Configuring History Scan (last 14 days)...")
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y/%m/%d')

    scan_config = ScanConfig(
        account_id=account_id,
        query=f"after:{fourteen_days_ago}",
        batch_size=50,
        skip_already_processed=True,  # Only scan new emails
        max_results=None,  # No limit
    )
    print(f"✅ Query: {scan_config.query}")
    print(f"✅ Batch size: {scan_config.batch_size}")

    # Step 3: Initialize scan service with orchestrator
    print(f"\n[3/5] Initializing scan service...")
    orchestrator = ClassificationOrchestrator()
    scan_service = HistoryScanService(orchestrator=orchestrator)
    print(f"✅ Scan service ready")

    # Step 4: Start scan
    print(f"\n[4/5] Starting history scan...")
    start_time = datetime.now()

    try:
        progress = await scan_service.start_scan(
            gmail_service=gmail_service,
            config=scan_config,
        )

        print(f"✅ Scan started: {progress.scan_id}")
        print(f"   Status: {progress.status}")

        # Monitor progress
        while True:
            current_progress = scan_service.get_scan_progress(progress.scan_id)
            if not current_progress:
                break

            if current_progress.status.value in ['completed', 'failed', 'paused']:
                break

            # Print progress every 5 seconds
            print(f"   Progress: {current_progress.processed}/{current_progress.total_found} emails "
                  f"(Skipped: {current_progress.skipped}, Failed: {current_progress.failed})")

            await asyncio.sleep(5)

        duration = (datetime.now() - start_time).total_seconds()

        # Final progress
        final_progress = scan_service.get_scan_progress(progress.scan_id)

        print(f"\n✅ Scan completed in {duration:.1f}s")
        print(f"   Total found: {final_progress.total_found}")
        print(f"   Processed: {final_progress.processed}")
        print(f"   Skipped: {final_progress.skipped}")
        print(f"   Failed: {final_progress.failed}")

        return {
            'account_id': account_id,
            'email': email_address,
            'scan_id': progress.scan_id,
            'duration': duration,
            'total_found': final_progress.total_found,
            'processed': final_progress.processed,
            'skipped': final_progress.skipped,
            'failed': final_progress.failed,
            'tasks': final_progress.tasks_extracted,
            'decisions': final_progress.decisions_extracted,
            'questions': final_progress.questions_extracted,
            'high_confidence': final_progress.classified_high,
            'medium_confidence': final_progress.classified_medium,
            'low_confidence': final_progress.classified_low,
        }

    except Exception as e:
        print(f"❌ Scan failed: {e}")
        logger.error(f"Scan failed for {account_id}", exc_info=True)
        return None


def verify_storage_levels(account_id: str):
    """Verify that all processed emails have storage_level='full' (REQ-001)."""
    print(f"\n[5/5] Verifying REQ-001 (storage_level='full' for all emails)...")

    with get_db() as db:
        # Get account
        account = db.query(EmailAccount).filter(EmailAccount.account_id == account_id).first()
        if not account:
            print(f"❌ Account not found in database")
            return

        # Check storage levels
        emails = db.query(ProcessedEmail).filter(
            ProcessedEmail.account_id == account.id
        ).all()

        total_emails = len(emails)
        full_storage = sum(1 for e in emails if e.storage_level == 'full')
        other_storage = sum(1 for e in emails if e.storage_level != 'full')

        print(f"   Total emails in database: {total_emails}")
        print(f"   storage_level='full': {full_storage} ({full_storage/total_emails*100:.1f}%)")

        if other_storage > 0:
            print(f"   ⚠️  Other storage levels: {other_storage}")
            # Show breakdown
            storage_counts = {}
            for email in emails:
                storage_counts[email.storage_level] = storage_counts.get(email.storage_level, 0) + 1
            print(f"   Breakdown: {storage_counts}")
        else:
            print(f"   ✅ All emails have storage_level='full' (REQ-001 verified)")


async def main():
    """Main test function."""
    print("\n" + "="*80)
    print("Real-World History Scan Test - Last 14 Days")
    print("Testing REQ-001: Standardized Email Storage (storage_level='full')")
    print("="*80 + "\n")

    results = []

    # Test each account
    for account_config in GMAIL_ACCOUNTS:
        result = await test_account(account_config)
        if result:
            results.append(result)
            verify_storage_levels(result['account_id'])

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY - All Accounts")
    print("="*80 + "\n")

    if not results:
        print("❌ No accounts tested successfully")
        return

    total_processed = sum(r['processed'] for r in results)
    total_skipped = sum(r['skipped'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_tasks = sum(r['tasks'] for r in results)
    total_decisions = sum(r['decisions'] for r in results)
    total_questions = sum(r['questions'] for r in results)
    total_duration = sum(r['duration'] for r in results)

    print(f"Accounts tested: {len(results)}/{len(GMAIL_ACCOUNTS)}")
    print(f"Total emails processed: {total_processed}")
    print(f"Total emails skipped: {total_skipped}")
    print(f"Total emails failed: {total_failed}")
    print(f"Total duration: {total_duration:.1f}s")
    print(f"Average speed: {total_processed/total_duration:.2f} emails/sec\n")

    print(f"Extraction Results:")
    print(f"  Tasks extracted: {total_tasks}")
    print(f"  Decisions extracted: {total_decisions}")
    print(f"  Questions extracted: {total_questions}\n")

    print(f"Per-Account Breakdown:")
    for result in results:
        print(f"\n  {result['account_id']} ({result['email']}):")
        print(f"    Processed: {result['processed']}")
        print(f"    Skipped: {result['skipped']}")
        print(f"    Failed: {result['failed']}")
        print(f"    Tasks: {result['tasks']}")
        print(f"    Decisions: {result['decisions']}")
        print(f"    Questions: {result['questions']}")
        print(f"    High confidence: {result['high_confidence']}")
        print(f"    Medium confidence: {result['medium_confidence']}")
        print(f"    Low confidence: {result['low_confidence']}")

    print("\n" + "="*80)
    print("✅ Real-World Testing Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
