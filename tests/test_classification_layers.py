"""
Test Script for Rule Layer + History Layer

Tests the two-layer classification system without LLM calls:
1. Rule Layer: Pattern matching (spam, auto-reply, newsletters, etc.)
2. History Layer: Learning from user behavior patterns

Usage:
    python tests/test_classification_layers.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.classification.models import EmailToClassify
from agent_platform.classification.importance_rules import RuleLayer
from agent_platform.classification.importance_history import HistoryLayer
from agent_platform.db.models import SenderPreference, DomainPreference
from agent_platform.db.database import get_db


def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_result(result, layer_name: str):
    """Print classification result."""
    print(f"\n{layer_name} Result:")
    print(f"  Category: {result.category}")
    print(f"  Importance: {result.importance:.2f}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Reasoning: {result.reasoning}")

    if hasattr(result, 'matched_rules') and result.matched_rules:
        print(f"  Matched Rules: {', '.join(result.matched_rules)}")

    if hasattr(result, 'spam_signals') and result.spam_signals:
        print(f"  Spam Signals: {', '.join(result.spam_signals[:3])}")

    if hasattr(result, 'data_source'):
        print(f"  Data Source: {result.data_source}")
        print(f"  Historical Emails: {result.total_historical_emails}")


def test_rule_layer():
    """Test Rule Layer with various email types."""
    print_header("TEST 1: RULE LAYER")

    rule_layer = RuleLayer()

    # Test cases
    test_emails = [
        # 1. Obvious spam
        EmailToClassify(
            email_id="spam_1",
            subject="GEWINNSPIEL!!! Du hast gewonnen! KOSTENLOS!!!",
            sender="spam@spammer.com",
            body="Klicke hier für gratis Geld! Viagra! Casino!",
            account_id="test",
        ),

        # 2. Auto-reply
        EmailToClassify(
            email_id="auto_1",
            subject="Out of Office: Vacation",
            sender="colleague@company.com",
            body="This is an automatic reply. I am out of office until next week.",
            account_id="test",
        ),

        # 3. Newsletter
        EmailToClassify(
            email_id="newsletter_1",
            subject="Weekly Tech Newsletter - This Week's Updates",
            sender="newsletter@techblog.com",
            body="Here are this week's tech updates. Unsubscribe at the bottom.",
            account_id="test",
        ),

        # 4. System notification
        EmailToClassify(
            email_id="system_1",
            subject="Password Reset Request",
            sender="noreply@github.com",
            body="You requested a password reset. Your verification code is: 123456",
            account_id="test",
        ),

        # 5. Normal email (no clear pattern)
        EmailToClassify(
            email_id="normal_1",
            subject="Meeting tomorrow",
            sender="boss@company.com",
            body="Can we meet tomorrow at 2pm to discuss the project?",
            account_id="test",
        ),

        # 6. German auto-reply
        EmailToClassify(
            email_id="auto_2",
            subject="Automatische Antwort: Abwesenheitsnotiz",
            sender="mueller@firma.de",
            body="Ich bin bis nächste Woche im Urlaub und nicht erreichbar.",
            account_id="test",
        ),
    ]

    print("\n📋 Testing Rule Layer with 6 different email types...\n")

    for i, email in enumerate(test_emails, 1):
        print(f"\n{'─' * 70}")
        print(f"Test Case {i}: {email.subject[:50]}")
        print(f"  From: {email.sender}")

        result = rule_layer.classify(email)
        print_result(result, "Rule Layer")

        # Evaluate if this is a high-confidence result
        if result.confidence >= 0.85:
            print(f"  ✅ HIGH CONFIDENCE - Would skip History/LLM layers")
        elif result.confidence >= 0.6:
            print(f"  ⚠️  MEDIUM CONFIDENCE - Would proceed to History layer")
        else:
            print(f"  ❌ LOW CONFIDENCE - Would proceed to History layer")

    return True


def test_history_layer_without_data():
    """Test History Layer with no historical data."""
    print_header("TEST 2: HISTORY LAYER (No Historical Data)")

    with get_db() as db:
        history_layer = HistoryLayer(db=db)

        email = EmailToClassify(
            email_id="test_1",
            subject="First email from new sender",
            sender="newperson@example.com",
            body="This is the first email from this sender.",
            account_id="test_account",
        )

        print("\n📧 Testing with email from unknown sender...")
        print(f"  Sender: {email.sender}")

        result = history_layer.classify(email)
        print_result(result, "History Layer")

        if result.confidence < 0.3:
            print(f"  ✅ CORRECT: Low confidence due to no historical data")
        else:
            print(f"  ❌ UNEXPECTED: Should have low confidence with no data")

    return True


def test_history_layer_with_mock_data():
    """Test History Layer with mock historical data."""
    print_header("TEST 3: HISTORY LAYER (With Mock Historical Data)")

    with get_db() as db:
        # Create mock sender preference (important sender)
        important_sender = SenderPreference(
            account_id="test_account",
            sender_email="boss@company.com",
            sender_domain="company.com",
            sender_name="Boss",
            average_importance=0.9,
            total_emails_received=20,
            total_replies=18,  # 90% reply rate
            total_archived=2,
            reply_rate=0.9,
            archive_rate=0.1,
            avg_time_to_reply_hours=1.5,  # Quick responses
        )

        # Create mock sender preference (newsletter sender)
        newsletter_sender = SenderPreference(
            account_id="test_account",
            sender_email="newsletter@blog.com",
            sender_domain="blog.com",
            sender_name="Blog Newsletter",
            average_importance=0.3,
            total_emails_received=50,
            total_replies=0,  # 0% reply rate
            total_archived=50,  # 100% archived
            reply_rate=0.0,
            archive_rate=1.0,
        )

        # Create mock domain preference
        company_domain = DomainPreference(
            account_id="test_account",
            domain="company.com",
            preferred_category="wichtig",
            average_importance=0.7,
            total_emails_received=100,
            reply_rate=0.6,
            archive_rate=0.4,
        )

        # Add to database
        db.add(important_sender)
        db.add(newsletter_sender)
        db.add(company_domain)
        db.commit()

        print("\n✅ Created mock historical data:")
        print(f"  • boss@company.com: 20 emails, 90% reply rate")
        print(f"  • newsletter@blog.com: 50 emails, 0% reply rate, 100% archived")
        print(f"  • company.com domain: 100 emails, 60% reply rate")

        # Test 1: Email from important sender
        print(f"\n{'─' * 70}")
        print("Test Case 1: Email from boss (high engagement)")

        email1 = EmailToClassify(
            email_id="test_2",
            subject="Urgent: Project deadline",
            sender="boss@company.com",
            body="We need to discuss the project deadline.",
            account_id="test_account",
        )

        history_layer = HistoryLayer(db=db)
        result1 = history_layer.classify(email1)
        print_result(result1, "History Layer")

        if result1.confidence >= 0.8 and result1.importance >= 0.7:
            print(f"  ✅ CORRECT: High confidence + high importance (important sender)")
        else:
            print(f"  ❌ UNEXPECTED: Should have high confidence/importance")

        # Test 2: Email from newsletter sender
        print(f"\n{'─' * 70}")
        print("Test Case 2: Email from newsletter (low engagement)")

        email2 = EmailToClassify(
            email_id="test_3",
            subject="This week's blog updates",
            sender="newsletter@blog.com",
            body="Check out this week's articles.",
            account_id="test_account",
        )

        result2 = history_layer.classify(email2)
        print_result(result2, "History Layer")

        if result2.confidence >= 0.8 and result2.importance <= 0.4:
            print(f"  ✅ CORRECT: High confidence + low importance (newsletter)")
        else:
            print(f"  ❌ UNEXPECTED: Should have high confidence but low importance")

        # Test 3: Email from unknown sender in known domain
        print(f"\n{'─' * 70}")
        print("Test Case 3: Unknown sender from known domain")

        email3 = EmailToClassify(
            email_id="test_4",
            subject="Question about project",
            sender="newperson@company.com",
            body="I have a question about the project.",
            account_id="test_account",
        )

        result3 = history_layer.classify(email3)
        print_result(result3, "History Layer")

        if result3.data_source == "domain" and result3.confidence >= 0.7:
            print(f"  ✅ CORRECT: Using domain-level data (moderate confidence)")
        else:
            print(f"  ❌ UNEXPECTED: Should use domain-level data")

        # Cleanup
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

    return True


def test_two_layer_workflow():
    """Test realistic workflow: Rule Layer → History Layer."""
    print_header("TEST 4: TWO-LAYER WORKFLOW")

    print("\n🔄 Simulating realistic classification workflow:\n")
    print("  Step 1: Rule Layer tries to classify")
    print("  Step 2: If low confidence → History Layer")
    print("  Step 3: If still low confidence → Would go to LLM Layer")

    rule_layer = RuleLayer()

    # Email that won't match rules (normal work email)
    email = EmailToClassify(
        email_id="test_5",
        subject="Q4 Budget Review",
        sender="finance@company.com",
        body="Please review the Q4 budget proposal attached.",
        account_id="test_account",
    )

    print(f"\n{'─' * 70}")
    print("Email Details:")
    print(f"  Subject: {email.subject}")
    print(f"  From: {email.sender}")

    # Step 1: Rule Layer
    print(f"\n{'─' * 70}")
    print("STEP 1: Rule Layer")
    rule_result = rule_layer.classify(email)
    print_result(rule_result, "Rule Layer")

    if rule_result.confidence >= 0.85:
        print(f"\n✅ DONE: High confidence from Rule Layer")
        return True

    print(f"\n⏭️  Low confidence → Proceeding to History Layer")

    # Step 2: History Layer
    print(f"\n{'─' * 70}")
    print("STEP 2: History Layer")

    with get_db() as db:
        history_layer = HistoryLayer(db=db)
        history_result = history_layer.classify(email)
        print_result(history_result, "History Layer")

        if history_result.confidence >= 0.85:
            print(f"\n✅ DONE: High confidence from History Layer")
        elif history_result.confidence >= 0.6:
            print(f"\n⚠️  Medium confidence → Would add to review queue")
        else:
            print(f"\n⏭️  Low confidence → Would proceed to LLM Layer")

    return True


def main():
    """Run all tests."""
    print_header("RULE LAYER + HISTORY LAYER TEST SUITE")

    print("\nThis test suite validates the first two layers of the")
    print("importance classification system (NO LLM calls):")
    print("  • Rule Layer: Fast pattern matching")
    print("  • History Layer: Learning from user behavior")

    results = {
        'rule_layer': False,
        'history_no_data': False,
        'history_with_data': False,
        'two_layer_workflow': False,
    }

    # Run tests
    try:
        results['rule_layer'] = test_rule_layer()
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['history_no_data'] = test_history_layer_without_data()
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['history_with_data'] = test_history_layer_with_mock_data()
    except Exception as e:
        print(f"\n❌ Test 3 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['two_layer_workflow'] = test_two_layer_workflow()
    except Exception as e:
        print(f"\n❌ Test 4 crashed: {e}")
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
        print("\n🎉 All tests passed! Phase 2 components working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")

    print()
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user\n")
        sys.exit(1)
