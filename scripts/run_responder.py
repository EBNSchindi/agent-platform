"""
Test Script: Email Responder
Tests draft generation functionality.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from platform.core.config import Config
from platform.db.database import init_db
from modules.email.module import register_email_module
from modules.email.tools.gmail_tools import fetch_unread_emails_tool, create_draft_tool
from modules.email.agents.classifier import classify_emails_batch
from modules.email.agents.responder import generate_response
from platform.core.registry import get_registry


async def main():
    """Test email response generation"""

    print("=" * 70)
    print("EMAIL RESPONDER TEST")
    print("=" * 70)

    # Initialize
    print("\n🔧 Initializing...")
    init_db()
    registry = register_email_module()

    # Get agents
    classifier = registry.get_agent("email.classifier")
    responder = registry.get_agent("email.responder")

    if not (classifier and responder):
        print("❌ Agents not found!")
        return

    print(f"✅ Agents loaded")

    # Fetch emails
    print("\n📧 Fetching unread emails from gmail_1...")

    try:
        emails = fetch_unread_emails_tool("gmail_1", max_results=3)

        if not emails:
            print("📭 No unread emails found")
            print("\n💡 Tip: Send yourself a test email to try response generation")
            return

        print(f"✅ Found {len(emails)} unread emails\n")

        # Classify first
        print("🔍 Classifying emails...\n")
        classifications = await classify_emails_batch(emails, classifier)

        # Process emails that should be replied to
        for i, (email, classification) in enumerate(zip(emails, classifications), 1):
            print(f"{'=' * 70}")
            print(f"EMAIL #{i}")
            print(f"{'=' * 70}")
            print(f"📬 Subject: {email['subject'][:60]}")
            print(f"👤 From: {email['sender'][:50]}")
            print(f"🏷️  Category: {classification.category}")
            print(f"📊 Should Reply: {'✅ Yes' if classification.should_reply else '❌ No'}")
            print()

            if not classification.should_reply and classification.category != 'normal':
                print(f"⏭️  Skipping (not suitable for auto-reply)\n")
                continue

            # Generate response
            print("✍️  Generating response draft...\n")

            response = await generate_response(
                email=email,
                classification=classification.__dict__
            )

            print(f"📝 GENERATED DRAFT:")
            print(f"{'=' * 70}")
            print(f"Subject: {response.subject}")
            print(f"Tone: {response.tone.upper()}")
            print(f"Confidence: {response.confidence_score:.2%}")
            print(f"Requires Review: {'✅ Yes' if response.requires_review else '❌ No'}")
            print(f"\nBody:\n{'-' * 70}")
            print(response.body)
            print(f"{'-' * 70}\n")
            print(f"Reasoning: {response.reasoning}\n")

            # Ask to save draft
            save = input("💾 Save this draft to Gmail? (y/n): ").lower().strip()

            if save == 'y':
                print("📤 Creating draft in Gmail...")

                result = create_draft_tool(
                    account_id="gmail_1",
                    to=email['sender'],
                    subject=response.subject,
                    body=response.body
                )

                if result['status'] == 'success':
                    print(f"✅ {result['message']}")
                    print(f"   Draft ID: {result.get('draft_id', 'N/A')}")
                else:
                    print(f"❌ Failed: {result.get('message', 'Unknown error')}")
            else:
                print("⏭️  Draft not saved")

            print()

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Setup Instructions:")
        print("1. Configure .env with Gmail credentials")
        print("2. Run scripts/run_classifier.py first for OAuth setup")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
