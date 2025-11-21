#!/usr/bin/env python3
"""
Load sample emails using the new OAuth system.

Uses agent_platform/auth/ for token management and Gmail API access.
Loads 10 emails from each authenticated account and processes them.
"""

import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from agent_platform.auth.token_manager import TokenManager
from agent_platform.orchestration.classification_orchestrator import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail
from googleapiclient.discovery import build


async def load_and_process_emails(account_id: str, limit: int = 10):
    """
    Load and process emails from a Gmail account using OAuth tokens.

    Args:
        account_id: Account identifier (e.g., 'gmail_1')
        limit: Number of emails to process
    """
    print(f"\n{'='*60}")
    print(f"Processing {account_id}")
    print(f"{'='*60}")

    try:
        # Initialize token manager
        token_manager = TokenManager()

        # Check if account has valid credentials
        if not token_manager.is_valid(account_id):
            print(f"❌ Account {account_id} does not have valid credentials")
            print(f"   Please authenticate via Settings page first")
            return 0

        # Refresh token if needed
        token_manager.refresh_if_needed(account_id)

        # Get credentials (returns Credentials object)
        creds = token_manager.get_credentials(account_id)
        if not creds:
            print(f"❌ Could not get credentials for {account_id}")
            return 0

        print(f"✅ Credentials valid, expires: {creds.expiry}")

        # Build Gmail service using credentials
        service = build('gmail', 'v1', credentials=creds)

        # Fetch recent emails
        print(f"Fetching {limit} recent emails...")

        # Call Gmail API
        results = service.users().messages().list(
            userId='me',
            maxResults=limit,
            labelIds=['INBOX']
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print(f"⚠️  No emails found in inbox for {account_id}")
            return 0

        print(f"✅ Found {len(messages)} emails")

        # Fetch full message details
        emails = []
        for msg in messages:
            msg_id = msg['id']

            # Get full message
            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            headers_dict = {h['name'].lower(): h['value'] for h in headers}

            # Extract body
            body_text = ''
            body_html = ''

            def extract_body(payload):
                nonlocal body_text, body_html

                if 'parts' in payload:
                    for part in payload['parts']:
                        extract_body(part)
                else:
                    mime_type = payload.get('mimeType', '')
                    body_data = payload.get('body', {}).get('data', '')

                    if body_data:
                        import base64
                        decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

                        if mime_type == 'text/plain':
                            body_text = decoded
                        elif mime_type == 'text/html':
                            body_html = decoded

            extract_body(message.get('payload', {}))

            # Build email dict
            email = {
                'id': msg_id,
                'threadId': message.get('threadId'),
                'subject': headers_dict.get('subject', '(No Subject)'),
                'sender': headers_dict.get('from', 'Unknown'),
                'recipient': headers_dict.get('to', ''),
                'date': headers_dict.get('date', ''),
                'body': body_text or body_html[:500] + '...' if body_html else '(No body)',
                'body_text': body_text,
                'body_html': body_html,
                'labels': message.get('labelIds', []),
            }

            emails.append(email)

        print(f"✅ Fetched full details for {len(emails)} emails")

        # Check which emails are already processed
        with get_db() as db:
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
        print(f"   {e}")
        return 0
    except Exception as e:
        print(f"❌ Error processing {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def main():
    """Load sample emails from all authenticated Gmail accounts."""
    print("=" * 60)
    print("LOAD EMAILS VIA OAUTH")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check which accounts are authenticated
    token_manager = TokenManager()
    accounts = ['gmail_account_1', 'gmail_account_2', 'gmail_account_3']

    authenticated_accounts = []
    for account_id in accounts:
        if token_manager.is_valid(account_id):
            authenticated_accounts.append(account_id)
            print(f"✅ {account_id} has valid credentials")
        else:
            print(f"⚠️  {account_id} does NOT have valid credentials (skipping)")

    if not authenticated_accounts:
        print("\n❌ No authenticated accounts found!")
        print("   Please authenticate accounts via Settings page first")
        return

    print(f"\nProcessing {len(authenticated_accounts)} authenticated account(s)")

    emails_per_account = 10
    total_processed = 0

    for account_id in authenticated_accounts:
        processed = await load_and_process_emails(account_id, emails_per_account)
        total_processed += processed

        # Small delay between accounts
        if account_id != authenticated_accounts[-1]:
            print("\n" + "-" * 60)
            await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total emails processed: {total_processed}")
    print(f"Accounts processed: {len(authenticated_accounts)}")
    print(f"\n✅ Done! Check the inbox at http://localhost:3000/inbox")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
