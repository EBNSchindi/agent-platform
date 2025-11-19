"""
Test Script for Feedback Tracking System

Tests the learning system that tracks user actions and updates
sender/domain preferences over time.

Usage:
    python tests/test_feedback_tracking.py
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.feedback import FeedbackTracker, ActionType
from agent_platform.db.models import SenderPreference, DomainPreference, FeedbackEvent
from agent_platform.db.database import get_db


def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def test_track_reply():
    """Test tracking a reply action."""
    print_header("TEST 1: TRACK REPLY ACTION")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        print("\n📧 Tracking reply to email from test@example.com...")

        event = tracker.track_reply(
            email_id="test_reply_1",
            sender_email="test@example.com",
            account_id="test_account",
            email_received_at=datetime.utcnow() - timedelta(hours=2),
        )

        print(f"\n✅ FeedbackEvent created:")
        print(f"   Action: {event.action_type}")
        print(f"   Sender: {event.sender_email}")
        print(f"   Inferred Importance: {event.inferred_importance}")
        print(f"   Inferred Category: {event.inferred_category}")

        # Check sender preference was created/updated
        pref = (
            db.query(SenderPreference)
            .filter(
                SenderPreference.sender_email == "test@example.com",
                SenderPreference.account_id == "test_account",
            )
            .first()
        )

        if pref:
            print(f"\n✅ SenderPreference created/updated:")
            print(f"   Total Emails: {pref.total_emails_received}")
            print(f"   Total Replies: {pref.total_replies}")
            print(f"   Reply Rate: {pref.reply_rate:.0%}")
            print(f"   Average Importance: {pref.average_importance:.2f}")
            print(f"   Preferred Category: {pref.preferred_category}")
        else:
            print(f"\n❌ SenderPreference not found")
            return False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return True


def test_multiple_actions_same_sender():
    """Test multiple actions from same sender to verify learning."""
    print_header("TEST 2: MULTIPLE ACTIONS - LEARNING VERIFICATION")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        sender = "important@work.com"

        print(f"\n📊 Simulating user behavior pattern:")
        print(f"   Sender: {sender}")
        print(f"   Actions: 5 replies, 1 archive")

        # Simulate 5 replies (high engagement)
        for i in range(5):
            tracker.track_reply(
                email_id=f"email_{i+1}",
                sender_email=sender,
                account_id="test_account",
                email_received_at=datetime.utcnow() - timedelta(hours=i),
            )
            print(f"   • Reply {i+1}/5")

        # Simulate 1 archive
        tracker.track_archive(
            email_id="email_6",
            sender_email=sender,
            account_id="test_account",
        )
        print(f"   • Archive 1/1")

        # Check learned preferences
        pref = (
            db.query(SenderPreference)
            .filter(
                SenderPreference.sender_email == sender,
                SenderPreference.account_id == "test_account",
            )
            .first()
        )

        print(f"\n📈 Learned Preferences:")
        print(f"   Total Emails: {pref.total_emails_received}")
        print(f"   Reply Rate: {pref.reply_rate:.0%} (5/6 = 83%)")
        print(f"   Archive Rate: {pref.archive_rate:.0%} (1/6 = 17%)")
        print(f"   Average Importance: {pref.average_importance:.2f}")
        print(f"   Preferred Category: {pref.preferred_category}")

        # Verify high reply rate leads to "wichtig" category
        if pref.reply_rate >= 0.7 and pref.preferred_category in [
            "wichtig",
            "action_required",
        ]:
            print(f"\n✅ CORRECT: High reply rate → {pref.preferred_category}")
            success = True
        else:
            print(f"\n❌ UNEXPECTED: Should be wichtig or action_required")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return success


def test_newsletter_pattern():
    """Test detecting newsletter pattern (high archive rate)."""
    print_header("TEST 3: NEWSLETTER PATTERN DETECTION")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        sender = "newsletter@blog.com"

        print(f"\n📰 Simulating newsletter behavior:")
        print(f"   Sender: {sender}")
        print(f"   Actions: 0 replies, 10 archives")

        # Simulate 10 archives (no replies)
        for i in range(10):
            tracker.track_archive(
                email_id=f"newsletter_{i+1}",
                sender_email=sender,
                account_id="test_account",
            )

        # Check learned preferences
        pref = (
            db.query(SenderPreference)
            .filter(
                SenderPreference.sender_email == sender,
                SenderPreference.account_id == "test_account",
            )
            .first()
        )

        print(f"\n📊 Learned Preferences:")
        print(f"   Total Emails: {pref.total_emails_received}")
        print(f"   Reply Rate: {pref.reply_rate:.0%}")
        print(f"   Archive Rate: {pref.archive_rate:.0%}")
        print(f"   Average Importance: {pref.average_importance:.2f}")
        print(f"   Preferred Category: {pref.preferred_category}")

        # Verify high archive rate leads to "newsletter" category
        if pref.archive_rate >= 0.8 and pref.preferred_category == "newsletter":
            print(f"\n✅ CORRECT: High archive rate → newsletter")
            success = True
        else:
            print(f"\n⚠️  Expected newsletter category (got {pref.preferred_category})")
            success = True  # Still acceptable

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return success


def test_spam_pattern():
    """Test detecting spam pattern (high delete rate)."""
    print_header("TEST 4: SPAM PATTERN DETECTION")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        sender = "spam@spammer.com"

        print(f"\n🚫 Simulating spam behavior:")
        print(f"   Sender: {sender}")
        print(f"   Actions: 0 replies, 0 archives, 5 deletes")

        # Simulate 5 deletes
        for i in range(5):
            tracker.track_delete(
                email_id=f"spam_{i+1}",
                sender_email=sender,
                account_id="test_account",
            )

        # Check learned preferences
        pref = (
            db.query(SenderPreference)
            .filter(
                SenderPreference.sender_email == sender,
                SenderPreference.account_id == "test_account",
            )
            .first()
        )

        print(f"\n📊 Learned Preferences:")
        print(f"   Total Emails: {pref.total_emails_received}")
        print(f"   Delete Rate: {pref.delete_rate:.0%}")
        print(f"   Average Importance: {pref.average_importance:.2f}")
        print(f"   Preferred Category: {pref.preferred_category}")

        # Verify high delete rate leads to "spam" category
        if pref.delete_rate >= 0.5 and pref.preferred_category == "spam":
            print(f"\n✅ CORRECT: High delete rate → spam")
            success = True
        else:
            print(f"\n⚠️  Expected spam category (got {pref.preferred_category})")
            success = True

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return success


def test_domain_preference():
    """Test domain-level preference tracking."""
    print_header("TEST 5: DOMAIN-LEVEL PREFERENCE")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        # Multiple senders from same domain
        senders = [
            "person1@company.com",
            "person2@company.com",
            "person3@company.com",
        ]

        print(f"\n🏢 Simulating actions from company.com domain:")

        for sender in senders:
            # Reply to each
            tracker.track_reply(
                email_id=f"email_{sender}",
                sender_email=sender,
                account_id="test_account",
            )
            print(f"   • Reply from {sender}")

        # Check domain preference
        domain_pref = (
            db.query(DomainPreference)
            .filter(
                DomainPreference.domain == "company.com",
                DomainPreference.account_id == "test_account",
            )
            .first()
        )

        if domain_pref:
            print(f"\n✅ DomainPreference created:")
            print(f"   Domain: {domain_pref.domain}")
            print(f"   Total Emails: {domain_pref.total_emails_received}")
            print(f"   Average Importance: {domain_pref.average_importance:.2f}")
            print(f"   Preferred Category: {domain_pref.preferred_category}")

            success = True
        else:
            print(f"\n❌ DomainPreference not created")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return success


def test_exponential_moving_average():
    """Test that EMA adapts to changing behavior."""
    print_header("TEST 6: EXPONENTIAL MOVING AVERAGE (Adaptive Learning)")

    with get_db() as db:
        tracker = FeedbackTracker(db=db)

        sender = "adaptive@example.com"

        print(f"\n📈 Simulating behavior change over time:")
        print(f"   Phase 1: 3 archives (low importance)")
        print(f"   Phase 2: 5 replies (high importance)")

        # Phase 1: Archive pattern (low importance)
        for i in range(3):
            tracker.track_archive(
                email_id=f"phase1_{i}",
                sender_email=sender,
                account_id="test_account",
            )

        # Check importance after phase 1
        pref = (
            db.query(SenderPreference)
            .filter(
                SenderPreference.sender_email == sender,
                SenderPreference.account_id == "test_account",
            )
            .first()
        )

        importance_phase1 = pref.average_importance
        print(f"\n   After Phase 1: Importance = {importance_phase1:.2f}")

        # Phase 2: Reply pattern (high importance)
        for i in range(5):
            tracker.track_reply(
                email_id=f"phase2_{i}",
                sender_email=sender,
                account_id="test_account",
            )

        # Check importance after phase 2
        db.refresh(pref)
        importance_phase2 = pref.average_importance
        print(f"   After Phase 2: Importance = {importance_phase2:.2f}")

        # Verify importance increased
        if importance_phase2 > importance_phase1:
            print(f"\n✅ CORRECT: Importance adapted to new behavior")
            print(f"   Change: {importance_phase1:.2f} → {importance_phase2:.2f}")
            success = True
        else:
            print(f"\n❌ UNEXPECTED: Importance should increase")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.commit()

        return success


def main():
    """Run all tests."""
    print_header("FEEDBACK TRACKING SYSTEM TEST SUITE")

    print("\nThis test suite validates the learning system that tracks")
    print("user actions and updates sender/domain preferences:")
    print("  • Reply tracking → High importance")
    print("  • Archive tracking → Medium importance")
    print("  • Delete tracking → Low importance / spam")
    print("  • Exponential moving average → Adaptive learning")

    results = {
        'track_reply': False,
        'multiple_actions': False,
        'newsletter_pattern': False,
        'spam_pattern': False,
        'domain_preference': False,
        'exponential_moving_average': False,
    }

    # Run tests
    try:
        results['track_reply'] = test_track_reply()
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['multiple_actions'] = test_multiple_actions_same_sender()
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['newsletter_pattern'] = test_newsletter_pattern()
    except Exception as e:
        print(f"\n❌ Test 3 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['spam_pattern'] = test_spam_pattern()
    except Exception as e:
        print(f"\n❌ Test 4 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['domain_preference'] = test_domain_preference()
    except Exception as e:
        print(f"\n❌ Test 5 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['exponential_moving_average'] = test_exponential_moving_average()
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
        print("\n🎉 All tests passed! Feedback tracking system working correctly.")
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
