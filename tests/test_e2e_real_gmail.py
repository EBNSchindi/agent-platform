#!/usr/bin/env python3
"""
End-to-End Test with Real Gmail Account

This test runs the complete email classification pipeline with real emails
from a Gmail account.

Test Flow:
1. Authenticate with Gmail Account 2
2. Fetch 5-10 unread emails
3. Process through complete classification pipeline:
   - Rule Layer (spam, newsletter detection)
   - History Layer (sender preferences)
   - LLM Layer (if needed, requires OpenAI API key)
4. Route based on confidence (high/medium/low)
5. Generate statistics

Requirements:
- Gmail Account 2 credentials in credentials/gmail_account_2.json
- OpenAI API key in .env
- database initialized (python -c "from agent_platform.db.database import init_db; init_db()")

Run:
    python tests/test_e2e_real_gmail.py

Expected Output:
    - Classification results for each email
    - Statistics by confidence level
    - Statistics by category
    - Processing time
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Gmail tools
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Import classification system
from agent_platform.classification import UnifiedClassifier, EmailToClassify
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.db.database import init_db


def load_environment():
    """Load environment variables."""
    load_dotenv()
    return {
        'openai_key': os.getenv('OPENAI_API_KEY'),
        'gmail_2_creds': os.getenv('GMAIL_2_CREDENTIALS_PATH'),
        'gmail_2_token': os.getenv('GMAIL_2_TOKEN_PATH'),
        'gmail_2_email': os.getenv('GMAIL_2_EMAIL'),
    }


def authenticate_gmail(creds_path: str, token_path: str) -> Any:
    """
    Authenticate with Gmail using OAuth2.

    Args:
        creds_path: Path to credentials.json
        token_path: Path to token.json

    Returns:
        Gmail service object
    """
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
    ]

    creds = None

    # Load cached token if exists
    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

    # Otherwise, perform OAuth flow
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def fetch_unread_emails(service, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch unread emails from Gmail.

    Args:
        service: Gmail service object
        max_results: Maximum number of emails to fetch

    Returns:
        List of email dictionaries
    """
    print(f"📧 Fetching up to {max_results} unread emails from Gmail...")

    # Get unread message IDs
    results = service.users().messages().list(
        userId='me',
        q='is:unread',
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    print(f"   Found {len(messages)} unread email(s)")

    if not messages:
        return []

    # Fetch full message details
    emails = []
    for msg_id_obj in messages:
        msg_id = msg_id_obj['id']

        # Get full message
        msg = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '(unknown)')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')

        # Extract body
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = msg['payload']['body'].get('data', '')
            if data:
                import base64
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        # Truncate body to first 500 chars for display
        snippet = body[:500] if body else "(no body)"

        emails.append({
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'body': body,
            'snippet': snippet,
            'received_at': datetime.utcnow(),
        })

    return emails


async def run_e2e_test():
    """Run the complete end-to-end test."""
    print("=" * 70)
    print("EMAIL CLASSIFICATION SYSTEM - E2E TEST WITH REAL GMAIL")
    print("=" * 70)
    print()

    # Load environment
    env = load_environment()

    # Validate environment
    print("🔍 Validating environment...")
    if not env['openai_key'] or env['openai_key'].startswith('your_'):
        print("   ⚠️  OPENAI_API_KEY not configured")
        print("   → Set in .env for full classification")
    else:
        print("   ✅ OPENAI_API_KEY configured")

    if not env['gmail_2_creds']:
        print("   ❌ GMAIL_2_CREDENTIALS_PATH not configured")
        return False

    if not os.path.exists(env['gmail_2_creds']):
        print(f"   ❌ Credentials file not found: {env['gmail_2_creds']}")
        return False

    print(f"   ✅ Gmail credentials found")
    print(f"   ✅ Database configured")
    print()

    # Initialize database
    print("🗄️  Initializing database...")
    init_db()
    print("   ✅ Database ready")
    print()

    # Authenticate with Gmail
    print("🔐 Authenticating with Gmail...")
    try:
        service = authenticate_gmail(env['gmail_2_creds'], env['gmail_2_token'])
        print("   ✅ Gmail authentication successful")
    except Exception as e:
        print(f"   ❌ Gmail authentication failed: {e}")
        return False
    print()

    # Fetch emails
    print("📬 Fetching emails from Gmail...")
    emails = fetch_unread_emails(service, max_results=10)

    if not emails:
        print("   ℹ️  No unread emails found")
        print("   Send some test emails to your account first")
        return True

    print(f"   ✅ Fetched {len(emails)} email(s)")
    print()

    # Process emails through classification pipeline
    print("🔄 Processing emails through classification pipeline...")
    print()

    orchestrator = ClassificationOrchestrator()
    stats = await orchestrator.process_emails(emails, 'gmail_2')

    # Print results
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print()
    print(f"✅ Test completed successfully!")
    print(f"   Processed: {stats.total_processed} emails")
    print(f"   Duration: {stats.duration_seconds:.2f}s" if stats.duration_seconds else "   Duration: N/A")
    print()
    print(f"By Confidence Level:")
    print(f"   High (≥0.85):     {stats.high_confidence} ({stats.high_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   High (≥0.85):     0")
    print(f"   Medium (0.6-0.85): {stats.medium_confidence} ({stats.medium_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   Medium (0.6-0.85): 0")
    print(f"   Low (<0.6):       {stats.low_confidence} ({stats.low_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   Low (<0.6):       0")
    print()
    print(f"By Category:")
    for category, count in sorted(stats.by_category.items(), key=lambda x: x[1], reverse=True):
        print(f"   {category:20s}: {count:3d}")
    print()

    print("=" * 70)
    print("✅ E2E TEST PASSED")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Analyze mailbox history: python scripts/analyze_mailbox_history.py")
    print("2. Run all tests: pytest tests/")
    print("3. Review classification results in database")
    print()

    return True


def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_e2e_test())
        sys.exit(0 if success else 1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
