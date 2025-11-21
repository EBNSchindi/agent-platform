#!/usr/bin/env python3
"""
Load recent emails from IONOS IMAP account.
"""

import sys
import asyncio
import imaplib
import email
from datetime import datetime, timedelta
from pathlib import Path
from email.utils import parsedate_to_datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_platform.orchestration.classification_orchestrator import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail
import os


async def load_ionos_emails(max_emails: int = 3):
    """Load and process emails from IONOS IMAP account."""
    print(f"\n{'='*60}")
    print("Processing IONOS Account")
    print(f"{'='*60}")

    # Get credentials from environment
    email_address = os.getenv('IONOS_EMAIL')
    password = os.getenv('IONOS_PASSWORD')
    imap_server = os.getenv('IONOS_IMAP_SERVER', 'imap.ionos.de')
    imap_port = int(os.getenv('IONOS_IMAP_PORT', '993'))

    if not email_address or not password:
        print("❌ IONOS credentials not found in .env")
        return 0

    print(f"📧 Connecting to {imap_server}:{imap_port}...")

    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, password)
        mail.select('INBOX')

        print(f"✅ Connected to IONOS mailbox")

        # Search for recent emails (last 4 days)
        four_days_ago = (datetime.now() - timedelta(days=4)).strftime('%d-%b-%Y')
        result, data = mail.search(None, f'(SINCE {four_days_ago})')

        if result != 'OK':
            print("❌ Failed to search emails")
            return 0

        email_ids = data[0].split()

        # Get last N emails
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

        if not email_ids:
            print(f"⚠️  No emails found in last 4 days")
            return 0

        print(f"✅ Found {len(email_ids)} recent emails")

        # Fetch email details
        emails = []
        for email_id in email_ids:
            result, data = mail.fetch(email_id, '(RFC822)')
            if result != 'OK':
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract headers
            subject = msg.get('Subject', '(No Subject)')
            sender = msg.get('From', 'Unknown')
            recipient = msg.get('To', '')
            date_str = msg.get('Date', '')

            # Parse date
            try:
                received_at = parsedate_to_datetime(date_str)
            except:
                received_at = datetime.now()

            # Extract body
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = ''

            # Create email dict
            emails.append({
                'id': f"ionos_{email_id.decode()}",
                'threadId': f"ionos_thread_{email_id.decode()}",
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'date': date_str,
                'body': body[:1000] if body else '(No body)',
                'body_text': body,
                'body_html': '',
                'labels': ['INBOX'],
            })

        mail.close()
        mail.logout()

        print(f"✅ Fetched {len(emails)} email details")

        # Check which emails are already processed
        account_id = 'ionos'
        with get_db() as db:
            existing_ids = set()
            for email_data in emails:
                result = db.query(ProcessedEmail).filter(
                    ProcessedEmail.account_id == account_id,
                    ProcessedEmail.email_id == email_data['id']
                ).first()
                if result:
                    existing_ids.add(email_data['id'])

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

        print(f"\n✅ Processing complete for ionos:")
        print(f"   Total processed: {stats.total_processed}")
        print(f"   High confidence: {stats.high_confidence}")
        print(f"   Medium confidence: {stats.medium_confidence}")
        print(f"   Low confidence: {stats.low_confidence}")

        if stats.by_category:
            print(f"\n   By category:")
            for cat, count in stats.by_category.items():
                print(f"     {cat}: {count}")

        return stats.total_processed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def main():
    """Main function."""
    print("=" * 60)
    print("LOAD IONOS EMAILS")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    processed = await load_ionos_emails(max_emails=3)

    print("\n" + "=" * 60)
    print(f"✅ DONE: Processed {processed} emails from IONOS")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
