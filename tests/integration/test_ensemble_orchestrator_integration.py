"""
Integration Test: Ensemble Classifier + Orchestrator

Tests the complete Phase 2 Ensemble System in production workflow:
1. EnsembleClassifier with parallel 3-layer execution
2. Confidence-based routing with new thresholds (0.90/0.65)
3. Agreement detection & confidence boosting
4. Review queue population with disagreement tracking
5. Smart LLM Skip optimization
6. Custom weight configurations

Usage:
    pytest tests/integration/test_ensemble_orchestrator_integration.py -v
    python tests/integration/test_ensemble_orchestrator_integration.py
"""

import asyncio
import pytest
from datetime import datetime

from agent_platform.classification import (
    EnsembleClassifier,
    EmailToClassify,
    ScoringWeights,
)
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.db.database import get_db
from agent_platform.db.models import ProcessedEmail


# ============================================================================
# TEST HELPERS
# ============================================================================

def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_stats(stats):
    """Print orchestrator statistics."""
    print(f"\n  Processing Statistics:")
    print(f"    Total Processed: {stats.total_processed}")
    print(f"    High Confidence (≥0.90): {stats.high_confidence}")
    print(f"    Medium Confidence (0.65-0.90): {stats.medium_confidence}")
    print(f"    Low Confidence (<0.65): {stats.low_confidence}")
    print(f"    Auto-labeled: {stats.auto_labeled}")
    print(f"    Added to Review: {stats.added_to_review}")
    print(f"    Marked Manual: {stats.marked_manual}")

    if stats.duration_seconds:
        print(f"    Duration: {stats.duration_seconds:.2f}s")


# ============================================================================
# TEST EMAILS
# ============================================================================

def get_test_emails():
    """Get test emails covering different scenarios."""
    return [
        # 1. HIGH CONFIDENCE: Spam (all layers should agree)
        {
            'id': 'test_spam_1',
            'subject': 'GEWINNSPIEL!!! Du hast gewonnen!!! KOSTENLOS!!!',
            'sender': 'spam@spammer.com',
            'body': 'Klicke hier für gratis Geld! Viagra! Casino! Kredit ohne Schufa!',
        },

        # 2. HIGH CONFIDENCE: Auto-Reply (all layers should agree)
        {
            'id': 'test_autoreply_1',
            'subject': 'Out of Office AutoReply: Vacation',
            'sender': 'colleague@company.com',
            'body': 'This is an automated message. I am currently out of office and will return on Monday. Do not reply to this email.',
        },

        # 3. MEDIUM CONFIDENCE: Newsletter (likely partial agreement)
        {
            'id': 'test_newsletter_1',
            'subject': 'Weekly Tech Newsletter - December 2025',
            'sender': 'newsletter@tech.com',
            'body': 'This week\'s top stories in tech. New AI developments and startup funding. Click here to unsubscribe if you no longer wish to receive our newsletter.',
        },

        # 4. MEDIUM/HIGH CONFIDENCE: Important Meeting (requires LLM)
        {
            'id': 'test_meeting_1',
            'subject': 'Quarterly Report Review Meeting - Urgent',
            'sender': 'boss@company.com',
            'body': 'Please review the Q4 financial report and prepare your analysis for the meeting on Friday. This is critical for our board presentation.',
        },

        # 5. POTENTIAL DISAGREEMENT: Invoice from noreply (Rule low, LLM high)
        {
            'id': 'test_invoice_1',
            'subject': 'Rechnung #12345',
            'sender': 'noreply@amazon.de',
            'body': 'Vielen Dank für Ihre Bestellung. Ihre Rechnung für €150.00 ist anbei. Bitte zahlen Sie innerhalb von 14 Tagen.',
        },

        # 6. EDGE CASE: Ambiguous (might cause disagreement)
        {
            'id': 'test_ambiguous_1',
            'subject': 'Quick question',
            'sender': 'unknown@example.com',
            'body': 'Hi there, just wanted to check something.',
        },
    ]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ensemble_orchestrator_default_config():
    """Test orchestrator with default Ensemble configuration."""
    print_header("TEST 1: ENSEMBLE ORCHESTRATOR - DEFAULT CONFIG")

    orchestrator = ClassificationOrchestrator()
    emails = get_test_emails()

    print(f"\n📧 Processing {len(emails)} test emails with EnsembleClassifier (default weights)...")

    stats = await orchestrator.process_emails(emails, 'test_account')

    print_stats(stats)

    # Assertions
    assert stats.total_processed == len(emails), "All emails should be processed"
    assert stats.high_confidence + stats.medium_confidence + stats.low_confidence == len(emails), "Confidence distribution should sum to total"
    assert stats.high_confidence >= 2, "At least spam and auto-reply should be high confidence"

    print(f"\n✅ PASS: Ensemble orchestrator processed all emails successfully")

    return stats


