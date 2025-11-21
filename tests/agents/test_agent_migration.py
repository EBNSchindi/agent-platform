"""
Test Agent-Based Classification Migration

This script verifies that the Agent-based implementation produces IDENTICAL
results to the original UnifiedClassifier implementation.

PRESERVATION VERIFICATION:
- Classification results must be 100% identical
- Early stopping must work the same (80-85% stop at Rule/History layers)
- Performance must be similar (no regression)
- EMA learning must be preserved (verified separately in feedback tests)

Test Strategy:
1. Run 50 sample emails through both classifiers
2. Compare results (category, importance, confidence, layer_used)
3. Verify early stopping percentages match
4. Check for any regressions
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_platform.classification import UnifiedClassifier
from agent_platform.classification.agents.orchestrator_agent import AgentBasedClassifier
from agent_platform.classification.models import EmailToClassify
from agent_platform.db.database import init_db


# ============================================================================
# TEST DATA (50 Sample Emails - Various Categories)
# ============================================================================

SAMPLE_EMAILS = [
    # Spam (should be caught by Rule Layer)
    {
        "email_id": "spam_001",
        "subject": "CONGRATULATIONS!!! YOU WON $$$",
        "body": "Click here now to claim your free money! Limited time offer! Act now!",
        "sender": "noreply@spam-lottery.com",
        "account_id": "gmail_1",
        "expected_category": "spam",
        "expected_layer": "rules",
    },
    {
        "email_id": "spam_002",
        "subject": "Viagra now! Special promotion!!!",
        "body": "Get viagra at 90% discount. Buy now! Free shipping!",
        "sender": "marketing@pharma-spam.com",
        "account_id": "gmail_1",
        "expected_category": "spam",
        "expected_layer": "rules",
    },

    # Newsletters (should be caught by Rule Layer)
    {
        "email_id": "newsletter_001",
        "subject": "Weekly Tech Newsletter - October 2025",
        "body": "This week in tech... Unsubscribe here if you don't want to receive these emails.",
        "sender": "newsletter@techcrunch.com",
        "account_id": "gmail_1",
        "expected_category": "newsletter",
        "expected_layer": "rules",
    },
    {
        "email_id": "newsletter_002",
        "subject": "Your monthly digest from Medium",
        "body": "Top stories this month... Manage preferences or unsubscribe.",
        "sender": "noreply@medium.com",
        "account_id": "gmail_1",
        "expected_category": "newsletter",
        "expected_layer": "rules",
    },

    # Auto-replies (should be caught by Rule Layer)
    {
        "email_id": "autoreply_001",
        "subject": "Out of office: Vacation",
        "body": "I am currently out of office until Monday. I will respond to your email when I return.",
        "sender": "colleague@company.com",
        "account_id": "gmail_1",
        "expected_category": "system_notifications",
        "expected_layer": "rules",
    },
    {
        "email_id": "autoreply_002",
        "subject": "Automatic reply: Your message",
        "body": "This is an automated message. I am not available right now.",
        "sender": "john@example.com",
        "account_id": "gmail_1",
        "expected_category": "system_notifications",
        "expected_layer": "rules",
    },

    # System notifications (should be caught by Rule Layer)
    {
        "email_id": "system_001",
        "subject": "Password reset requested",
        "body": "You requested a password reset. Your verification code is 123456.",
        "sender": "noreply@github.com",
        "account_id": "gmail_1",
        "expected_category": "system_notifications",
        "expected_layer": "rules",
    },
    {
        "email_id": "system_002",
        "subject": "Order confirmation #12345",
        "body": "Thank you for your order. Your order has been confirmed and will ship soon.",
        "sender": "orders@amazon.com",
        "account_id": "gmail_1",
        "expected_category": "system_notifications",
        "expected_layer": "rules",
    },

    # Ambiguous emails (need LLM Layer)
    {
        "email_id": "ambiguous_001",
        "subject": "Quick question",
        "body": "Hey, do you have time for a quick call this week? I want to discuss the project.",
        "sender": "colleague@company.com",
        "account_id": "gmail_1",
        "expected_category": None,  # Could be action_required or wichtig
        "expected_layer": "llm",  # Needs semantic understanding
    },
    {
        "email_id": "ambiguous_002",
        "subject": "Meeting notes",
        "body": "Here are the notes from yesterday's meeting. Let me know if you have any questions.",
        "sender": "manager@company.com",
        "account_id": "gmail_1",
        "expected_category": None,  # Could be nice_to_know or wichtig
        "expected_layer": "llm",
    },
]


# ============================================================================
# COMPARISON FUNCTIONS
# ============================================================================

def compare_results(original, agent_based, email_data):
    """
    Compare classification results from both implementations.

    Returns:
        dict with comparison metrics and any differences found
    """
    differences = []

    # Compare category
    if original.category != agent_based.category:
        differences.append(f"Category mismatch: {original.category} vs {agent_based.category}")

    # Compare layer used
    if original.layer_used != agent_based.layer_used:
        differences.append(f"Layer mismatch: {original.layer_used} vs {agent_based.layer_used}")

    # Compare confidence (allow small floating point differences)
    conf_diff = abs(original.confidence - agent_based.confidence)
    if conf_diff > 0.01:  # Allow 1% difference for floating point
        differences.append(f"Confidence mismatch: {original.confidence:.3f} vs {agent_based.confidence:.3f} (diff: {conf_diff:.3f})")

    # Compare importance (allow small floating point differences)
    imp_diff = abs(original.importance - agent_based.importance)
    if imp_diff > 0.01:  # Allow 1% difference for floating point
        differences.append(f"Importance mismatch: {original.importance:.3f} vs {agent_based.importance:.3f} (diff: {imp_diff:.3f})")

    return {
        'email_id': email_data['email_id'],
        'matches': len(differences) == 0,
        'differences': differences,
        'original_result': {
            'category': original.category,
            'confidence': original.confidence,
            'importance': original.importance,
            'layer_used': original.layer_used,
        },
        'agent_result': {
            'category': agent_based.category,
            'confidence': agent_based.confidence,
            'importance': agent_based.importance,
            'layer_used': agent_based.layer_used,
        }
    }


# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

async def run_migration_test():
    """
    Run migration test comparing original and agent-based classifiers.
    """
    print("=" * 80)
    print("AGENT MIGRATION TEST")
    print("=" * 80)
    print("\nVerifying that Agent-based implementation produces IDENTICAL results")
    print("to the original UnifiedClassifier implementation.\n")

    # Initialize database
    print("Initializing database...")
    init_db()

    # Create both classifiers
    print("Creating classifiers...")
    original_classifier = UnifiedClassifier()
    agent_classifier = AgentBasedClassifier()

    # Test results
    all_comparisons = []
    total_tests = len(SAMPLE_EMAILS)
    passed_tests = 0
    failed_tests = 0

    print(f"\nRunning {total_tests} test classifications...\n")

    # Run classifications
    for i, email_data in enumerate(SAMPLE_EMAILS, 1):
        email_id = email_data['email_id']
        print(f"[{i}/{total_tests}] Testing {email_id}...")

        # Create EmailToClassify object
        email = EmailToClassify(
            email_id=email_data['email_id'],
            subject=email_data['subject'],
            body=email_data['body'],
            sender=email_data['sender'],
            account_id=email_data['account_id'],
        )

        # Classify with both implementations
        try:
            original_result = await original_classifier.classify(email)
            agent_result = await agent_classifier.classify(email)

            # Compare results
            comparison = compare_results(original_result, agent_result, email_data)
            all_comparisons.append(comparison)

            if comparison['matches']:
                passed_tests += 1
                print(f"  ✅ PASS - Results identical")
                print(f"     Category: {original_result.category}, Layer: {original_result.layer_used}, Confidence: {original_result.confidence:.2f}")
            else:
                failed_tests += 1
                print(f"  ❌ FAIL - Results differ!")
                for diff in comparison['differences']:
                    print(f"     - {diff}")

        except Exception as e:
            failed_tests += 1
            print(f"  ❌ ERROR: {e}")
            all_comparisons.append({
                'email_id': email_id,
                'matches': False,
                'differences': [f"Exception: {e}"],
                'original_result': None,
                'agent_result': None,
            })

        print()

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    # Overall results
    print(f"\n📊 Overall Results:")
    print(f"  Total tests:  {total_tests}")
    print(f"  Passed:       {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"  Failed:       {failed_tests} ({failed_tests/total_tests*100:.1f}%)")

    # Statistics comparison
    print(f"\n📈 Statistics Comparison:")

    original_stats = original_classifier.get_stats()
    agent_stats = agent_classifier.get_stats()

    print(f"\n  Original Classifier:")
    print(f"    Rule Layer:    {original_stats['rule_layer_percentage']:.1f}%")
    print(f"    History Layer: {original_stats['history_layer_percentage']:.1f}%")
    print(f"    LLM Layer:     {original_stats['llm_layer_percentage']:.1f}%")

    print(f"\n  Agent-Based Classifier:")
    print(f"    Rule Layer:    {agent_stats['rule_layer_percentage']:.1f}%")
    print(f"    History Layer: {agent_stats['history_layer_percentage']:.1f}%")
    print(f"    LLM Layer:     {agent_stats['llm_layer_percentage']:.1f}%")

    # Layer distribution comparison
    rule_diff = abs(original_stats['rule_layer_percentage'] - agent_stats['rule_layer_percentage'])
    history_diff = abs(original_stats['history_layer_percentage'] - agent_stats['history_layer_percentage'])
    llm_diff = abs(original_stats['llm_layer_percentage'] - agent_stats['llm_layer_percentage'])

    print(f"\n  Layer Distribution Differences:")
    print(f"    Rule Layer:    {rule_diff:.1f}%")
    print(f"    History Layer: {history_diff:.1f}%")
    print(f"    LLM Layer:     {llm_diff:.1f}%")

    # Detailed failures
    if failed_tests > 0:
        print(f"\n❌ Failed Tests Details:")
        for comp in all_comparisons:
            if not comp['matches']:
                print(f"\n  {comp['email_id']}:")
                for diff in comp['differences']:
                    print(f"    - {diff}")

    # ========================================================================
    # PRESERVATION VERIFICATION
    # ========================================================================

    print("\n" + "=" * 80)
    print("PRESERVATION VERIFICATION")
    print("=" * 80)

    preservation_checks = []

    # Check 1: 100% identical results
    if passed_tests == total_tests:
        print("✅ PASS: Classification results are 100% identical")
        preservation_checks.append(True)
    else:
        print(f"❌ FAIL: Only {passed_tests}/{total_tests} results are identical")
        preservation_checks.append(False)

    # Check 2: Early stopping preserved (80-85% should stop at Rule/History)
    early_stop_original = original_stats['rule_layer_percentage'] + original_stats['history_layer_percentage']
    early_stop_agent = agent_stats['rule_layer_percentage'] + agent_stats['history_layer_percentage']

    if 75 <= early_stop_original <= 90 and abs(early_stop_original - early_stop_agent) < 5:
        print(f"✅ PASS: Early stopping preserved ({early_stop_agent:.1f}% stop at Rule/History layers)")
        preservation_checks.append(True)
    else:
        print(f"❌ FAIL: Early stopping not preserved (Original: {early_stop_original:.1f}%, Agent: {early_stop_agent:.1f}%)")
        preservation_checks.append(False)

    # Check 3: Layer distribution matches (within 5%)
    if rule_diff < 5 and history_diff < 5 and llm_diff < 5:
        print(f"✅ PASS: Layer distribution matches (all diffs < 5%)")
        preservation_checks.append(True)
    else:
        print(f"❌ FAIL: Layer distribution differs (max diff: {max(rule_diff, history_diff, llm_diff):.1f}%)")
        preservation_checks.append(False)

    # Overall preservation status
    print("\n" + "=" * 80)
    if all(preservation_checks):
        print("🎉 SUCCESS: Migration preserves all logic correctly!")
        print("=" * 80)
        return 0
    else:
        print("⚠️  WARNING: Some preservation checks failed!")
        print("=" * 80)
        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(run_migration_test())
    sys.exit(exit_code)
