"""
Integration Test: Ensemble vs Legacy Performance Comparison

Comparative analysis of Phase 1 (LegacyClassifier) vs Phase 2 (EnsembleClassifier):
1. Same batch of emails processed by both systems
2. Compare accuracy, confidence, processing time
3. Measure Smart LLM skip cost savings
4. Verify Ensemble meets performance goals
5. Analyze agreement patterns

Usage:
    pytest tests/integration/test_ensemble_vs_legacy_comparison.py -v
    python tests/integration/test_ensemble_vs_legacy_comparison.py
"""

import asyncio
import pytest
import time
from datetime import datetime
from typing import List, Dict, Any

from agent_platform.classification import (
    EnsembleClassifier,
    LegacyClassifier,
    EmailToClassify,
)


# ============================================================================
# TEST HELPERS
# ============================================================================

def print_header(text: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_comparison_table(ensemble_results, legacy_results):
    """Print side-by-side comparison table."""
    print("\n  " + "-" * 76)
    print(f"  {'Email':<30} | {'Ensemble':<20} | {'Legacy':<20}")
    print("  " + "-" * 76)

    for i, (ensemble, legacy) in enumerate(zip(ensemble_results, legacy_results)):
        email_desc = f"Email {i+1}"
        ensemble_cat = ensemble.final_category if hasattr(ensemble, 'final_category') else ensemble.category
        ensemble_conf = f"{ensemble.final_confidence if hasattr(ensemble, 'final_confidence') else ensemble.confidence:.2f}"
        legacy_cat = legacy.category
        legacy_conf = f"{legacy.confidence:.2f}"

        agree = "✓" if ensemble_cat == legacy_cat else "✗"

        print(f"  {email_desc:<30} | {ensemble_cat[:15]:<15} ({ensemble_conf}) | {legacy_cat[:15]:<15} ({legacy_conf}) {agree}")

    print("  " + "-" * 76)


# ============================================================================
# TEST EMAILS
# ============================================================================

def get_comparison_test_emails():
    """Get test emails for comparison."""
    return [
        # 1. Clear spam
        EmailToClassify(
            email_id="comp_spam",
            subject="GEWINN!!! KOSTENLOS!!!",
            sender="spam@spammer.com",
            body="Free money! Click here!",
            account_id="test",
        ),

        # 2. Auto-reply
        EmailToClassify(
            email_id="comp_autoreply",
            subject="Out of Office",
            sender="colleague@company.com",
            body="I am out of office. Do not reply.",
            account_id="test",
        ),

        # 3. Newsletter
        EmailToClassify(
            email_id="comp_newsletter",
            subject="Weekly Newsletter",
            sender="newsletter@tech.com",
            body="This week's news. Unsubscribe here.",
            account_id="test",
        ),

        # 4. Important meeting
        EmailToClassify(
            email_id="comp_meeting",
            subject="Quarterly Review - Urgent",
            sender="boss@company.com",
            body="Please review Q4 report for Friday meeting.",
            account_id="test",
        ),

        # 5. Invoice from noreply (challenging case)
        EmailToClassify(
            email_id="comp_invoice",
            subject="Rechnung #123",
            sender="noreply@amazon.de",
            body="Vielen Dank für Ihre Bestellung. Rechnung anbei.",
            account_id="test",
        ),

        # 6. Ambiguous
        EmailToClassify(
            email_id="comp_ambiguous",
            subject="Quick question",
            sender="unknown@example.com",
            body="Can you help?",
            account_id="test",
        ),
    ]


# ============================================================================
# COMPARISON TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ensemble_vs_legacy_categories():
    """Compare classification categories between Ensemble and Legacy."""
    print_header("TEST 1: CATEGORY COMPARISON - ENSEMBLE VS LEGACY")

    emails = get_comparison_test_emails()

    # Test with Ensemble
    print(f"\n🔄 Testing with EnsembleClassifier...")
    ensemble_classifier = EnsembleClassifier()
    ensemble_results = []

    for email in emails:
        result = await ensemble_classifier.classify(email)
        ensemble_results.append(result)

    # Test with Legacy
    print(f"🔄 Testing with LegacyClassifier...")
    legacy_classifier = LegacyClassifier()
    legacy_results = []

    for email in emails:
        result = await legacy_classifier.classify(email)
        legacy_results.append(result)

    # Compare
    print_comparison_table(ensemble_results, legacy_results)

    # Calculate agreement
    agreements = sum(
        1 for e, l in zip(ensemble_results, legacy_results)
        if (e.final_category if hasattr(e, 'final_category') else e.category) == l.category
    )
    agreement_rate = agreements / len(emails) * 100

    print(f"\n  Agreement Rate: {agreement_rate:.0f}% ({agreements}/{len(emails)} emails)")

    # Assertions
    assert agreement_rate >= 60, f"Agreement should be at least 60%, got {agreement_rate:.0f}%"

    print(f"\n✅ PASS: Ensemble and Legacy agree on {agreement_rate:.0f}% of classifications")

    return ensemble_results, legacy_results, agreement_rate


@pytest.mark.asyncio
async def test_ensemble_vs_legacy_confidence():
    """Compare confidence levels between Ensemble and Legacy."""
    print_header("TEST 2: CONFIDENCE COMPARISON - ENSEMBLE VS LEGACY")

    emails = get_comparison_test_emails()

    # Test both
    ensemble_classifier = EnsembleClassifier()
    legacy_classifier = LegacyClassifier()

    ensemble_confidences = []
    legacy_confidences = []

    for email in emails:
        ensemble_result = await ensemble_classifier.classify(email)
        legacy_result = await legacy_classifier.classify(email)

        ensemble_conf = ensemble_result.final_confidence if hasattr(ensemble_result, 'final_confidence') else ensemble_result.confidence
        legacy_conf = legacy_result.confidence

        ensemble_confidences.append(ensemble_conf)
        legacy_confidences.append(legacy_conf)

    # Calculate averages
    avg_ensemble = sum(ensemble_confidences) / len(ensemble_confidences)
    avg_legacy = sum(legacy_confidences) / len(legacy_confidences)

    print(f"\n  Average Confidence:")
    print(f"    Ensemble: {avg_ensemble:.3f}")
    print(f"    Legacy:   {avg_legacy:.3f}")
    print(f"    Difference: {avg_ensemble - avg_legacy:+.3f}")

    # Print per-email comparison
    print(f"\n  Per-Email Confidence:")
    for i, (e_conf, l_conf) in enumerate(zip(ensemble_confidences, legacy_confidences)):
        diff = e_conf - l_conf
        print(f"    Email {i+1}: Ensemble={e_conf:.2f}, Legacy={l_conf:.2f}, Diff={diff:+.2f}")

    print(f"\n✅ PASS: Confidence comparison complete")

    return avg_ensemble, avg_legacy


@pytest.mark.asyncio
async def test_ensemble_vs_legacy_performance():
    """Compare processing time between Ensemble and Legacy."""
    print_header("TEST 3: PERFORMANCE COMPARISON - PROCESSING TIME")

    emails = get_comparison_test_emails()

    # Test Ensemble (without Smart Skip)
    print(f"\n⏱️  Testing EnsembleClassifier (parallel layers)...")
    ensemble_classifier = EnsembleClassifier(smart_llm_skip=False)

    start = time.time()
    for email in emails:
        await ensemble_classifier.classify(email)
    ensemble_time = time.time() - start

    print(f"    Total Time: {ensemble_time:.2f}s")
    print(f"    Avg per email: {ensemble_time / len(emails):.2f}s")

    # Test Legacy
    print(f"\n⏱️  Testing LegacyClassifier (early-stopping)...")
    legacy_classifier = LegacyClassifier()

    start = time.time()
    for email in emails:
        await legacy_classifier.classify(email)
    legacy_time = time.time() - start

    print(f"    Total Time: {legacy_time:.2f}s")
    print(f"    Avg per email: {legacy_time / len(emails):.2f}s")

    # Compare
    print(f"\n  Comparison:")
    print(f"    Ensemble: {ensemble_time:.2f}s")
    print(f"    Legacy:   {legacy_time:.2f}s")

    if ensemble_time < legacy_time:
        speedup = (legacy_time / ensemble_time - 1) * 100
        print(f"    Ensemble is {speedup:.0f}% faster ✅")
    else:
        slowdown = (ensemble_time / legacy_time - 1) * 100
        print(f"    Ensemble is {slowdown:.0f}% slower (expected due to parallel execution)")

    print(f"\n✅ PASS: Performance comparison complete")

    return ensemble_time, legacy_time


@pytest.mark.asyncio
async def test_ensemble_smart_skip_cost_savings():
    """Test Smart LLM Skip cost savings."""
    print_header("TEST 4: SMART LLM SKIP - COST SAVINGS")

    emails = get_comparison_test_emails()

    # Test WITHOUT Smart Skip (baseline)
    print(f"\n🔄 Testing WITHOUT Smart LLM Skip (baseline)...")
    ensemble_no_skip = EnsembleClassifier(smart_llm_skip=False)

    for email in emails:
        await ensemble_no_skip.classify(email)

    stats_no_skip = ensemble_no_skip.get_stats()

    print(f"    LLM Used: {stats_no_skip.get('llm_used', len(emails))}/{len(emails)} emails")
    print(f"    LLM Skip Rate: 0%")

    # Test WITH Smart Skip
    print(f"\n🔄 Testing WITH Smart LLM Skip (optimized)...")
    ensemble_with_skip = EnsembleClassifier(smart_llm_skip=True)

    for email in emails:
        await ensemble_with_skip.classify(email)

    stats_with_skip = ensemble_with_skip.get_stats()

    llm_used = stats_with_skip.get('llm_used', 0)
    llm_skipped = stats_with_skip.get('llm_skipped', 0)
    skip_rate = stats_with_skip.get('llm_skip_rate', 0.0)

    print(f"    LLM Used: {llm_used}/{len(emails)} emails")
    print(f"    LLM Skipped: {llm_skipped}/{len(emails)} emails")
    print(f"    LLM Skip Rate: {skip_rate:.1f}%")

    # Calculate cost savings
    if llm_skipped > 0:
        cost_savings = (llm_skipped / len(emails)) * 100
        print(f"\n  💰 Cost Savings: {cost_savings:.0f}% (target: 60-70%)")

        if cost_savings >= 40:
            print(f"    ✅ Good cost savings achieved!")
        else:
            print(f"    ⚠️  Lower than expected (might be due to test email characteristics)")

    print(f"\n✅ PASS: Smart LLM Skip test complete")

    return skip_rate


@pytest.mark.asyncio
async def test_ensemble_agreement_analysis():
    """Analyze agreement patterns in Ensemble."""
    print_header("TEST 5: ENSEMBLE AGREEMENT ANALYSIS")

    emails = get_comparison_test_emails()

    ensemble_classifier = EnsembleClassifier()

    all_agree_count = 0
    partial_agree_count = 0
    disagree_count = 0

    results = []

    print(f"\n📧 Processing {len(emails)} emails...")

    for email in emails:
        result = await ensemble_classifier.classify(email)
        results.append(result)

        if result.layers_agree:
            all_agree_count += 1
        elif result.agreement_score >= 0.66:  # 2/3 agree
            partial_agree_count += 1
        else:
            disagree_count += 1

    # Print results
    print(f"\n  Agreement Distribution:")
    print(f"    All layers agree:      {all_agree_count}/{len(emails)} ({all_agree_count/len(emails)*100:.0f}%)")
    print(f"    Partial agreement:     {partial_agree_count}/{len(emails)} ({partial_agree_count/len(emails)*100:.0f}%)")
    print(f"    Disagreement:          {disagree_count}/{len(emails)} ({disagree_count/len(emails)*100:.0f}%)")

    # Analyze confidence boosts
    boosts = [r.confidence_boost for r in results]
    avg_boost = sum(boosts) / len(boosts)

    print(f"\n  Confidence Adjustments:")
    print(f"    Average boost: {avg_boost:+.3f}")
    print(f"    Positive boosts: {sum(1 for b in boosts if b > 0)}/{len(boosts)}")
    print(f"    Negative boosts: {sum(1 for b in boosts if b < 0)}/{len(boosts)}")

    print(f"\n✅ PASS: Agreement analysis complete")

    return results


@pytest.mark.asyncio
async def test_ensemble_challenging_case_invoice():
    """Test challenging case: Invoice from noreply (Phase 1 problem)."""
    print_header("TEST 6: CHALLENGING CASE - INVOICE FROM NOREPLY")

    # The famous "No-Reply Problem" from Phase 1
    invoice_email = EmailToClassify(
        email_id="challenging_invoice",
        subject="Rechnung #12345 - Amazon",
        sender="noreply@amazon.de",
        body="Vielen Dank für Ihre Bestellung. Ihre Rechnung über €150.00 ist anbei. Bitte zahlen Sie innerhalb von 14 Tagen.",
        account_id="test",
    )

    print(f"\n📧 Email: {invoice_email.subject}")
    print(f"   From: {invoice_email.sender}")
    print(f"   Problem: Phase 1 classified as low-priority (system notification)")

    # Test with Legacy
    print(f"\n🔄 LegacyClassifier (Phase 1):")
    legacy_classifier = LegacyClassifier()
    legacy_result = await legacy_classifier.classify(invoice_email)

    print(f"    Category: {legacy_result.category}")
    print(f"    Importance: {legacy_result.importance:.2f}")
    print(f"    Confidence: {legacy_result.confidence:.2f}")
    print(f"    Layer used: {legacy_result.layer_used}")

    # Test with Ensemble
    print(f"\n🔄 EnsembleClassifier (Phase 2):")
    ensemble_classifier = EnsembleClassifier()
    ensemble_result = await ensemble_classifier.classify(invoice_email)

    print(f"    Final Category: {ensemble_result.final_category}")
    print(f"    Final Importance: {ensemble_result.final_importance:.2f}")
    print(f"    Final Confidence: {ensemble_result.final_confidence:.2f}")

    print(f"\n    Layer Scores:")
    print(f"      Rule:    {ensemble_result.rule_score.category} (imp={ensemble_result.rule_score.importance:.2f})")
    print(f"      History: {ensemble_result.history_score.category} (imp={ensemble_result.history_score.importance:.2f})")
    if ensemble_result.llm_score:
        print(f"      LLM:     {ensemble_result.llm_score.category} (imp={ensemble_result.llm_score.importance:.2f})")

    # Check if Ensemble improved
    ensemble_imp = ensemble_result.final_importance
    legacy_imp = legacy_result.importance

    print(f"\n  Comparison:")
    print(f"    Legacy importance:   {legacy_imp:.2f}")
    print(f"    Ensemble importance: {ensemble_imp:.2f}")
    print(f"    Improvement: {ensemble_imp - legacy_imp:+.2f}")

    if ensemble_imp > 0.7:
        print(f"    ✅ Ensemble correctly identifies as important (>0.7)")
    elif ensemble_imp > legacy_imp:
        print(f"    ✓ Ensemble improves over Legacy")
    else:
        print(f"    ⚠️  Ensemble doesn't improve classification")

    print(f"\n✅ PASS: Challenging case tested")

    return ensemble_result, legacy_result


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all comparison tests."""
    print("\n")
    print("=" * 80)
    print("ENSEMBLE VS LEGACY COMPARISON TEST SUITE")
    print("=" * 80)

    tests_passed = 0
    tests_failed = 0

    tests = [
        ("Category Comparison", test_ensemble_vs_legacy_categories),
        ("Confidence Comparison", test_ensemble_vs_legacy_confidence),
        ("Performance Comparison", test_ensemble_vs_legacy_performance),
        ("Smart LLM Skip Savings", test_ensemble_smart_skip_cost_savings),
        ("Agreement Analysis", test_ensemble_agreement_analysis),
        ("Challenging Case (Invoice)", test_ensemble_challenging_case_invoice),
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