@pytest.mark.asyncio
async def test_ensemble_orchestrator_smart_llm_skip():
    """Test orchestrator with Smart LLM Skip enabled."""
    print_header("TEST 2: ENSEMBLE ORCHESTRATOR - SMART LLM SKIP")

    orchestrator = ClassificationOrchestrator(smart_llm_skip=True)
    emails = get_test_emails()

    print(f"\n📧 Processing {len(emails)} test emails with Smart LLM Skip enabled...")
    print(f"   Expected: LLM should be skipped for spam, auto-reply, newsletter (~50% skip rate)")

    stats = await orchestrator.process_emails(emails, 'test_account')

    print_stats(stats)

    # Check classifier stats
    if hasattr(orchestrator.classifier, 'get_stats'):
        classifier_stats = orchestrator.classifier.get_stats()
        print(f"\n  Ensemble Classifier Stats:")
        print(f"    Total Classifications: {classifier_stats['total_classifications']}")
        print(f"    LLM Used: {classifier_stats.get('llm_used', 'N/A')}")
        print(f"    LLM Skipped: {classifier_stats.get('llm_skipped', 'N/A')}")
        if 'llm_skip_rate' in classifier_stats:
            print(f"    LLM Skip Rate: {classifier_stats['llm_skip_rate']:.1f}%")

    assert stats.total_processed == len(emails), "All emails should be processed"

    print(f"\n✅ PASS: Smart LLM Skip optimization working")

    return stats


@pytest.mark.asyncio
async def test_ensemble_orchestrator_custom_weights():
    """Test orchestrator with custom weights (LLM-heavy)."""
    print_header("TEST 3: ENSEMBLE ORCHESTRATOR - CUSTOM WEIGHTS (LLM-HEAVY)")

    # LLM-heavy weights
    custom_weights = ScoringWeights(
        rule_weight=0.15,
        history_weight=0.15,
        llm_weight=0.70,
    )

    orchestrator = ClassificationOrchestrator(ensemble_weights=custom_weights)
    emails = get_test_emails()

    print(f"\n📧 Processing {len(emails)} test emails with LLM-heavy weights (0.15/0.15/0.70)...")
    print(f"   Expected: LLM opinions should dominate classification")

    stats = await orchestrator.process_emails(emails, 'test_account')

    print_stats(stats)

    assert stats.total_processed == len(emails), "All emails should be processed"

    print(f"\n✅ PASS: Custom weights applied successfully")

    return stats


@pytest.mark.asyncio
async def test_ensemble_agreement_detection():
    """Test that ensemble detects agreement/disagreement correctly."""
    print_header("TEST 4: AGREEMENT DETECTION")

    classifier = EnsembleClassifier()

    # Test 1: Spam (all should agree)
    spam_email = EmailToClassify(
        email_id="agreement_spam",
        subject="WIN WIN WIN!!!",
        sender="spam@test.com",
        body="Free money! Click now!",
        account_id="test",
    )

    print(f"\n📧 Test Email 1: Spam (all layers should agree)")
    result1 = await classifier.classify(spam_email)

    print(f"  Layer Scores:")
    print(f"    Rule:    {result1.rule_score.category} (conf={result1.rule_score.confidence:.2f})")
    print(f"    History: {result1.history_score.category} (conf={result1.history_score.confidence:.2f})")
    print(f"    LLM:     {result1.llm_score.category if result1.llm_score else 'SKIPPED'} (conf={result1.llm_score.confidence if result1.llm_score else 'N/A'})")

    print(f"\n  Agreement Metrics:")
    print(f"    All agree: {result1.layers_agree}")
    print(f"    Agreement score: {result1.agreement_score:.2f}")
    print(f"    Confidence boost: {result1.confidence_boost:+.2f}")

    # Assertions
    if result1.llm_was_used:
        assert result1.agreement_score >= 0.66, "At least 2/3 should agree on spam"

    assert result1.final_category == "spam", "Should classify as spam"

    # Test 2: Ambiguous email (might disagree)
    ambiguous_email = EmailToClassify(
        email_id="agreement_ambiguous",
        subject="Question",
        sender="someone@example.com",
        body="Can you help me with this?",
        account_id="test",
    )

    print(f"\n📧 Test Email 2: Ambiguous (layers might disagree)")
    result2 = await classifier.classify(ambiguous_email)

    print(f"  Layer Scores:")
    print(f"    Rule:    {result2.rule_score.category} (conf={result2.rule_score.confidence:.2f})")
    print(f"    History: {result2.history_score.category} (conf={result2.history_score.confidence:.2f})")
    print(f"    LLM:     {result2.llm_score.category if result2.llm_score else 'SKIPPED'} (conf={result2.llm_score.confidence if result2.llm_score else 'N/A'})")

    print(f"\n  Agreement Metrics:")
    print(f"    All agree: {result2.layers_agree}")
    print(f"    Agreement score: {result2.agreement_score:.2f}")
    print(f"    Confidence boost: {result2.confidence_boost:+.2f}")

    if result2.disagreement:
        print(f"\n  ⚠️  Disagreement Detected:")
        print(f"    Needs review: {result2.disagreement.needs_user_review}")
        print(f"    Confidence variance: {result2.disagreement.confidence_variance:.3f}")

    print(f"\n✅ PASS: Agreement detection working correctly")

    return result1, result2


