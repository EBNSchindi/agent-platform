#!/usr/bin/env python3
"""
Test Gmail OAuth2 Authentication

This script tests the Gmail OAuth2 authentication flow.
On first run, it opens a browser for you to authorize access.
The token is automatically cached for future use.

Usage:
    python scripts/test_gmail_auth.py

The script will:
1. Check if credentials.json exists
2. If no token cached: Open browser for OAuth consent
3. Fetch 5 unread emails to verify authentication works
4. Display email subjects
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
import json


def get_gmail_service(account_id: str = "gmail_2"):
    """
    Get Gmail service with OAuth2 authentication.

    Args:
        account_id: Account ID (e.g., "gmail_2")

    Returns:
        Gmail service object
    """
    from dotenv import load_dotenv

    # Load .env
    load_dotenv()

    # Get paths from environment
    creds_key = f"{account_id.upper()}_CREDENTIALS_PATH"
    token_key = f"{account_id.upper()}_TOKEN_PATH"

    creds_path = os.getenv(creds_key)
    token_path = os.getenv(token_key)

    if not creds_path:
        print(f"❌ Error: {creds_key} not found in .env")
        return None

    if not os.path.exists(creds_path):
        print(f"❌ Error: Credentials file not found: {creds_path}")
        print(f"\n📝 Please create credentials file:")
        print(f"   1. Go to https://console.cloud.google.com/")
        print(f"   2. Create OAuth2 Desktop credentials")
        print(f"   3. Download as JSON")
        print(f"   4. Save to: {creds_path}")
        return None

    # OAuth2 scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels',
    ]

    creds = None

    # Try to load cached token
    if os.path.exists(token_path):
        print(f"✅ Found cached token: {token_path}")
        from google.oauth2.credentials import Credentials as UserCredentials
        creds = UserCredentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            print("🔄 Token expired, refreshing...")
            creds.refresh(Request())

            # Save refreshed token
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            print(f"💾 Token saved: {token_path}")

    # If no cached token, perform OAuth flow
    if not creds:
        print(f"📱 No cached token found, starting OAuth flow...")
        print(f"   Credentials: {creds_path}")

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path,
                SCOPES
            )

            # This will open a browser window
            print(f"\n🌐 Opening browser for authorization...")
            print(f"   If browser doesn't open, visit the URL manually")

            creds = flow.run_local_server(port=0)

            # Save token
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())

            print(f"✅ Authorization successful!")
            print(f"💾 Token saved: {token_path}")

        except Exception as e:
            print(f"❌ OAuth flow failed: {e}")
            return None

    # Build Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        print(f"✅ Gmail service created successfully")
        return service
    except Exception as e:
        print(f"❌ Failed to create Gmail service: {e}")
        return None


def test_gmail_access(service):
    """
    Test Gmail access by fetching unread emails.

    Args:
        service: Gmail service object

    Returns:
        Number of emails fetched
    """
    try:
        print(f"\n📧 Fetching unread emails...")

        # Get unread emails
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=5
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print(f"✅ Inbox is clean! (0 unread emails)")
            return 0

        print(f"✅ Found {len(messages)} unread email(s):\n")

        for i, message in enumerate(messages, 1):
            msg_id = message['id']

            # Get message details
            msg = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(unknown)')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '(unknown)')

            print(f"   {i}. {subject[:60]}")
            print(f"      From: {sender[:50]}")
            print(f"      Date: {date}")
            print()

        return len(messages)

    except Exception as e:
        print(f"❌ Failed to fetch emails: {e}")
        return 0


def main():
    """Main test function."""
    print("=" * 70)
    print("Gmail OAuth2 Authentication Test")
    print("=" * 70)
    print()

    # Get Gmail service
    service = get_gmail_service(account_id="gmail_2")

    if not service:
        print("\n❌ Failed to authenticate with Gmail")
        sys.exit(1)

    # Test access
    count = test_gmail_access(service)

    print("=" * 70)
    if count >= 0:
        print(f"✅ Gmail authentication successful!")
        print(f"\nYou can now use the Email Classification System with gmail_2")
        print(f"Token location: tokens/gmail_account_2_token.json")
        print(f"\nNext steps:")
        print(f"1. Run E2E tests: python tests/test_e2e_real_gmail.py")
        print(f"2. Analyze mailbox: python scripts/analyze_mailbox_history.py")
    else:
        print(f"❌ Gmail authentication failed")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
