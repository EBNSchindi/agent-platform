#!/usr/bin/env python3
"""
Authenticate gmail_1 account
Creates token file at tokens/gmail_account_1_token.json
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

def main():
    """Authenticate gmail_1."""
    print("\n" + "="*70)
    print("Gmail Account 1 Authentication")
    print("="*70)
    print()

    # Get paths from .env
    creds_path = os.getenv('GMAIL_1_CREDENTIALS_PATH')
    token_path = os.getenv('GMAIL_1_TOKEN_PATH')
    email = os.getenv('GMAIL_1_EMAIL')

    print(f"Email: {email}")
    print(f"Credentials: {creds_path}")
    print(f"Token will be saved to: {token_path}")
    print()

    if not creds_path or not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return 1

    print("✅ Credentials file exists")
    print()
    print("🔐 Starting OAuth flow...")
    print("   Your browser will open for authorization")
    print()

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

        print(f"✅ Token saved to: {token_path}")
        print()

        # Test connection
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()

        print("✅ Connection successful!")
        print(f"📧 Email: {profile.get('emailAddress')}")
        print(f"📬 Messages: {profile.get('messagesTotal')}")
        print(f"📨 Threads: {profile.get('threadsTotal')}")
        print()
        print("="*70)
        print("🎉 Authentication complete!")
        print("="*70)

        return 0

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
