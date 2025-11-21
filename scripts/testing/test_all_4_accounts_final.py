#!/usr/bin/env python3
"""
Test all 4 email accounts
- gmail_1: daniel.schindler1992@gmail.com
- gmail_2: danischin92@gmail.com
- gmail_3: ebn.veranstaltungen.consulting@gmail.com
- ionos: info@ettlingen-by-night.de
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def test_gmail_account(account_id: str, email: str) -> dict:
    """Test a single Gmail account connection."""
    print(f"\n{'='*70}")
    print(f"Testing Account: {account_id}")
    print(f"Email: {email}")
    print(f"{'='*70}")

    result = {
        'account_id': account_id,
        'email': email,
        'success': False,
        'message_count': 0,
        'error': None
    }

    try:
        # Check credentials
        creds_path_key = f"{account_id.upper()}_CREDENTIALS_PATH"
        creds_path = os.getenv(creds_path_key)

        if not creds_path:
            print(f"⚠️  {creds_path_key} not set in .env")
            result['error'] = f"{creds_path_key} not configured"
            return result

        if not os.path.exists(creds_path):
            print(f"❌ Credentials file not found: {creds_path}")
            result['error'] = "Credentials file not found"
            return result

        print(f"✅ Credentials file exists: {creds_path}")

        # Check token
        token_path_key = f"{account_id.upper()}_TOKEN_PATH"
        token_path = os.getenv(token_path_key)

        creds = None
        # Load token if exists
        if token_path and os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print(f"✅ Token file exists: {token_path}")

        # Refresh or authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
            else:
                print("⚠️  No valid token - skipping OAuth flow to avoid blocking")
                result['error'] = "No valid token (OAuth flow needed)"
                return result

        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Get profile info
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Connection successful!")
        print(f"📧 Email address: {profile.get('emailAddress', 'N/A')}")
        print(f"📬 Total messages: {profile.get('messagesTotal', 'N/A')}")
        print(f"📨 Total threads: {profile.get('threadsTotal', 'N/A')}")

        result['message_count'] = profile.get('messagesTotal', 0)
        result['success'] = True

    except Exception as e:
        error_str = str(e)
        print(f"❌ Connection failed: {e}")
        result['error'] = error_str

    return result


def test_ionos_account() -> dict:
    """Test Ionos account connection."""
    print(f"\n{'='*70}")
    print(f"Testing Account: ionos")
    print(f"Email: {os.getenv('IONOS_EMAIL', 'Not configured')}")
    print(f"{'='*70}")

    result = {
        'account_id': 'ionos',
        'email': os.getenv('IONOS_EMAIL', 'Not configured'),
        'success': False,
        'message_count': 0,
        'error': None
    }

    try:
        from modules.email.tools.ionos_tools import IonosService

        print(f"✅ Connecting to Ionos IMAP...")
        service = IonosService()

        # Fetch a few emails to test connection
        emails = service.fetch_unread_emails(max_results=1)

        print(f"✅ Connection successful!")
        print(f"📧 Email address: {result['email']}")
        print(f"📬 Unread messages: {len(emails)}")

        result['message_count'] = len(emails)
        result['success'] = True

    except Exception as e:
        error_str = str(e)
        print(f"❌ Connection failed: {e}")
        result['error'] = error_str

    return result


def main():
    """Test all accounts."""
    print("\n" + "="*70)
    print("EMAIL ACCOUNT CONNECTION TEST - ALL 4 ACCOUNTS")
    print("="*70)

    # Gmail accounts
    gmail_accounts = [
        ('gmail_1', os.getenv('GMAIL_1_EMAIL', 'Not configured')),
        ('gmail_2', os.getenv('GMAIL_2_EMAIL', 'Not configured')),
        ('gmail_3', os.getenv('GMAIL_3_EMAIL', 'Not configured')),
    ]

    results = []

    # Test Gmail accounts
    for account_id, email in gmail_accounts:
        result = test_gmail_account(account_id, email)
        results.append(result)

    # Test Ionos account
    ionos_result = test_ionos_account()
    results.append(ionos_result)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY - ALL 4 ACCOUNTS")
    print("="*70)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        msg_count = r['message_count']
        # Gmail shows total, Ionos shows unread
        count_label = "messages" if r['account_id'].startswith('gmail') else "unread"
        if r['account_id'].startswith('gmail'):
            print(f"   ✅ {r['account_id']:15} ({r['email'][:45]}) - {msg_count:,} {count_label}")
        else:
            print(f"   ✅ {r['account_id']:15} ({r['email'][:45]}) - {msg_count} {count_label}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"   ❌ {r['account_id']:15} ({r['email'][:45]}) - {r['error']}")

    print("\n" + "="*70)

    if len(successful) == len(results):
        print("🎉 All 4 accounts are working!")
        total_messages = sum(r['message_count'] for r in successful if r['account_id'].startswith('gmail'))
        print(f"📧 Total Gmail messages: {total_messages:,}")
        print("="*70)
        return 0
    else:
        print(f"⚠️  {len(failed)} account(s) need attention")
        return 1


if __name__ == '__main__':
    sys.exit(main())
