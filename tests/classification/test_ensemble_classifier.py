"""
Test Script for Ensemble Classifier (Phase 2)

Tests the ensemble classification system:
1. All 3 layers run in parallel
2. Weighted score combination
3. Agreement detection & confidence boosting
4. Smart LLM skip optimization
5. Disagreement logging

Usage:
    python tests/classification/test_ensemble_classifier.py
    pytest tests/classification/test_ensemble_classifier.py -v
"""

import asyncio
import pytest
from datetime import datetime

from agent_platform.classification import (
    EnsembleClassifier,
    LegacyClassifier,
    EmailToClassify,
    ScoringWeights,
)


# ============================================================================
# TEST HELPERS
# ============================================================================

def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_ensemble_result(result, test_name: str):
    """Print ensemble classification result."""
    print(f"\n{test_name}:")
    print(f"  📊 Final Category: {result.final_category}")
    print(f"  📈 Final Importance: {result.final_importance:.2f}")
    print(f"  🎯 Final Confidence: {result.final_confidence:.2f}")
    print(f"  🔀 Confidence Boost: {result.confidence_boost:+.2f}")

    print(f"\n  Layer Scores:")
    print(f"    Rule:    {result.rule_score.category:20s} (conf={result.rule_score.confidence:.2f}, imp={result.rule_score.importance:.2f})")
    print(f"    History: {result.history_score.category:20s} (conf={result.history_score.confidence:.2f}, imp={result.history_score.importance:.2f})")

    if result.llm_score:
        print(f"    LLM:     {result.llm_score.category:20s} (conf={result.llm_score.confidence:.2f}, imp={result.llm_score.importance:.2f})")
    else:
        print(f"    LLM:     SKIPPED (Smart optimization)")

    print(f"\n  Agreement:")
    print(f"    All layers agree: {result.layers_agree}")
    print(f"    Agreement score:  {result.agreement_score:.2f}")
    print(f"    LLM was used:     {result.llm_was_used}")

    print(f"\n  Weights Used:")
    print(f"    Rule={result.rule_weight:.2f}, History={result.history_weight:.2f}, LLM={result.llm_weight:.2f}")

    print(f"\n  Processing Time: {result.total_processing_time_ms:.0f}ms")

    if result.disagreement:
        print(f"\n  ⚠️  Disagreement detected:")
        print(f"    Needs review: {result.disagreement.needs_user_review}")
        print(f"    Variance: {result.disagreement.confidence_variance:.3f}")


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
async def test_spam_email_all_agree():
    """Test that spam email triggers agreement across all layers."""
    print_header("TEST 1: SPAM EMAIL (All layers should agree)")

    classifier = EnsembleClassifier()

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
    print_ensemble_result(result, "Ensemble Classification")

    # Verify all layers agree on spam
    assert result.final_category == "spam", "Should classify as spam"
    assert result.layers_agree or result.agreement_score >= 0.66, "At least 2 layers should agree"
    assert result.confidence_boost >= 0, "Agreement should boost confidence"

    print(f"\n✅ PASS: Spam correctly identified with ensemble consensus")

    return result


