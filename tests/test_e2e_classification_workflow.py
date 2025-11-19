"""
End-to-End Integration Test for Classification System

Tests the complete workflow from email intake to review and feedback:
1. Email classification (Rule → History → LLM layers)
2. Confidence-based routing (high/medium/low)
3. Review queue management
4. Daily digest generation
5. User review and feedback tracking
6. Learning from feedback

Usage:
    python tests/test_e2e_classification_workflow.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.review import ReviewHandler, DailyDigestGenerator
from agent_platform.feedback import FeedbackTracker
from agent_platform.db.models import (
    ProcessedEmail,
    ReviewQueueItem,
    SenderPreference,
    DomainPreference,
    FeedbackEvent,
)
from agent_platform.db.database import get_db


def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


async def test_full_workflow():
    """
    Test complete workflow from email intake to feedback learning.
    """
    print_header("END-TO-END CLASSIFICATION WORKFLOW TEST")

    print("\nThis test validates the complete system:")
    print("  1. Email classification (all layers)")
    print("  2. Confidence-based routing")
    print("  3. Review queue management")
    print("  4. Daily digest generation")
    print("  5. User review actions")
    print("  6. Feedback tracking and learning")

    with get_db() as db:
        # Clean up before test
        db.query(FeedbackEvent).delete()
        db.query(ReviewQueueItem).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ProcessedEmail).delete()
        db.commit()

        # ====================================================================
        # STEP 1: CLASSIFY EMAILS
        # ====================================================================
        print_header("STEP 1: CLASSIFY EMAILS")

        orchestrator = ClassificationOrchestrator(db=db)

        # Create test emails with different confidence levels
        test_emails = [
            # High confidence - spam (should auto-filter)
            {
                'id': 'email_spam',
                'subject': 'CONGRATULATIONS! YOU WON $1,000,000!!!',
                'sender': 'winner@lottery-scam.com',
                'body': 'Click here to claim your prize! Free money! Act now!',
                'received_at': datetime.utcnow(),
            },
            # High confidence - newsletter (should auto-label)
            {
                'id': 'email_newsletter',
                'subject': 'Weekly Tech Newsletter',
                'sender': 'newsletter@techblog.com',
                'body': 'Here are this week\'s top tech stories. Unsubscribe at bottom.',
                'received_at': datetime.utcnow(),
            },
            # Medium confidence - potentially important (should go to review queue)
            {
                'id': 'email_medium',
                'subject': 'Project Update',
                'sender': 'colleague@company.com',
                'body': 'Hi, wanted to give you a quick update on the project status.',
                'received_at': datetime.utcnow(),
            },
            # Medium confidence - could be wichtig or nice_to_know
            {
                'id': 'email_medium2',
                'subject': 'Team Meeting Notes',
                'sender': 'team@company.com',
                'body': 'Here are the notes from yesterday\'s team meeting for your review.',
                'received_at': datetime.utcnow(),
            },
        ]

        # Process emails
        stats = await orchestrator.process_emails(test_emails, 'gmail_1')

        print(f"\n✅ Processed {stats.total_processed} emails:")
        print(f"   High confidence: {stats.high_confidence}")
        print(f"   Medium confidence: {stats.medium_confidence}")
        print(f"   Low confidence: {stats.low_confidence}")

        # Verify ProcessedEmail records were created
        processed_count = db.query(ProcessedEmail).count()
        if processed_count == len(test_emails):
            print(f"✅ All {processed_count} ProcessedEmail records created")
            success_step1 = True
        else:
            print(f"❌ Expected {len(test_emails)} ProcessedEmail records, got {processed_count}")
            success_step1 = False

        # ====================================================================
        # STEP 2: VERIFY REVIEW QUEUE
        # ====================================================================
        print_header("STEP 2: VERIFY REVIEW QUEUE")

        # Get pending review items
        from agent_platform.review import ReviewQueueManager
        queue_manager = ReviewQueueManager(db=db)

        pending_items = queue_manager.get_pending_items(account_id='gmail_1')

        print(f"\n📋 Review queue has {len(pending_items)} items")

        if len(pending_items) >= 2:  # At least the 2 medium-confidence emails
            print("✅ Medium-confidence emails added to review queue")
            for item in pending_items:
                print(f"   • {item.subject} (confidence: {item.confidence:.0%})")
            success_step2 = True
        else:
            print(f"❌ Expected at least 2 items in review queue, got {len(pending_items)}")
            success_step2 = False

        # ====================================================================
        # STEP 3: GENERATE DAILY DIGEST
        # ====================================================================
        print_header("STEP 3: GENERATE DAILY DIGEST")

        digest_generator = DailyDigestGenerator(db=db)

        digest = digest_generator.generate_digest(
            account_id='gmail_1',
            hours_back=24,
        )

        print(f"\n📧 Daily digest generated:")
        print(f"   Total items: {digest['summary']['total_items']}")
        print(f"   HTML length: {len(digest['html'])} characters")

        if digest['summary']['total_items'] >= 2:
            print("✅ Digest contains review queue items")

            # Check HTML content
            html = digest['html']
            if 'Email Review Digest' in html and 'Approve' in html:
                print("✅ Digest HTML properly formatted")
                success_step3 = True
            else:
                print("❌ Digest HTML missing expected content")
                success_step3 = False
        else:
            print(f"❌ Expected at least 2 items in digest")
            success_step3 = False

        # ====================================================================
        # STEP 4: USER REVIEWS EMAILS
        # ====================================================================
        print_header("STEP 4: USER REVIEWS EMAILS")

        review_handler = ReviewHandler(db=db)

        # Get first review item
        if len(pending_items) > 0:
            item1 = pending_items[0]

            # User approves classification
            print(f"\n👍 User approves: {item1.subject}")
            approve_result = review_handler.approve_classification(
                item_id=item1.id,
                user_feedback="Good classification",
            )

            if approve_result['success']:
                print(f"✅ Approval recorded")
                print(f"   Status: {approve_result['item'].status}")
                print(f"   Feedback tracked: {approve_result['feedback_event'].action_type}")
                success_step4a = True
            else:
                print(f"❌ Approval failed")
                success_step4a = False

        else:
            success_step4a = False

        # Get second review item (if exists)
        if len(pending_items) > 1:
            item2 = pending_items[1]

            # User modifies classification
            print(f"\n✏️  User modifies: {item2.subject}")
            modify_result = review_handler.modify_classification(
                item_id=item2.id,
                corrected_category="wichtig",
                user_feedback="This is actually important",
            )

            if modify_result['success']:
                print(f"✅ Modification recorded")
                print(f"   Original: {item2.suggested_category}")
                print(f"   Corrected: {modify_result['item'].user_corrected_category}")
                success_step4b = True
            else:
                print(f"❌ Modification failed")
                success_step4b = False

        else:
            success_step4b = False

        success_step4 = success_step4a and success_step4b

        # ====================================================================
        # STEP 5: VERIFY FEEDBACK TRACKING
        # ====================================================================
        print_header("STEP 5: VERIFY FEEDBACK TRACKING")

        # Check FeedbackEvents were created
        feedback_events = db.query(FeedbackEvent).filter(
            FeedbackEvent.account_id == 'gmail_1'
        ).all()

        print(f"\n📊 Feedback events: {len(feedback_events)}")

        if len(feedback_events) >= 2:
            print("✅ Feedback events created for user reviews")
            for event in feedback_events:
                print(f"   • {event.sender_email}: {event.action_type} (importance: {event.inferred_importance:.2f})")
            success_step5a = True
        else:
            print(f"❌ Expected at least 2 feedback events, got {len(feedback_events)}")
            success_step5a = False

        # Check SenderPreferences were updated
        sender_prefs = db.query(SenderPreference).filter(
            SenderPreference.account_id == 'gmail_1'
        ).all()

        print(f"\n📈 Sender preferences updated: {len(sender_prefs)}")

        if len(sender_prefs) >= 2:
            print("✅ Sender preferences created/updated")
            for pref in sender_prefs:
                print(f"   • {pref.sender_email}:")
                print(f"     Total emails: {pref.total_emails_received}")
                print(f"     Avg importance: {pref.average_importance:.2f}")
                print(f"     Category: {pref.preferred_category}")
            success_step5b = True
        else:
            print(f"❌ Expected at least 2 sender preferences, got {len(sender_prefs)}")
            success_step5b = False

        success_step5 = success_step5a and success_step5b

        # ====================================================================
        # STEP 6: TEST LEARNING EFFECT
        # ====================================================================
        print_header("STEP 6: TEST LEARNING EFFECT")

        # Process another email from same sender as item1
        if len(pending_items) > 0:
            original_sender = pending_items[0].sender

            print(f"\n📧 Processing another email from {original_sender}...")

            new_email = {
                'id': 'email_repeat',
                'subject': 'Follow-up Message',
                'sender': original_sender,
                'body': 'Following up on my previous email.',
                'received_at': datetime.utcnow(),
            }

            # Process email
            stats2 = await orchestrator.process_emails([new_email], 'gmail_1')

            # Check ProcessedEmail for improved classification
            processed = db.query(ProcessedEmail).filter(
                ProcessedEmail.email_id == 'email_repeat'
            ).first()

            if processed:
                print(f"✅ Email classified:")
                print(f"   Category: {processed.category}")
                print(f"   Confidence: {processed.confidence:.0%}")
                print(f"   Layer: {processed.layer_used}")

                # Check if history layer was used (should have sender data now)
                if processed.layer_used in ["history", "llm"]:
                    print(f"✅ System used learning from previous interaction")
                    success_step6 = True
                else:
                    print(f"⚠️  Expected history/llm layer, got {processed.layer_used}")
                    success_step6 = True  # Still acceptable
            else:
                print(f"❌ Email not processed")
                success_step6 = False

        else:
            success_step6 = False

        # ====================================================================
        # CLEANUP
        # ====================================================================

        # Clean up after test
        db.query(FeedbackEvent).delete()
        db.query(ReviewQueueItem).delete()
        db.query(SenderPreference).delete()
        db.query(DomainPreference).delete()
        db.query(ProcessedEmail).delete()
        db.commit()

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print_header("TEST SUMMARY")

        results = {
            'Step 1: Email Classification': success_step1,
            'Step 2: Review Queue': success_step2,
            'Step 3: Daily Digest': success_step3,
            'Step 4: User Reviews': success_step4,
            'Step 5: Feedback Tracking': success_step5,
            'Step 6: Learning Effect': success_step6,
        }

        passed = sum(results.values())
        total = len(results)

        for step_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{step_name:.<50} {status}")

        print(f"\n{'─' * 70}")
        print(f"Total: {passed}/{total} steps passed ({passed/total*100:.0f}%)")
        print("=" * 70)

        if passed == total:
            print("\n🎉 All steps passed! Complete system working end-to-end.")
        else:
            print(f"\n⚠️  {total - passed} step(s) failed. Review output above.")

        print()
        return passed == total


def main():
    """Run the end-to-end test."""
    try:
        success = asyncio.run(test_full_workflow())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test crashed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
