"""
Quick Test for Individual Classification Agents

This script tests each agent individually to verify they work correctly
before running the full comparison test.

Tests:
1. Rule Agent - Pattern matching
2. History Agent - Database lookups
3. LLM Agent - Semantic analysis
4. Orchestrator Agent - Early stopping
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_platform.classification.agents import (
    create_rule_agent,
    create_history_agent,
    create_llm_agent,
    create_orchestrator_agent,
)
from agent_platform.classification.agents.rule_agent import classify_email_with_rules
from agent_platform.classification.agents.history_agent import classify_email_with_history
from agent_platform.classification.agents.llm_agent import classify_email_with_llm
from agent_platform.db.database import init_db


# ============================================================================
# TEST 1: RULE AGENT
# ============================================================================

def test_rule_agent():
    """Test Rule Agent with clear spam email."""
    print("\n" + "=" * 80)
    print("TEST 1: Rule Agent (Pattern Matching)")
    print("=" * 80)

    # Create spam email (should be caught with high confidence)
    email_id = "test_spam_001"
    subject = "CONGRATULATIONS!!! YOU WON $$$"
    body = "Click here now to claim your free money! Limited time offer! Act now! Get rich quick!"
    sender = "noreply@spam-lottery.com"

    print(f"\nTesting spam detection...")
    print(f"Subject: {subject}")
    print(f"Sender: {sender}\n")

    # Call rule classification function directly
    result = classify_email_with_rules(email_id, subject, body, sender)

    print(f"Results:")
    print(f"  Category:   {result['category']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Importance: {result['importance']:.2f}")
    print(f"  Reasoning:  {result['reasoning']}")
    print(f"  Matched Rules: {', '.join(result['matched_rules'])}")

    # Verify expectations
    if result['category'] == 'spam' and result['confidence'] >= 0.9:
        print("\n✅ PASS: Rule Agent correctly detected spam with high confidence")
        return True
    else:
        print(f"\n❌ FAIL: Expected spam with confidence >= 0.9, got {result['category']} with {result['confidence']:.2f}")
        return False


# ============================================================================
# TEST 2: HISTORY AGENT
# ============================================================================

def test_history_agent():
    """Test History Agent with database lookup."""
    print("\n" + "=" * 80)
    print("TEST 2: History Agent (Database Lookup)")
    print("=" * 80)

    # Initialize database
    init_db()

    # Test with unknown sender (should have no history)
    email_id = "test_history_001"
    sender = "unknown-sender-12345@example.com"
    account_id = "gmail_1"

    print(f"\nTesting history lookup for unknown sender...")
    print(f"Sender: {sender}\n")

    # Call history classification function directly
    result = classify_email_with_history(email_id, sender, account_id)

    print(f"Results:")
    print(f"  Category:   {result['category']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Importance: {result['importance']:.2f}")
    print(f"  Reasoning:  {result['reasoning']}")
    print(f"  Data Source: {result['data_source']}")
    print(f"  Historical Emails: {result['total_historical_emails']}")

    # Verify expectations (unknown sender should have low confidence)
    if result['confidence'] <= 0.3 and result['total_historical_emails'] == 0:
        print("\n✅ PASS: History Agent correctly handles unknown sender with low confidence")
        return True
    else:
        print(f"\n❌ FAIL: Expected low confidence for unknown sender, got {result['confidence']:.2f}")
        return False


# ============================================================================
# TEST 3: LLM AGENT
# ============================================================================

async def test_llm_agent():
    """Test LLM Agent with semantic analysis."""
    print("\n" + "=" * 80)
    print("TEST 3: LLM Agent (Semantic Analysis)")
    print("=" * 80)

    # Create ambiguous email that needs LLM
    email_id = "test_llm_001"
    subject = "Quick question about the project"
    body = "Hey, do you have time for a quick call this week? I want to discuss the project timeline and next steps."
    sender = "colleague@company.com"

    print(f"\nTesting semantic analysis...")
    print(f"Subject: {subject}")
    print(f"Body: {body[:50]}...\n")

    try:
        # Call LLM classification function directly
        result = await classify_email_with_llm(
            email_id=email_id,
            subject=subject,
            body=body,
            sender=sender,
        )

        print(f"Results:")
        print(f"  Category:   {result['category']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Importance: {result['importance']:.2f}")
        print(f"  Reasoning:  {result['reasoning']}")
        print(f"  LLM Provider: {result['llm_provider_used']}")
        print(f"  LLM Model: {result['llm_model_used']}")
        print(f"  Response Time: {result['llm_response_time_ms']:.0f}ms")

        # Verify LLM was actually used
        if result['llm_provider_used'] in ['ollama', 'openai_fallback']:
            print("\n✅ PASS: LLM Agent successfully classified email")
            return True
        else:
            print(f"\n❌ FAIL: Expected LLM provider, got {result['llm_provider_used']}")
            return False

    except Exception as e:
        print(f"\n❌ FAIL: LLM Agent raised exception: {e}")
        return False


# ============================================================================
# TEST 4: ORCHESTRATOR AGENT
# ============================================================================

async def test_orchestrator_agent():
    """Test Orchestrator Agent with early stopping."""
    print("\n" + "=" * 80)
    print("TEST 4: Orchestrator Agent (Early Stopping)")
    print("=" * 80)

    from agent_platform.classification.agents.orchestrator_agent import orchestrate_classification

    # Test 1: Clear spam (should stop at Rule Layer)
    print("\n[Test 4.1] Testing early stopping with clear spam...")

    email_id = "test_orch_spam"
    subject = "FREE MONEY!!! WIN WIN WIN"
    body = "Click here to get rich quick! Free money guaranteed! Act now!"
    sender = "spam@scam.com"
    account_id = "gmail_1"

    result = await orchestrate_classification(
        email_id=email_id,
        subject=subject,
        body=body,
        sender=sender,
        account_id=account_id,
    )

    print(f"\nResults:")
    print(f"  Layer Used: {result['layer_used']}")
    print(f"  Category:   {result['category']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Processing Time: {result['processing_time_ms']:.0f}ms")

    if result['layer_used'] == 'rules' and result['category'] == 'spam':
        print("  ✅ Correctly stopped at Rule Layer for spam")
        test1_pass = True
    else:
        print(f"  ❌ Expected to stop at Rule Layer for spam, got {result['layer_used']}")
        test1_pass = False

    # Test 2: Ambiguous email (should proceed to LLM Layer)
    print("\n[Test 4.2] Testing LLM fallback for ambiguous email...")

    email_id = "test_orch_ambiguous"
    subject = "Project update"
    body = "I wanted to give you a quick update on the project status and discuss next steps."
    sender = "colleague@company.com"
    account_id = "gmail_1"

    result = await orchestrate_classification(
        email_id=email_id,
        subject=subject,
        body=body,
        sender=sender,
        account_id=account_id,
    )

    print(f"\nResults:")
    print(f"  Layer Used: {result['layer_used']}")
    print(f"  Category:   {result['category']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Processing Time: {result['processing_time_ms']:.0f}ms")

    if result['layer_used'] == 'llm':
        print("  ✅ Correctly proceeded to LLM Layer for ambiguous email")
        test2_pass = True
    else:
        print(f"  ❌ Expected to use LLM Layer, got {result['layer_used']}")
        test2_pass = False

    if test1_pass and test2_pass:
        print("\n✅ PASS: Orchestrator Agent early stopping works correctly")
        return True
    else:
        print("\n❌ FAIL: Orchestrator Agent early stopping has issues")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all quick tests."""
    print("=" * 80)
    print("QUICK AGENT TESTS")
    print("=" * 80)
    print("\nTesting individual agents before running full comparison...\n")

    results = []

    # Run synchronous tests
    results.append(("Rule Agent", test_rule_agent()))
    results.append(("History Agent", test_history_agent()))

    # Run async tests
    results.append(("LLM Agent", await test_llm_agent()))
    results.append(("Orchestrator Agent", await test_orchestrator_agent()))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    failed_tests = total_tests - passed_tests

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed:      {passed_tests}")
    print(f"Failed:      {failed_tests}\n")

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Ready for full comparison test.\n")
        return 0
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Fix issues before running full comparison.\n")
        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
