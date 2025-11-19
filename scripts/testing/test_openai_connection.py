#!/usr/bin/env python3
"""
Test OpenAI API Connection

Tests the OpenAI API connection and model availability.

Usage:
    python scripts/test_openai_connection.py

The script will:
1. Check if OPENAI_API_KEY is set
2. Validate API key format
3. Test connection with a simple request
4. Check available models
5. Display pricing information
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


def test_openai_connection():
    """Test OpenAI API connection."""
    print("=" * 70)
    print("OpenAI API Connection Test")
    print("=" * 70)
    print()

    # Load environment
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')

    # 1. Check if API key is set
    print("1️⃣  Checking API Key Configuration...")
    if not api_key:
        print("   ❌ OPENAI_API_KEY not found in .env")
        return False

    if api_key.startswith('your_') or api_key == 'your_openai_api_key_here':
        print("   ❌ OPENAI_API_KEY is still a placeholder")
        return False

    print("   ✅ OPENAI_API_KEY is set")
    print(f"   Key preview: {api_key[:20]}...{api_key[-10:]}")
    print()

    # 2. Validate API key format
    print("2️⃣  Validating API Key Format...")
    if not api_key.startswith('sk-proj-'):
        print("   ⚠️  Warning: API key doesn't start with 'sk-proj-'")
        print("      This might be an older API key format")
    else:
        print("   ✅ API key format looks valid (sk-proj-...)")
    print()

    # 3. Test connection
    print("3️⃣  Testing Connection to OpenAI...")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # Make a simple request
        response = client.models.list()

        print("   ✅ Connection successful!")
        print()

        # 4. List available models
        print("4️⃣  Available Models:")
        models = response.data

        # Filter for commonly used models
        gpt_models = [m for m in models if 'gpt' in m.id.lower()][:10]

        for model in gpt_models:
            print(f"   • {model.id}")

        if not gpt_models:
            print("   ⚠️  No GPT models found in response")

        print()

        # 5. Test with actual LLM call
        print("5️⃣  Testing with Simple LLM Request...")
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Connection successful!' and nothing else."
                }
            ],
            max_tokens=50,
            temperature=0.7,
        )

        response_text = completion.choices[0].message.content
        print(f"   ✅ LLM Response: {response_text}")
        print()

        # 6. Display usage information
        print("6️⃣  Request Usage:")
        print(f"   Tokens used: {completion.usage.total_tokens}")
        print(f"   Prompt tokens: {completion.usage.prompt_tokens}")
        print(f"   Completion tokens: {completion.usage.completion_tokens}")
        print()

        # 7. Display pricing info
        print("7️⃣  Pricing Information:")
        print("   Model: gpt-4o")
        print("   Input: $5 per 1M tokens")
        print("   Output: $15 per 1M tokens")
        print()
        print(f"   Estimated cost for this test: ~$0.00001 (negligible)")
        print()

        print("=" * 70)
        print("✅ OpenAI Connection Test PASSED")
        print("=" * 70)
        print()
        print("Your OpenAI API is properly configured!")
        print()
        print("You can now:")
        print("1. Run E2E tests: python tests/test_e2e_real_gmail.py")
        print("2. Analyze mailbox: python scripts/analyze_mailbox_history.py")
        print("3. Test both together: python tests/test_e2e_real_gmail.py")
        print()

        return True

    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if API key is correct")
        print("2. Check if API key is active (not revoked)")
        print("3. Check if OpenAI API endpoint is accessible")
        print("4. Check your internet connection")
        print()

        # Show the error details
        if hasattr(e, '__dict__'):
            print("Error details:")
            for key, value in e.__dict__.items():
                print(f"  {key}: {value}")

        return False


def main():
    """Main entry point."""
    try:
        success = test_openai_connection()
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
