#!/usr/bin/env python3
"""
Load sample emails using JSON token files directly.
Simple approach - loads JSON tokens, refreshes if needed, fetches emails.
"""

import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from agent_platform.orchestration.classification_orchestrator import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail


def load_credentials_from_json(token_path: str) -> Credentials:
    """Load credentials from JSON file and refresh if needed."""
    with open(token_path, 'r') as f:
        token_data = json.load(f)

    # Create Credentials object from JSON data
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes')
    )

    # Refresh if expired
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print(f"   Token expired, refreshing...")
            creds.refresh(Request())
            print(f"   Token refreshed, new expiry: {creds.expiry}")

            # Save refreshed token back to JSON
            token_data['token'] = creds.token
            token_data['expiry'] = creds.expiry.isoformat() if creds.expiry else None
            with open(token_path, 'w') as f:
                json.dump(token_data, f, indent=2)

    return creds


async def load_and_process_emails(account_id: str, token_path: str, limit: int = 10):
    """
    Load and process emails from a Gmail account.

    Args:
        account_id: Account identifier for database storage
        token_path: Path to JSON token file
        limit: Number of emails to process
    """
    print(f"\n{'='*60}")
    print(f"Processing {account_id}")
    print(f"{'='*60}")

    try:
        # Load credentials from JSON
        creds = load_credentials_from_json(token_path)
        print(f"✅ Credentials loaded, valid until: {creds.expiry}")

        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Fetch recent emails
        print(f"Fetching {limit} recent emails...")
        results = service.users().messages().list(
            userId='me',
            maxResults=limit,
            labelIds=['INBOX']
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print(f"⚠️  No emails found in inbox")
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
        print(f"   Total processed: {stats.total_processed}")
        print(f"   High confidence: {stats.high_confidence}")
        print(f"   Medium confidence: {stats.medium_confidence}")
        print(f"   Low confidence: {stats.low_confidence}")

        if stats.by_category:
            print(f"\n   By category:")
            for cat, count in stats.by_category.items():
                print(f"     {cat}: {count}")

        if stats.extraction_summary:
            ext = stats.extraction_summary
            print(f"\n   Extracted:")
            print(f"     Tasks: {ext.tasks_count}")
            print(f"     Decisions: {ext.decisions_count}")
            print(f"     Questions: {ext.questions_count}")

        return stats.total_processed

    except FileNotFoundError as e:
        print(f"❌ Error: Token file not found: {token_path}")
        return 0
    except Exception as e:
        print(f"❌ Error processing {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def main():
    """Load sample emails from all accounts with JSON tokens."""
    print("=" * 60)
    print("LOAD EMAILS FROM JSON TOKENS")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Find all JSON token files
    tokens_dir = Path('tokens')
    token_files = list(tokens_dir.glob('gmail_*_token.json'))

    if not token_files:
        print("❌ No token files found in tokens/ directory")
        return

    print(f"Found {len(token_files)} token file(s):")
    for token_file in token_files:
        print(f"  - {token_file.name}")

    emails_per_account = 3
    total_processed = 0

    for token_file in token_files:
        # Extract account ID from filename: gmail_account_1_token.json -> gmail_account_1
        account_id = token_file.stem.replace('_token', '')

        processed = await load_and_process_emails(
            account_id=account_id,
            token_path=str(token_file),
            limit=emails_per_account
        )
        total_processed += processed

        # Small delay between accounts
        if token_file != token_files[-1]:
            print("\n" + "-" * 60)
            await asyncio.sleep(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total emails processed: {total_processed}")
    print(f"Accounts processed: {len(token_files)}")
    print(f"\n✅ Done! Check the inbox at http://localhost:3000/inbox")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
