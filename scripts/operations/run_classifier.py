"""
Test Script: Email Classifier
Tests email classification functionality.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.core.config import Config
from agent_platform.db.database import init_db
from modules.email.module import register_email_module
from modules.email.tools.gmail_tools import fetch_unread_emails_tool
from modules.email.agents.classifier import classify_emails_batch
from agent_platform.core.registry import get_registry


async def main():
    """Test email classification"""

    print("=" * 70)
    print("EMAIL CLASSIFIER TEST")
    print("=" * 70)

    # Initialize database
    print("\n🔧 Initializing database...")
    init_db()

    # Register email module
    print("\n🔧 Registering email module...")
    registry = register_email_module()

    # Get classifier agent
    classifier = registry.get_agent("email.classifier")
    if not classifier:
        print("❌ Classifier agent not found!")
        return

    print(f"\n✅ Classifier agent loaded: {classifier.name}")

    # Test with Gmail account 1
    print("\n📧 Fetching unread emails from gmail_1...")
    try:
        emails = fetch_unread_emails_tool("gmail_1", max_results=5)

        if not emails:
            print("📭 No unread emails found")
            print("\n💡 Tip: Send yourself a test email to try classification")
            return

        print(f"✅ Found {len(emails)} unread emails\n")

        # Classify emails
        print("🔍 Classifying emails...\n")
        classifications = await classify_emails_batch(emails, classifier)

        # Display results
        for i, (email, classification) in enumerate(zip(emails, classifications), 1):
            print(f"{'=' * 70}")
            print(f"EMAIL #{i}")
            print(f"{'=' * 70}")
            print(f"📬 Subject: {email['subject'][:60]}")
            print(f"👤 From: {email['sender'][:50]}")
            print(f"📅 Date: {email['date']}")
            print()
            print(f"🏷️  CLASSIFICATION:")
            print(f"   Category: {classification.category.upper()}")
            print(f"   Confidence: {classification.confidence:.2%}")
            print(f"   Suggested Label: {classification.suggested_label}")
            print(f"   Should Reply: {'✅ Yes' if classification.should_reply else '❌ No'}")
            print(f"   Urgency: {classification.urgency.upper()}")
            print(f"   Reasoning: {classification.reasoning}")
            print()

        # Summary
        print(f"{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        categories = {}
        for c in classifications:
            categories[c.category] = categories.get(c.category, 0) + 1

        print(f"Total emails classified: {len(classifications)}")
        for category, count in categories.items():
            print(f"  - {category}: {count}")

        spam_count = categories.get('spam', 0)
        if spam_count > 0:
            print(f"\n🗑️  {spam_count} spam email(s) detected - ready to be filtered!")

        auto_reply_count = sum(1 for c in classifications if c.should_reply)
        if auto_reply_count > 0:
            print(f"✉️  {auto_reply_count} email(s) can be auto-replied")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Setup Instructions:")
        print("1. Copy .env.example to .env")
        print("2. Set up Gmail API credentials:")
        print("   - Go to https://console.cloud.google.com/")
        print("   - Enable Gmail API")
        print("   - Create OAuth credentials")
        print("   - Download credentials.json")
        print("   - Update GMAIL_1_CREDENTIALS_PATH in .env")
        print("3. Run this script again - browser will open for OAuth")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
