#!/usr/bin/env python3
"""
Test Ionos Email Connection
Tests IMAP connection and email fetching from Ionos account.
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from modules.email.tools.ionos_tools import IonosService

load_dotenv()


def main():
    """Test Ionos connection."""
    print("\n" + "="*70)
    print("IONOS EMAIL CONNECTION TEST")
    print("="*70)
    print()

    # Get config from .env
    email = os.getenv('IONOS_EMAIL')
    password = os.getenv('IONOS_PASSWORD')
    imap_server = os.getenv('IONOS_IMAP_SERVER', 'imap.ionos.de')
    imap_port = int(os.getenv('IONOS_IMAP_PORT', '993'))
    smtp_server = os.getenv('IONOS_SMTP_SERVER', 'smtp.ionos.de')
    smtp_port = int(os.getenv('IONOS_SMTP_PORT', '587'))

    print(f"Email: {email}")
    print(f"IMAP Server: {imap_server}:{imap_port}")
    print(f"SMTP Server: {smtp_server}:{smtp_port}")
    print()

    if not email or not password:
        print("❌ Ionos credentials not configured in .env")
        print("   Required: IONOS_EMAIL and IONOS_PASSWORD")
        return 1

    try:
        # Create service
        print("🔄 Connecting to Ionos IMAP server...")
        service = IonosService()

        # Test connection by fetching emails
        print("📬 Fetching unread emails...")
        emails = service.fetch_unread_emails(max_results=5)

        print()
        print("="*70)
        print("CONNECTION SUCCESSFUL")
        print("="*70)
        print()
        print(f"✅ Connected to {email}")
        print(f"📧 Found {len(emails)} unread email(s)")
        print()

        if emails:
            print("Recent unread emails:")
            print("-" * 70)
            for i, email_data in enumerate(emails, 1):
                print(f"\n{i}. {email_data['subject'][:60]}")
                print(f"   From: {email_data['sender'][:50]}")
                print(f"   Date: {email_data['date'][:30]}")
                print(f"   Snippet: {email_data['snippet'][:80]}...")

        print()
        print("="*70)
        print("🎉 Ionos connection test passed!")
        print("="*70)

        return 0

    except Exception as e:
        print()
        print("="*70)
        print("CONNECTION FAILED")
        print("="*70)
        print()
        print(f"❌ Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check IONOS_EMAIL and IONOS_PASSWORD in .env")
        print("2. Verify IMAP is enabled in Ionos webmail settings")
        print("3. Check firewall/network allows IMAP connections")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
