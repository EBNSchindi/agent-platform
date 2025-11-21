#!/usr/bin/env python3
"""
Test script for Inbox API endpoints.

Tests:
- Dynamic account discovery
- Email listing with filters
- Email detail retrieval
"""

import sys
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, '/home/dani/Schreibtisch/cursor_dev/agent-systems/agent-platform')

from agent_platform.api.main import app


def main():
    """Test inbox API endpoints."""
    client = TestClient(app)

    print("=" * 60)
    print("INBOX API TEST")
    print("=" * 60)
    print()

    # Test 1: GET /api/v1/accounts
    print("Test 1: GET /api/v1/accounts")
    print("-" * 60)
    response = client.get("/api/v1/accounts")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: Found {data['total']} accounts")
        print()

        for account in data['accounts']:
            print(f"  Account: {account['account_id']}")
            print(f"    Email: {account['email']}")
            print(f"    Type: {account['account_type']}")
            print(f"    Has Token: {account['has_token']}")
            print(f"    Email Count: {account['email_count']}")
            print(f"    Last Seen: {account['last_seen']}")
            print()
    else:
        print(f"❌ Failed: {response.text}")

    print()

    # Test 2: GET /api/v1/accounts/{account_id}
    print("Test 2: GET /api/v1/accounts/gmail_1")
    print("-" * 60)
    response = client.get("/api/v1/accounts/gmail_1")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['email']} - {data['email_count']} emails")
    elif response.status_code == 404:
        print("⚠️  Account 'gmail_1' not found (may not be configured)")
    else:
        print(f"❌ Failed: {response.text}")

    print()

    # Test 3: GET /api/v1/emails (all accounts)
    print("Test 3: GET /api/v1/emails?limit=5")
    print("-" * 60)
    response = client.get("/api/v1/emails?limit=5")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['total']} total emails, showing {len(data['emails'])}")
        print()

        for email in data['emails']:
            print(f"  Subject: {email['subject']}")
            print(f"  Sender: {email['sender']}")
            print(f"  Account: {email['account_id']}")
            print(f"  Category: {email['category']} ({email['confidence']:.2f} confidence)")
            print(f"  Received: {email['received_at']}")
            print()
    else:
        print(f"❌ Failed: {response.text}")

    print()

    # Test 4: GET /api/v1/emails?account_id=gmail_1
    print("Test 4: GET /api/v1/emails?account_id=gmail_1&limit=3")
    print("-" * 60)
    response = client.get("/api/v1/emails?account_id=gmail_1&limit=3")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['total']} emails for account gmail_1")

        if len(data['emails']) > 0:
            print()
            print(f"First email: {data['emails'][0]['subject']}")
            first_email_id = data['emails'][0]['email_id']

            # Test 5: GET /api/v1/emails/{email_id} (with body)
            print()
            print(f"Test 5: GET /api/v1/emails/{first_email_id}")
            print("-" * 60)
            response = client.get(f"/api/v1/emails/{first_email_id}")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                email_data = response.json()
                print("✅ Success: Retrieved email details")
                print()
                print(f"  Subject: {email_data['subject']}")
                print(f"  Sender: {email_data['sender']}")
                print(f"  Received: {email_data['received_at']}")
                print(f"  Category: {email_data['category']}")
                print(f"  Has Body Text: {'Yes' if email_data['body_text'] else 'No'}")
                print(f"  Has Body HTML: {'Yes' if email_data['body_html'] else 'No'}")
                print(f"  Tasks: {len(email_data.get('tasks', []))}")
                print(f"  Decisions: {len(email_data.get('decisions', []))}")
                print(f"  Questions: {len(email_data.get('questions', []))}")

                if email_data['body_text']:
                    print()
                    print("  Body Preview (first 200 chars):")
                    print(f"  {email_data['body_text'][:200]}...")
            else:
                print(f"❌ Failed to retrieve email detail: {response.text}")
        else:
            print("⚠️  No emails found for gmail_1")
    else:
        print(f"❌ Failed: {response.text}")

    print()

    # Test 6: GET /api/v1/emails?category=wichtig
    print("Test 6: GET /api/v1/emails?category=wichtig&limit=3")
    print("-" * 60)
    response = client.get("/api/v1/emails?category=wichtig&limit=3")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data['total']} emails with category 'wichtig'")

        for email in data['emails']:
            print(f"  - {email['subject']} (confidence: {email['confidence']:.2f})")
    else:
        print(f"❌ Failed: {response.text}")

    print()
    print("=" * 60)
    print("INBOX API TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
