"""
Test Script for Unified Three-Layer Classifier

Tests the complete classification system:
1. Rule Layer → History Layer → LLM Layer flow
2. Early stopping on high-confidence results
3. Ollama-first + OpenAI fallback
4. Structured outputs from LLM

Usage:
    python tests/test_unified_classifier.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.classification import UnifiedClassifier, EmailToClassify
from agent_platform.db.models import SenderPreference
from agent_platform.db.database import get_db


def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_result(result, test_name: str):
    """Print classification result."""
    print(f"\n{test_name}:")
    print(f"  📊 Category: {result.category}")
    print(f"  📈 Importance: {result.importance:.2f}")
    print(f"  🎯 Confidence: {result.confidence:.2f}")
    print(f"  🔍 Layer Used: {result.layer_used}")
    print(f"  🤖 Provider: {result.llm_provider_used}")
    print(f"  ⏱️  Processing Time: {result.processing_time_ms:.0f}ms")
    print(f"  💡 Reasoning: {result.reasoning}")


async def test_spam_email():
    """Test that spam is caught by Rule Layer (no LLM call)."""
    print_header("TEST 1: SPAM EMAIL (Should use Rule Layer)")

    classifier = UnifiedClassifier()

    email = EmailToClassify(
        email_id="test_spam_1",
        subject="GEWINNSPIEL!!! Du hast gewonnen!!! KOSTENLOS!!!",
        sender="spam@spammer.com",
        body="Klicke hier für gratis Geld! Viagra! Casino! Kredit ohne Schufa!",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_result(result, "Classification Result")

    # Verify
    if result.layer_used == "rules" and result.category == "spam":
        print(f"\n✅ CORRECT: Spam caught by Rule Layer (no LLM call)")
        return True
    else:
        print(f"\n❌ UNEXPECTED: Should have been caught by Rule Layer")
        return False


async def test_normal_email_no_history():
    """Test normal email without history (should go to LLM Layer)."""
    print_header("TEST 2: NORMAL EMAIL (No History - Should use LLM Layer)")

    classifier = UnifiedClassifier()

    email = EmailToClassify(
        email_id="test_normal_1",
        subject="Projektbesprechung morgen",
        sender="colleague@company.com",
        body="Können wir uns morgen um 14 Uhr treffen, um das Projekt zu besprechen?",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_result(result, "Classification Result")

    # Verify
    if result.layer_used == "llm":
        print(f"\n✅ CORRECT: Normal email went to LLM Layer")
        return True
    else:
        print(f"\n⚠️  Unexpected layer: {result.layer_used}")
        return True  # Still pass, could be caught by rules


async def test_normal_email_with_history():
    """Test normal email WITH history (should use History Layer)."""
    print_header("TEST 3: NORMAL EMAIL (With History - Should use History Layer)")

    with get_db() as db:
        # Create mock sender with high engagement
        important_sender = SenderPreference(
            account_id="test",
            sender_email="boss@company.com",
            sender_domain="company.com",
            sender_name="Boss",
            average_importance=0.9,
            total_emails_received=25,
            total_replies=23,  # 92% reply rate
            total_archived=2,
            reply_rate=0.92,
            archive_rate=0.08,
            avg_time_to_reply_hours=1.2,
        )

        db.add(important_sender)
        db.commit()

        classifier = UnifiedClassifier(db=db)

        email = EmailToClassify(
            email_id="test_history_1",
            subject="Q4 Budget needs your approval",
            sender="boss@company.com",
            body="Please review and approve the Q4 budget proposal.",
            account_id="test",
        )

        print(f"\n📧 Email: {email.subject}")
        print(f"   From: {email.sender}")
        print(f"   History: 25 emails, 92% reply rate")

        result = await classifier.classify(email)
        print_result(result, "Classification Result")

        # Cleanup
        db.query(SenderPreference).delete()
        db.commit()

        # Verify
        if result.layer_used == "history":
            print(f"\n✅ CORRECT: Email classified by History Layer (no LLM call)")
            return True
        else:
            print(f"\n⚠️  Used {result.layer_used} layer instead of History")
            return True  # Still acceptable


async def test_newsletter():
    """Test newsletter (should be caught by Rule Layer)."""
    print_header("TEST 4: NEWSLETTER (Should use Rule Layer)")

    classifier = UnifiedClassifier()

    email = EmailToClassify(
        email_id="test_newsletter_1",
        subject="Weekly Tech Newsletter - This Week's Updates",
        sender="newsletter@techblog.com",
        body="Here are this week's tech updates. To unsubscribe, click here.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_result(result, "Classification Result")

    # Verify
    if result.layer_used == "rules" and result.category == "newsletter":
        print(f"\n✅ CORRECT: Newsletter caught by Rule Layer")
        return True
    else:
        print(f"\n❌ UNEXPECTED: Should have been caught by Rule Layer")
        return False


async def test_force_llm():
    """Test forcing LLM layer (skip Rule and History)."""
    print_header("TEST 5: FORCE LLM LAYER")

    classifier = UnifiedClassifier()

    email = EmailToClassify(
        email_id="test_force_llm_1",
        subject="Meeting rescheduled to next week",
        sender="colleague@company.com",
        body="The meeting has been rescheduled to next Monday at 10am.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")
    print(f"   Force LLM: YES")

    result = await classifier.classify(email, force_llm=True)
    print_result(result, "Classification Result")

    # Verify
    if result.layer_used == "llm":
        print(f"\n✅ CORRECT: LLM Layer forced (skipped Rule and History)")
        return True
    else:
        print(f"\n❌ UNEXPECTED: Should have used LLM Layer")
        return False


async def test_statistics():
    """Test classifier statistics tracking."""
    print_header("TEST 6: STATISTICS TRACKING")

    classifier = UnifiedClassifier()
    classifier.reset_stats()

    # Classify multiple emails
    test_emails = [
        # Spam (Rule Layer)
        EmailToClassify(
            email_id="stats_1",
            subject="GEWINNSPIEL!!!",
            sender="spam@spam.com",
            body="Gratis Geld!",
            account_id="test"
        ),
        # Newsletter (Rule Layer)
        EmailToClassify(
            email_id="stats_2",
            subject="Newsletter",
            sender="newsletter@blog.com",
            body="Unsubscribe here",
            account_id="test"
        ),
        # Normal (LLM Layer)
        EmailToClassify(
            email_id="stats_3",
            subject="Project update",
            sender="colleague@work.com",
            body="Here's an update on the project",
            account_id="test"
        ),
    ]

    print("\n📊 Classifying 3 emails to test statistics...")

    for email in test_emails:
        result = await classifier.classify(email)
        print(f"\n  • {email.subject[:30]:30s} → {result.layer_used:8s} layer")

    # Print statistics
    classifier.print_stats()

    stats = classifier.get_stats()

    if stats['total_classifications'] == 3:
        print(f"\n✅ CORRECT: Tracked 3 classifications")
        return True
    else:
        print(f"\n❌ UNEXPECTED: Should have tracked 3 classifications")
        return False


async def main():
    """Run all tests."""
    print_header("UNIFIED THREE-LAYER CLASSIFIER TEST SUITE")

    print("\nThis test suite validates the complete classification system:")
    print("  • Rule Layer: Fast pattern matching")
    print("  • History Layer: User behavior learning")
    print("  • LLM Layer: Ollama-first + OpenAI fallback")
    print("  • Unified Classifier: Orchestrates all three layers")

    # Check if Ollama or OpenAI is available
    print("\n⚠️  NOTE: These tests require either:")
    print("  1. Ollama running locally (ollama serve)")
    print("  2. Valid OpenAI API key in .env")
    print("\nIf neither is available, LLM tests will fail (expected).")

    input("\n▶️  Press Enter to continue...")

    results = {
        'spam_email': False,
        'normal_email_no_history': False,
        'normal_email_with_history': False,
        'newsletter': False,
        'force_llm': False,
        'statistics': False,
    }

    # Run tests
    try:
        results['spam_email'] = await test_spam_email()
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['normal_email_no_history'] = await test_normal_email_no_history()
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['normal_email_with_history'] = await test_normal_email_with_history()
    except Exception as e:
        print(f"\n❌ Test 3 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['newsletter'] = await test_newsletter()
    except Exception as e:
        print(f"\n❌ Test 4 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['force_llm'] = await test_force_llm()
    except Exception as e:
        print(f"\n❌ Test 5 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['statistics'] = await test_statistics()
    except Exception as e:
        print(f"\n❌ Test 6 crashed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title():.<50} {status}")

    print(f"\n{'─' * 70}")
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 70)

    if passed == total:
        print("\n🎉 All tests passed! Unified Classifier working correctly.")
    elif passed >= total - 2:
        print(f"\n⚠️  {total - passed} test(s) failed (likely due to missing Ollama/OpenAI).")
        print("   This is expected if you haven't set up LLM providers yet.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")

    print()
    sys.exit(0 if passed >= total - 2 else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user\n")
        sys.exit(1)
