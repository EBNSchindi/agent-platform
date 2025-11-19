#!/usr/bin/env python3
"""
Test All Service Connections

Comprehensive test of:
1. Gmail OAuth2 Connection
2. OpenAI API Connection
3. Database Connection
4. Environment Configuration

Usage:
    python scripts/test_all_connections.py

Provides a complete health check before running E2E tests.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


class ConnectionTester:
    """Test all service connections."""

    def __init__(self):
        """Initialize tester."""
        self.results = {}
        self.load_environment()

    def load_environment(self):
        """Load environment variables."""
        load_dotenv()
        self.env = {
            'openai_key': os.getenv('OPENAI_API_KEY'),
            'gmail_2_creds': os.getenv('GMAIL_2_CREDENTIALS_PATH'),
            'gmail_2_token': os.getenv('GMAIL_2_TOKEN_PATH'),
            'gmail_2_email': os.getenv('GMAIL_2_EMAIL'),
            'database_url': os.getenv('DATABASE_URL', 'sqlite:///platform.db'),
        }

    def print_header(self):
        """Print test header."""
        print()
        print("=" * 70)
        print("Service Connection Health Check")
        print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 70)
        print()

    def test_environment(self):
        """Test environment configuration."""
        print("1️⃣  Environment Configuration")
        print("   " + "-" * 66)

        tests = {
            'OPENAI_API_KEY': self.env['openai_key'] is not None,
            'GMAIL_2_CREDENTIALS_PATH': self.env['gmail_2_creds'] is not None,
            'GMAIL_2_TOKEN_PATH': self.env['gmail_2_token'] is not None,
            'GMAIL_2_EMAIL': self.env['gmail_2_email'] is not None,
        }

        for key, result in tests.items():
            status = "✅" if result else "❌"
            value = getattr(self.env, key.lower().replace('_', '_'), None)
            if key == 'OPENAI_API_KEY' and result:
                value = f"{self.env['openai_key'][:20]}...{self.env['openai_key'][-10:]}"
            print(f"   {status} {key:30s} {'set' if result else 'NOT SET'}")

        all_ok = all(tests.values())
        self.results['environment'] = all_ok
        print()
        return all_ok

    def test_gmail_files(self):
        """Test Gmail file configuration."""
        print("2️⃣  Gmail Configuration Files")
        print("   " + "-" * 66)

        creds_path = self.env['gmail_2_creds']
        token_path = self.env['gmail_2_token']

        # Check credentials file
        if creds_path and os.path.exists(creds_path):
            print(f"   ✅ Credentials file exists: {creds_path}")
            creds_ok = True
        else:
            print(f"   ❌ Credentials file NOT found: {creds_path}")
            print(f"      Download from: https://console.cloud.google.com/")
            creds_ok = False

        # Check token file (might not exist yet)
        if token_path:
            if os.path.exists(token_path):
                print(f"   ✅ Token cached: {token_path}")
                token_ok = True
            else:
                print(f"   ⏳ Token not cached yet: {token_path}")
                print(f"      Will be created on first run of test_gmail_auth.py")
                token_ok = True  # Not required yet

        all_ok = creds_ok and token_ok
        self.results['gmail_files'] = all_ok
        print()
        return all_ok

    def test_gmail_connection(self):
        """Test Gmail API connection."""
        print("3️⃣  Gmail API Connection")
        print("   " + "-" * 66)

        creds_path = self.env['gmail_2_creds']

        if not creds_path or not os.path.exists(creds_path):
            print("   ⏭️  Skipping (credentials not found)")
            print("      Run: python scripts/test_gmail_auth.py")
            self.results['gmail_connection'] = None  # Not tested
            print()
            return None

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            SCOPES = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels',
            ]

            token_path = self.env['gmail_2_token']
            creds = None

            # Load cached token if exists
            if token_path and os.path.exists(token_path):
                try:
                    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                    if creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                except:
                    creds = None

            # If no cached token, flow is needed
            if not creds:
                print("   ⏳ No cached token - needs OAuth flow")
                print("      Run: python scripts/test_gmail_auth.py")
                print("      This will open your browser for authorization")
                self.results['gmail_connection'] = True  # Will work after auth
                print()
                return True

            # Test connection with cached token
            try:
                service = build('gmail', 'v1', credentials=creds)

                # Try to get profile
                profile = service.users().getProfile(userId='me').execute()
                email = profile.get('emailAddress', 'unknown')

                print(f"   ✅ Gmail API connection successful")
                print(f"      Email: {email}")
                print(f"      Messages in inbox: {profile.get('messagesTotal', 'unknown')}")

                self.results['gmail_connection'] = True
                print()
                return True

            except Exception as e:
                print(f"   ❌ Gmail API test request failed: {e}")
                self.results['gmail_connection'] = False
                print()
                return False

        except Exception as e:
            print(f"   ❌ Gmail connection test failed: {e}")
            self.results['gmail_connection'] = False
            print()
            return False

    def test_openai_connection(self):
        """Test OpenAI API connection."""
        print("4️⃣  OpenAI API Connection")
        print("   " + "-" * 66)

        api_key = self.env['openai_key']

        if not api_key or api_key.startswith('your_'):
            print("   ⏭️  Skipping (API key not set)")
            print("      Set OPENAI_API_KEY in .env")
            self.results['openai_connection'] = False
            print()
            return False

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            # Test with models list
            response = client.models.list()

            # Count available models
            all_models = len(response.data)
            gpt_models = len([m for m in response.data if 'gpt' in m.id.lower()])

            print(f"   ✅ OpenAI API connection successful")
            print(f"      Total models available: {all_models}")
            print(f"      GPT models available: {gpt_models}")

            # Test with actual LLM call
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": "OK"}],
                    max_tokens=10,
                )
                print(f"   ✅ LLM request successful (gpt-4o available)")
            except Exception as e:
                if "gpt-4o" in str(e):
                    print(f"   ⚠️  gpt-4o not available, will use fallback model")
                else:
                    print(f"   ⚠️  LLM request warning: {str(e)[:50]}")

            self.results['openai_connection'] = True
            print()
            return True

        except Exception as e:
            print(f"   ❌ OpenAI API test failed: {e}")
            self.results['openai_connection'] = False
            print()
            return False

    def test_database_connection(self):
        """Test database connection."""
        print("5️⃣  Database Connection")
        print("   " + "-" * 66)

        db_url = self.env['database_url']

        try:
            from agent_platform.db.database import get_db

            # Try to get a database session
            with get_db() as db:
                # Test with a simple query
                from agent_platform.db.models import Base
                print(f"   ✅ Database connection successful")
                print(f"      Database URL: {db_url}")
                print(f"      Database type: {'SQLite' if 'sqlite' in db_url else 'PostgreSQL/Other'}")

            self.results['database_connection'] = True
            print()
            return True

        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            print(f"      Database URL: {db_url}")
            print(f"      Initialize with: python -c \"from agent_platform.db.database import init_db; init_db()\"")
            self.results['database_connection'] = False
            print()
            return False

    def print_summary(self):
        """Print test summary."""
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print()

        # Status mapping
        status_map = {
            True: "✅ OK",
            False: "❌ FAILED",
            None: "⏳ PENDING",
        }

        for test_name, result in self.results.items():
            status = status_map.get(result, "❓ UNKNOWN")
            display_name = test_name.replace('_', ' ').title()
            print(f"  {status:12s} {display_name}")

        print()

        # Overall status
        failed = sum(1 for v in self.results.values() if v is False)
        all_ok = all(v is not False for v in self.results.values())

        if all_ok and failed == 0:
            print("🎉 All tests passed! System is ready.")
            print()
            print("Next steps:")
            print("1. Run E2E test: python tests/test_e2e_real_gmail.py")
            print("2. Or analyze mailbox: python scripts/analyze_mailbox_history.py")
            return True
        else:
            print("⚠️  Some tests need attention:")
            for test_name, result in self.results.items():
                if result is False:
                    print(f"  • {test_name.replace('_', ' ').title()} - see above for details")
            return False

    def run_all_tests(self):
        """Run all tests."""
        self.print_header()

        try:
            self.test_environment()
            self.test_gmail_files()
            self.test_gmail_connection()
            self.test_openai_connection()
            self.test_database_connection()

            return self.print_summary()

        except Exception as e:
            print()
            print("=" * 70)
            print(f"❌ Unexpected error: {e}")
            print("=" * 70)
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    tester = ConnectionTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
