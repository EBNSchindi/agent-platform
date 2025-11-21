#!/usr/bin/env python3
"""
Load sample emails from Gmail accounts for inbox testing.

Loads 10 emails from each configured Gmail account and processes them.
"""

import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from modules.email.tools.gmail_tools import GmailService
from agent_platform.orchestration.classification_orchestrator import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail


async def load_and_process_emails(account_id: str, limit: int = 10):
    """
    Load and process emails from a Gmail account.

    Args:
        account_id: Account identifier (e.g., 'gmail_1')
        limit: Number of emails to process
    """
    print(f"\n{'='*60}")
    print(f"Processing {account_id}")
    print(f"{'='*60}")

    try:
        # Construct paths to credentials and tokens
        credentials_path = f"credentials/{account_id}.json"
        token_path = f"tokens/{account_id}_token.json"

        # Initialize Gmail service
        gmail = GmailService(
            account_id=account_id,
            credentials_path=credentials_path,
            token_path=token_path
        )

        # Fetch recent emails
        print(f"Fetching {limit} recent emails...")
        emails = gmail.fetch_recent_emails(max_results=limit)

        if not emails:
            print(f"⚠️  No emails found for {account_id}")
            return 0

        print(f"✅ Fetched {len(emails)} emails")

        # Check which emails are already processed
        with get_db() as db:
            # Get list of already processed email_ids
            existing_ids = set()
            for email in emails:
                result = db.query(ProcessedEmail).filter(
                    ProcessedEmail.account_id == account_id,
                    ProcessedEmail.email_id == email['id']
                ).first()
                if result:
                    existing_ids.add(email['id'])

        # Filter out already processed emails
        new_emails = [e for e in emails if e['id'] not in existing_ids]

        if not new_emails:
            print(f"⚠️  All {len(emails)} emails already processed")
            return 0

        print(f"📧 Processing {len(new_emails)} new emails (skipping {len(existing_ids)} already processed)")

        # Initialize orchestrator
        orchestrator = ClassificationOrchestrator()

        # Process emails
        stats = await orchestrator.process_emails(new_emails, account_id)

        print(f"\n✅ Processing complete for {account_id}:")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   High confidence: {stats['high_confidence_count']}")
        print(f"   Medium confidence: {stats['medium_confidence_count']}")
        print(f"   Low confidence: {stats['low_confidence_count']}")

        if 'by_category' in stats:
            print(f"\n   By category:")
            for cat, count in stats['by_category'].items():
                print(f"     {cat}: {count}")

        if 'extraction_summary' in stats:
            ext = stats['extraction_summary']
            print(f"\n   Extracted:")
            print(f"     Tasks: {ext.get('tasks_count', 0)}")
            print(f"     Decisions: {ext.get('decisions_count', 0)}")
            print(f"     Questions: {ext.get('questions_count', 0)}")

        return stats['total_processed']

    except FileNotFoundError as e:
        print(f"❌ Error: Credentials not found for {account_id}")
        print(f"   Please run OAuth authentication first:")
        print(f"   PYTHONPATH=. python scripts/testing/auth_{account_id}.py")
        return 0
    except Exception as e:
        print(f"❌ Error processing {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def main():
    """Load sample emails from all Gmail accounts."""
    print("=" * 60)
    print("LOAD SAMPLE EMAILS FOR INBOX TESTING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Use gmail_account_* which have existing credentials and tokens
    accounts = ['gmail_account_1', 'gmail_account_2', 'gmail_account_3']
    emails_per_account = 10

    total_processed = 0

    for account_id in accounts:
        processed = await load_and_process_emails(account_id, emails_per_account)
        total_processed += processed

        # Small delay between accounts
        if account_id != accounts[-1]:
            print("\n" + "-" * 60)
            await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total emails processed: {total_processed}")
    print(f"Accounts processed: {len(accounts)}")
    print(f"\n✅ Done! Check the inbox at http://localhost:3000/inbox")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
