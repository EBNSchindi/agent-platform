"""
Test Script for Review System

Tests the review queue, daily digest generation, and user review handling.

Usage:
    python tests/test_review_system.py
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.review import ReviewQueueManager, DailyDigestGenerator, ReviewHandler
from agent_platform.classification.models import ClassificationResult, ImportanceCategory
from agent_platform.db.models import ReviewQueueItem, SenderPreference, DomainPreference, FeedbackEvent
from agent_platform.db.database import get_db


def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def test_add_to_queue():
    """Test adding items to review queue."""
    print_header("TEST 1: ADD TO REVIEW QUEUE")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)

        print("\n📧 Adding medium-confidence email to review queue...")

        # Create a classification result
        classification = ClassificationResult(
            category="wichtig",
            importance=0.75,
            confidence=0.72,  # Medium confidence
            reasoning="Email from boss about project deadline",
            layer_used="llm",
            processing_time_ms=150.0,
        )

        # Add to queue
        item = queue_manager.add_to_queue(
            email_id="test_email_1",
            account_id="gmail_1",
            subject="Project Deadline Update",
            sender="boss@company.com",
            snippet="We need to discuss the project timeline...",
            classification=classification,
        )

        print(f"\n✅ Added to queue:")
        print(f"   Item ID: {item.id}")
        print(f"   Subject: {item.subject}")
        print(f"   Category: {item.suggested_category}")
        print(f"   Confidence: {item.confidence:.0%}")
        print(f"   Importance: {item.importance_score:.0%}")
        print(f"   Status: {item.status}")

        # Verify item was added
        retrieved_item = queue_manager.get_item_by_id(item.id)

        if retrieved_item and retrieved_item.status == "pending":
            print(f"\n✅ Item successfully retrieved from queue")
            success = True
        else:
            print(f"\n❌ Failed to retrieve item")
            success = False

        # Cleanup
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_get_pending_items():
    """Test retrieving pending items from queue."""
    print_header("TEST 2: GET PENDING ITEMS")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)

        print("\n📧 Adding 3 items with different importance scores...")

        # Add 3 items with different importance
        items_data = [
            ("High Importance", "urgent@client.com", 0.9, 0.75),
            ("Medium Importance", "info@company.com", 0.6, 0.70),
            ("Low Importance", "newsletter@blog.com", 0.3, 0.65),
        ]

        added_items = []
        for subject, sender, importance, confidence in items_data:
            classification = ClassificationResult(
                category="wichtig",
                importance=importance,
                confidence=confidence,
                reasoning="Test item",
                layer_used="llm",
                processing_time_ms=100.0,
            )

            item = queue_manager.add_to_queue(
                email_id=f"test_{subject.replace(' ', '_')}",
                account_id="gmail_1",
                subject=subject,
                sender=sender,
                snippet="Test snippet...",
                classification=classification,
            )
            added_items.append(item)
            print(f"   • Added: {subject} (importance: {importance:.0%})")

        # Get pending items (should be ordered by importance DESC)
        pending = queue_manager.get_pending_items(account_id="gmail_1")

        print(f"\n📊 Retrieved {len(pending)} pending items:")
        for i, item in enumerate(pending, 1):
            print(f"   {i}. {item.subject} (importance: {item.importance_score:.0%})")

        # Verify order (highest importance first)
        if len(pending) == 3:
            if pending[0].importance_score >= pending[1].importance_score >= pending[2].importance_score:
                print(f"\n✅ Items correctly ordered by importance")
                success = True
            else:
                print(f"\n❌ Items not correctly ordered")
                success = False
        else:
            print(f"\n❌ Expected 3 items, got {len(pending)}")
            success = False

        # Cleanup
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_daily_digest_generation():
    """Test daily digest HTML generation."""
    print_header("TEST 3: DAILY DIGEST GENERATION")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)
        digest_generator = DailyDigestGenerator(db=db)

        print("\n📧 Adding items for digest...")

        # Add items with different categories
        items_data = [
            ("wichtig", "Important Email", "boss@company.com", 0.85, 0.75),
            ("action_required", "Urgent Request", "client@example.com", 0.90, 0.70),
            ("newsletter", "Weekly Update", "newsletter@blog.com", 0.35, 0.65),
        ]

        for category, subject, sender, importance, confidence in items_data:
            classification = ClassificationResult(
                category=category,
                importance=importance,
                confidence=confidence,
                reasoning=f"This is a {category} email",
                layer_used="llm",
                processing_time_ms=100.0,
            )

            queue_manager.add_to_queue(
                email_id=f"test_{category}",
                account_id="gmail_1",
                subject=subject,
                sender=sender,
                snippet="Test snippet for digest...",
                classification=classification,
            )
            print(f"   • Added: {subject} ({category})")

        # Generate digest
        digest = digest_generator.generate_digest(
            account_id="gmail_1",
            hours_back=24,
        )

        print(f"\n📊 Digest generated:")
        print(f"   Total items: {digest['summary']['total_items']}")
        print(f"   Categories: {list(digest['summary']['by_category'].keys())}")

        # Verify HTML was generated
        if digest['html'] and len(digest['html']) > 100:
            print(f"   HTML length: {len(digest['html'])} characters")
            print(f"\n✅ HTML digest generated successfully")

            # Check HTML contains expected elements
            html = digest['html']
            checks = [
                ("Email Review Digest" in html, "Contains title"),
                ("wichtig" in html.lower(), "Contains category 'wichtig'"),
                ("action_required" in html.lower() or "action required" in html.lower(), "Contains category 'action_required'"),
                ("newsletter" in html.lower(), "Contains category 'newsletter'"),
                ("Approve" in html, "Contains approve button"),
                ("Reject" in html, "Contains reject button"),
            ]

            print(f"\n   HTML Content Checks:")
            all_passed = True
            for check, description in checks:
                status = "✅" if check else "❌"
                print(f"   {status} {description}")
                if not check:
                    all_passed = False

            success = all_passed
        else:
            print(f"\n❌ HTML digest not generated or too short")
            success = False

        # Cleanup
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_approve_classification():
    """Test approving a classification."""
    print_header("TEST 4: APPROVE CLASSIFICATION")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)
        review_handler = ReviewHandler(db=db)

        print("\n📧 Adding item to queue...")

        # Add item
        classification = ClassificationResult(
            category="wichtig",
            importance=0.80,
            confidence=0.72,
            reasoning="Email from colleague about meeting",
            layer_used="llm",
            processing_time_ms=100.0,
        )

        item = queue_manager.add_to_queue(
            email_id="test_approve",
            account_id="gmail_1",
            subject="Meeting Tomorrow",
            sender="colleague@company.com",
            snippet="Can we meet tomorrow at 10am?",
            classification=classification,
        )

        print(f"   Item ID: {item.id}")
        print(f"   Status: {item.status}")

        # Approve the classification
        print(f"\n👍 Approving classification...")
        result = review_handler.approve_classification(
            item_id=item.id,
            user_feedback="Good classification, I replied to this email",
        )

        if result['success']:
            print(f"\n✅ Classification approved:")
            print(f"   Status: {result['item'].status}")
            print(f"   User Approved: {result['item'].user_approved}")
            print(f"   Reviewed At: {result['item'].reviewed_at}")

            # Check feedback was tracked
            feedback_event = result['feedback_event']
            print(f"\n✅ Feedback tracked:")
            print(f"   Action Type: {feedback_event.action_type}")
            print(f"   Inferred Importance: {feedback_event.inferred_importance:.2f}")

            # Check sender preference was updated
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == "colleague@company.com",
                SenderPreference.account_id == "gmail_1",
            ).first()

            if pref:
                print(f"\n✅ Sender preference updated:")
                print(f"   Total Emails: {pref.total_emails_received}")
                print(f"   Average Importance: {pref.average_importance:.2f}")
                success = True
            else:
                print(f"\n❌ Sender preference not created")
                success = False
        else:
            print(f"\n❌ Approval failed: {result.get('error')}")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_reject_classification():
    """Test rejecting a classification."""
    print_header("TEST 5: REJECT CLASSIFICATION")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)
        review_handler = ReviewHandler(db=db)

        print("\n📧 Adding item to queue...")

        # Add item (system thinks it's wichtig, user will reject)
        classification = ClassificationResult(
            category="wichtig",
            importance=0.75,
            confidence=0.70,
            reasoning="Email from marketing list",
            layer_used="llm",
            processing_time_ms=100.0,
        )

        item = queue_manager.add_to_queue(
            email_id="test_reject",
            account_id="gmail_1",
            subject="Special Offer Inside!",
            sender="marketing@shop.com",
            snippet="Limited time offer...",
            classification=classification,
        )

        print(f"   Suggested Category: {item.suggested_category}")

        # Reject and correct to newsletter
        print(f"\n👎 Rejecting classification (correcting to 'newsletter')...")
        result = review_handler.reject_classification(
            item_id=item.id,
            corrected_category="newsletter",
            user_feedback="This is actually a marketing newsletter",
        )

        if result['success']:
            print(f"\n✅ Classification rejected:")
            print(f"   Status: {result['item'].status}")
            print(f"   User Approved: {result['item'].user_approved}")
            print(f"   Corrected Category: {result['item'].user_corrected_category}")

            # Check feedback was tracked
            feedback_event = result['feedback_event']
            print(f"\n✅ Feedback tracked:")
            print(f"   Action Type: {feedback_event.action_type}")

            # Check sender preference reflects rejection
            pref = db.query(SenderPreference).filter(
                SenderPreference.sender_email == "marketing@shop.com",
                SenderPreference.account_id == "gmail_1",
            ).first()

            if pref:
                print(f"\n✅ Sender preference updated:")
                print(f"   Average Importance: {pref.average_importance:.2f}")
                print(f"   (Should be lower due to rejection)")
                success = True
            else:
                print(f"\n❌ Sender preference not created")
                success = False
        else:
            print(f"\n❌ Rejection failed: {result.get('error')}")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_modify_classification():
    """Test modifying a classification."""
    print_header("TEST 6: MODIFY CLASSIFICATION")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)
        review_handler = ReviewHandler(db=db)

        print("\n📧 Adding item to queue...")

        # Add item (system thinks it's nice_to_know, user will upgrade)
        classification = ClassificationResult(
            category="nice_to_know",
            importance=0.50,
            confidence=0.68,
            reasoning="General update from team",
            layer_used="llm",
            processing_time_ms=100.0,
        )

        item = queue_manager.add_to_queue(
            email_id="test_modify",
            account_id="gmail_1",
            subject="Team Update",
            sender="team@company.com",
            snippet="Important changes to our workflow...",
            classification=classification,
        )

        print(f"   Suggested Category: {item.suggested_category}")

        # Modify to action_required
        print(f"\n✏️  Modifying classification to 'action_required'...")
        result = review_handler.modify_classification(
            item_id=item.id,
            corrected_category="action_required",
            user_feedback="This requires immediate attention",
        )

        if result['success']:
            print(f"\n✅ Classification modified:")
            print(f"   Status: {result['item'].status}")
            print(f"   Original Category: {item.suggested_category}")
            print(f"   Corrected Category: {result['item'].user_corrected_category}")

            # Verify status is "modified"
            if result['item'].status == "modified":
                print(f"   Status correctly set to 'modified'")

                # Check feedback was tracked
                feedback_event = result['feedback_event']
                print(f"\n✅ Feedback tracked:")
                print(f"   Action Type: {feedback_event.action_type}")
                print(f"   Inferred Importance: {feedback_event.inferred_importance:.2f}")
                success = True
            else:
                print(f"\n❌ Status not set to 'modified'")
                success = False
        else:
            print(f"\n❌ Modification failed: {result.get('error')}")
            success = False

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def test_queue_statistics():
    """Test queue statistics."""
    print_header("TEST 7: QUEUE STATISTICS")

    with get_db() as db:
        queue_manager = ReviewQueueManager(db=db)
        review_handler = ReviewHandler(db=db)

        print("\n📧 Adding and reviewing multiple items...")

        # Add and review 5 items with different outcomes
        items_data = [
            ("wichtig", "approve", None),
            ("action_required", "approve", None),
            ("newsletter", "reject", "spam"),
            ("nice_to_know", "modify", "wichtig"),
            ("spam", "approve", None),
        ]

        for category, action, corrected in items_data:
            classification = ClassificationResult(
                category=category,
                importance=0.70,
                confidence=0.70,
                reasoning="Test item",
                layer_used="llm",
                processing_time_ms=100.0,
            )

            item = queue_manager.add_to_queue(
                email_id=f"test_{category}_{action}",
                account_id="gmail_1",
                subject=f"Test {category}",
                sender=f"sender@{category}.com",
                snippet="Test snippet",
                classification=classification,
            )

            # Process based on action
            if action == "approve":
                review_handler.approve_classification(item.id)
            elif action == "reject":
                review_handler.reject_classification(item.id, corrected_category=corrected)
            elif action == "modify":
                review_handler.modify_classification(item.id, corrected_category=corrected)

            print(f"   • {category}: {action}" + (f" → {corrected}" if corrected else ""))

        # Get statistics
        stats = queue_manager.get_queue_statistics(account_id="gmail_1")

        print(f"\n📊 Queue Statistics:")
        print(f"   Total Items: {stats['total_items']}")
        print(f"   Pending: {stats['pending']}")
        print(f"   Approved: {stats['approved']}")
        print(f"   Rejected: {stats['rejected']}")
        print(f"   Modified: {stats['modified']}")

        # Verify counts
        # Note: reject with corrected_category becomes "modified" status
        # So we expect: 3 approved, 0 rejected, 2 modified
        if stats['total_items'] == 5:
            if stats['approved'] == 3 and stats['rejected'] == 0 and stats['modified'] == 2:
                print(f"\n✅ Statistics correct")
                success = True
            else:
                print(f"\n❌ Status counts incorrect")
                print(f"   Expected: approved=3, rejected=0, modified=2")
                print(f"   Got: approved={stats['approved']}, rejected={stats['rejected']}, modified={stats['modified']}")
                success = False
        else:
            print(f"\n❌ Expected 5 total items, got {stats['total_items']}")
            success = False

        # Get review statistics
        review_stats = review_handler.get_review_statistics(account_id="gmail_1")

        print(f"\n📈 Review Statistics:")
        print(f"   Total Reviewed: {review_stats['total_reviewed']}")
        print(f"   Approval Rate: {review_stats['approval_rate']:.0%}")
        print(f"   Modification Rate: {review_stats['modification_rate']:.0%}")

        # Cleanup
        db.query(FeedbackEvent).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ReviewQueueItem).delete()
        db.commit()

        return success


def main():
    """Run all tests."""
    print_header("REVIEW SYSTEM TEST SUITE")

    print("\nThis test suite validates the review system:")
    print("  • Adding items to review queue")
    print("  • Retrieving pending items")
    print("  • Generating daily digest emails")
    print("  • Approving/rejecting/modifying classifications")
    print("  • Integration with feedback tracking")
    print("  • Queue and review statistics")

    results = {
        'add_to_queue': False,
        'get_pending_items': False,
        'daily_digest_generation': False,
        'approve_classification': False,
        'reject_classification': False,
        'modify_classification': False,
        'queue_statistics': False,
    }

    # Run tests
    try:
        results['add_to_queue'] = test_add_to_queue()
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['get_pending_items'] = test_get_pending_items()
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['daily_digest_generation'] = test_daily_digest_generation()
    except Exception as e:
        print(f"\n❌ Test 3 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['approve_classification'] = test_approve_classification()
    except Exception as e:
        print(f"\n❌ Test 4 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['reject_classification'] = test_reject_classification()
    except Exception as e:
        print(f"\n❌ Test 5 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['modify_classification'] = test_modify_classification()
    except Exception as e:
        print(f"\n❌ Test 6 crashed: {e}")
        import traceback
        traceback.print_exc()

    try:
        results['queue_statistics'] = test_queue_statistics()
    except Exception as e:
        print(f"\n❌ Test 7 crashed: {e}")
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
        print("\n🎉 All tests passed! Review system working correctly.")
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
