#!/usr/bin/env python3
"""
Test Auth API Endpoints
Quick test of the new OAuth management API endpoints.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from agent_platform.api.main import app

client = TestClient(app)


def main():
    """Test auth API endpoints."""
    print("\n" + "="*70)
    print("AUTH API ENDPOINTS TEST")
    print("="*70)

    # Test 1: List all accounts
    print("\n1️⃣  Testing GET /api/v1/auth/accounts")
    response = client.get("/api/v1/auth/accounts")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Total accounts: {data['total']}")
        print(f"   ✅ Authenticated: {data['authenticated_count']}")
        print(f"   ⚠️  Needs reauth: {data['needs_reauth_count']}")
        print("\n   Accounts:")
        for account in data['accounts']:
            status_icon = "✅" if account['authenticated'] else "❌"
            print(f"      {status_icon} {account['account_id']}: {account['email']}")
            if account['error']:
                print(f"         Error: {account['error']}")
    else:
        print(f"   ❌ Failed: {response.text}")

    # Test 2: Get status for gmail_1
    print("\n2️⃣  Testing GET /api/v1/auth/gmail/gmail_1/status")
    response = client.get("/api/v1/auth/gmail/gmail_1/status")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Account: {data['email']}")
        print(f"   ✅ Authenticated: {data['authenticated']}")
        print(f"   ✅ Token exists: {data['token_exists']}")
        print(f"   ✅ Credentials exist: {data['credentials_exist']}")
        if data['expires_at']:
            print(f"   ✅ Expires at: {data['expires_at']}")
        print(f"   ⚠️  Needs reauth: {data['needs_reauth']}")
    else:
        print(f"   ❌ Failed: {response.text}")

    # Test 3: Generate OAuth URL for gmail_1
    print("\n3️⃣  Testing GET /api/v1/auth/gmail/gmail_1/authorize")
    response = client.get("/api/v1/auth/gmail/gmail_1/authorize")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ OAuth URL generated")
        print(f"   ✅ State token: {data['state'][:20]}...")
        print(f"   ✅ URL: {data['auth_url'][:80]}...")
    else:
        print(f"   ❌ Failed: {response.text}")

    # Test 4: Try to refresh token for gmail_1
    print("\n4️⃣  Testing POST /api/v1/auth/gmail/gmail_1/refresh")
    response = client.post("/api/v1/auth/gmail/gmail_1/refresh")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success: {data['success']}")
        print(f"   ✅ Message: {data['message']}")
        if data.get('expires_at'):
            print(f"   ✅ New expiry: {data['expires_at']}")
    elif response.status_code == 400:
        print(f"   ⚠️  Cannot refresh (expected if no refresh token): {response.json()['detail']}")
    else:
        print(f"   ❌ Failed: {response.text}")

    # Test 5: Health check
    print("\n5️⃣  Testing GET /health")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Service: {data['service']}")
        print(f"   ✅ Status: {data['status']}")
    else:
        print(f"   ❌ Failed: {response.text}")

    print("\n" + "="*70)
    print("✅ Auth API tests completed")
    print("="*70)


if __name__ == '__main__':
    main()