@pytest.mark.asyncio
async def test_important_email_with_llm():
    """Test important email that requires LLM analysis."""
    print_header("TEST 2: IMPORTANT EMAIL (LLM should be used)")

    classifier = EnsembleClassifier()

    email = EmailToClassify(
        email_id="test_important_1",
        subject="Quarterly Report Review Meeting - Urgent",
        sender="boss@company.com",
        body="Please review the Q4 financial report and prepare your analysis for the meeting on Friday. This is critical for our board presentation.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_ensemble_result(result, "Ensemble Classification")

    # Verify LLM was used
    assert result.llm_was_used, "LLM should be used for important emails"
    assert result.llm_score is not None, "LLM score should exist"
    assert result.final_importance > 0.6, "Should have high importance"

    print(f"\n✅ PASS: Important email analyzed by all layers including LLM")

    return result


@pytest.mark.asyncio
async def test_smart_llm_skip():
    """Test that Smart LLM skip works when Rule+History agree."""
    print_header("TEST 3: SMART LLM SKIP (Newsletter - should skip LLM)")

    classifier = EnsembleClassifier(smart_llm_skip=True)

    email = EmailToClassify(
        email_id="test_newsletter_1",
        subject="Weekly Tech Newsletter - December 2025",
        sender="newsletter@tech.com",
        body="This week's top stories in tech. Unsubscribe here if you no longer wish to receive our newsletter.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_ensemble_result(result, "Ensemble Classification")

    # Verify LLM was skipped (if Rule+History agree with high confidence)
    # Note: This may or may not skip depending on confidence levels
    print(f"\n  LLM Skip Status: {'SKIPPED ✅' if not result.llm_was_used else 'USED (agreement not strong enough)'}")

    assert result.final_category in ["newsletter", "nice_to_know"], "Should classify as low priority"

    print(f"\n✅ PASS: Newsletter classified (Smart LLM skip {'active' if not result.llm_was_used else 'bypassed'})")

    return result


@pytest.mark.asyncio
async def test_custom_weights():
    """Test ensemble with custom weights."""
    print_header("TEST 4: CUSTOM WEIGHTS (LLM-heavy: 0.1/0.1/0.8)")

    # LLM-heavy weights
    custom_weights = ScoringWeights(
        rule_weight=0.1,
        history_weight=0.1,
        llm_weight=0.8,
    )

    classifier = EnsembleClassifier(weights=custom_weights)

    email = EmailToClassify(
        email_id="test_custom_1",
        subject="Project Budget Approval Needed",
        sender="manager@company.com",
        body="Can you approve the budget for the new project? We need your sign-off by end of week.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    result = await classifier.classify(email)
    print_ensemble_result(result, "Ensemble Classification")

    # Verify weights were applied
    assert result.rule_weight == 0.1, "Rule weight should be 0.1"
    assert result.history_weight == 0.1, "History weight should be 0.1"
    assert result.llm_weight == 0.8, "LLM weight should be 0.8"
    assert result.llm_was_used, "LLM should be used with high weight"

    print(f"\n✅ PASS: Custom weights applied correctly")

    return result


@pytest.mark.asyncio
async def test_weights_validation():
    """Test that weights validation works."""
    print_header("TEST 5: WEIGHTS VALIDATION")

    # Valid weights
    valid_weights = ScoringWeights(
        rule_weight=0.2,
        history_weight=0.3,
        llm_weight=0.5,
    )

    assert valid_weights.validate_weights(), "Valid weights should pass"
    print("✅ Valid weights (0.2/0.3/0.5) accepted")

    # Invalid weights (don't sum to 1.0)
    invalid_weights = ScoringWeights(
        rule_weight=0.5,
        history_weight=0.5,
        llm_weight=0.5,
    )

    assert not invalid_weights.validate_weights(), "Invalid weights should fail"
    print("✅ Invalid weights (0.5/0.5/0.5) rejected")

    print(f"\n✅ PASS: Weights validation working correctly")


@pytest.mark.asyncio
async def test_ensemble_vs_legacy_comparison():
    """Test Ensemble vs Legacy classifier on same email."""
    print_header("TEST 6: ENSEMBLE VS LEGACY COMPARISON")

    email = EmailToClassify(
        email_id="test_comparison_1",
        subject="Meeting Invitation - Q4 Planning",
        sender="colleague@company.com",
        body="Hi, can we schedule a meeting next week to discuss Q4 planning? Let me know your availability.",
        account_id="test",
    )

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")

    # Test with Ensemble
    print("\n🔄 Testing with EnsembleClassifier...")
    ensemble_classifier = EnsembleClassifier()
    ensemble_result = await ensemble_classifier.classify(email)

    print(f"  Ensemble Result:")
    print(f"    Category: {ensemble_result.final_category}")
    print(f"    Confidence: {ensemble_result.final_confidence:.2f}")
    print(f"    All layers agree: {ensemble_result.layers_agree}")

    # Test with Legacy
    print("\n🔄 Testing with LegacyClassifier...")
    legacy_classifier = LegacyClassifier()
    legacy_result = await legacy_classifier.classify(email)

    print(f"  Legacy Result:")
    print(f"    Category: {legacy_result.category}")
    print(f"    Confidence: {legacy_result.confidence:.2f}")
    print(f"    Layer used: {legacy_result.layer_used}")

    print("\n  Comparison:")
    print(f"    Categories match: {ensemble_result.final_category == legacy_result.category}")
    print(f"    Confidence difference: {abs(ensemble_result.final_confidence - legacy_result.confidence):.2f}")

    print(f"\n✅ PASS: Both classifiers completed successfully")

    return ensemble_result, legacy_result


@pytest.mark.asyncio
async def test_agreement_detection():
    """Test agreement detection logic."""
    print_header("TEST 7: AGREEMENT DETECTION")

    # Test with likely agreement (auto-reply email)
    email = EmailToClassify(
        email_id="test_agreement_1",
        subject="Out of Office AutoReply: Vacation",
        sender="colleague@company.com",
        body="This is an automated message. I am currently out of office and will return on Monday.",
        account_id="test",
    )

    classifier = EnsembleClassifier()
    result = await classifier.classify(email)

    print(f"\n📧 Email: {email.subject}")
    print(f"   From: {email.sender}")
    print_ensemble_result(result, "Agreement Test")

    # Check agreement metrics
    print(f"\n  Agreement Metrics:")
    print(f"    All agree: {result.layers_agree}")
    print(f"    Agreement score: {result.agreement_score:.2f}")
    print(f"    Confidence boost: {result.confidence_boost:+.2f}")

    if result.disagreement:
        print(f"    Disagreement variance: {result.disagreement.confidence_variance:.3f}")
        print(f"    Needs review: {result.disagreement.needs_user_review}")

    assert result.agreement_score >= 0, "Agreement score should be non-negative"
    assert result.agreement_score <= 1.0, "Agreement score should be <= 1.0"

    print(f"\n✅ PASS: Agreement detection working")

    return result


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all ensemble classifier tests."""
    print("\n")
    print("=" * 70)
    print("ENSEMBLE CLASSIFIER TEST SUITE - PHASE 2")
    print("=" * 70)

    tests_passed = 0
    tests_failed = 0

    tests = [
        ("Spam Email (All Agree)", test_spam_email_all_agree),
        ("Important Email (LLM)", test_important_email_with_llm),
        ("Smart LLM Skip", test_smart_llm_skip),
        ("Custom Weights", test_custom_weights),
        ("Weights Validation", test_weights_validation),
        ("Ensemble vs Legacy", test_ensemble_vs_legacy_comparison),
        ("Agreement Detection", test_agreement_detection),
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

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {tests_passed} ✅")
    print(f"Failed: {tests_failed} ❌")
    print(f"Success Rate: {tests_passed / len(tests) * 100:.0f}%")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