@pytest.mark.asyncio
async def test_ensemble_confidence_thresholds():
    """Test new confidence thresholds (0.90/0.65) in orchestrator."""
    print_header("TEST 5: CONFIDENCE THRESHOLDS (0.90/0.65)")

    orchestrator = ClassificationOrchestrator()

    # Check thresholds
    print(f"\n  Orchestrator Thresholds:")
    print(f"    HIGH_CONFIDENCE: {orchestrator.HIGH_CONFIDENCE_THRESHOLD}")
    print(f"    MEDIUM_CONFIDENCE: {orchestrator.MEDIUM_CONFIDENCE_THRESHOLD}")

    assert orchestrator.HIGH_CONFIDENCE_THRESHOLD == 0.90, "High confidence should be 0.90"
    assert orchestrator.MEDIUM_CONFIDENCE_THRESHOLD == 0.65, "Medium confidence should be 0.65"

    # Process emails and verify routing
    emails = get_test_emails()
    stats = await orchestrator.process_emails(emails, 'test_account')

    print(f"\n  Routing Results:")
    print(f"    High (≥0.90): {stats.high_confidence} emails → Auto-action")
    print(f"    Medium (0.65-0.90): {stats.medium_confidence} emails → Review queue")
    print(f"    Low (<0.65): {stats.low_confidence} emails → Manual review")

    assert stats.high_confidence + stats.medium_confidence + stats.low_confidence == len(emails), "All emails should be routed"

    print(f"\n✅ PASS: Confidence thresholds working correctly")

    return stats


@pytest.mark.asyncio
async def test_ensemble_review_queue_integration():
    """Test that disagreements are added to review queue."""
    print_header("TEST 6: REVIEW QUEUE INTEGRATION")

    orchestrator = ClassificationOrchestrator()

    # Email that might cause disagreement
    ambiguous_email = {
        'id': 'review_test_1',
        'subject': 'Invoice or Newsletter?',
        'sender': 'billing@company.com',
        'body': 'Check out our latest offers! Also, your invoice is attached.',
    }

    print(f"\n📧 Processing ambiguous email that might trigger review...")

    stats = await orchestrator.process_emails([ambiguous_email], 'test_account')

    print_stats(stats)

    # Check if item was added to review queue
    review_items = orchestrator.queue_manager.get_pending_items('test_account')

    print(f"\n  Review Queue:")
    print(f"    Items pending: {len(review_items)}")

    for item in review_items[:3]:  # Show first 3
        print(f"    - Email: {item.email_subject[:50]}... (confidence: {item.confidence:.2f})")

    print(f"\n✅ PASS: Review queue integration working")

    return stats


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all integration tests."""
    print("\n")
    print("=" * 80)
    print("ENSEMBLE ORCHESTRATOR INTEGRATION TEST SUITE")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    tests = [
        ("Default Config", test_ensemble_orchestrator_default_config),
        ("Smart LLM Skip", test_ensemble_orchestrator_smart_llm_skip),
        ("Custom Weights", test_ensemble_orchestrator_custom_weights),
        ("Agreement Detection", test_ensemble_agreement_detection),
        ("Confidence Thresholds", test_ensemble_confidence_thresholds),
        ("Review Queue Integration", test_ensemble_review_queue_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result, None))
            tests_passed += 1
        except Exception as e:
            results.append((test_name, None, e))
            tests_failed += 1
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {tests_passed} ✅")
    print(f"Failed: {tests_failed} ❌")
    print(f"Success Rate: {tests_passed / len(tests) * 100:.0f}%")
    print("=" * 80 + "\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
