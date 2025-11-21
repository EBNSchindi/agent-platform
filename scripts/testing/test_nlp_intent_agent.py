#!/usr/bin/env python3
"""
Test Script: NLP Intent Agent (Phase 5)

Tests:
1. Whitelist intent parsing
2. Blacklist intent parsing
3. Mute categories intent parsing
4. Allow only categories intent parsing
5. Set trust level intent parsing
6. Unknown/ambiguous intent parsing
7. Full pipeline: Parse → Execute
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.senders import (
    parse_nlp_intent,
    IntentExecutor,
    create_nlp_intent_agent
)


async def test_nlp_intent_agent():
    """Test NLP Intent Agent functionality."""

    print("=" * 80)
    print("NLP INTENT AGENT TEST")
    print("=" * 80)

    account_id = "test_account"

    # ========================================================================
    # TEST 1: Whitelist Intent
    # ========================================================================
    print("\n📋 TEST 1: Whitelist Intent")
    print("-" * 80)

    text1 = "Amazon auf die Whitelist setzen"
    result1 = await parse_nlp_intent(text1, account_id)

    print(f"Input: \"{text1}\"")
    print(f"Intent Type: {result1.parsed_intent.intent_type}")
    print(f"Sender: {result1.parsed_intent.sender_name or result1.parsed_intent.sender_domain}")
    print(f"Trust Level: {result1.parsed_intent.trust_level}")
    print(f"Confidence: {result1.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result1.parsed_intent.reasoning}")
    print(f"Key Signals: {result1.parsed_intent.key_signals}")
    print(f"Suggested Actions:")
    for action in result1.suggested_actions:
        print(f"  {action}")
    print(f"Requires Confirmation: {result1.requires_confirmation}")

    # ========================================================================
    # TEST 2: Blacklist Intent
    # ========================================================================
    print("\n📋 TEST 2: Blacklist Intent")
    print("-" * 80)

    text2 = "booking.com blockieren"
    result2 = await parse_nlp_intent(text2, account_id)

    print(f"Input: \"{text2}\"")
    print(f"Intent Type: {result2.parsed_intent.intent_type}")
    print(f"Sender: {result2.parsed_intent.sender_domain or result2.parsed_intent.sender_name}")
    print(f"Confidence: {result2.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result2.parsed_intent.reasoning}")
    print(f"Suggested Actions:")
    for action in result2.suggested_actions:
        print(f"  {action}")
    print(f"Requires Confirmation: {result2.requires_confirmation}")

    # ========================================================================
    # TEST 3: Mute Categories Intent
    # ========================================================================
    print("\n📋 TEST 3: Mute Categories Intent")
    print("-" * 80)

    text3 = "Alle Werbemails von Zalando muten"
    result3 = await parse_nlp_intent(text3, account_id)

    print(f"Input: \"{text3}\"")
    print(f"Intent Type: {result3.parsed_intent.intent_type}")
    print(f"Sender: {result3.parsed_intent.sender_name or result3.parsed_intent.sender_domain}")
    print(f"Categories: {result3.parsed_intent.categories}")
    print(f"Confidence: {result3.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result3.parsed_intent.reasoning}")
    print(f"Suggested Actions:")
    for action in result3.suggested_actions:
        print(f"  {action}")

    # ========================================================================
    # TEST 4: Allow Only Categories Intent
    # ========================================================================
    print("\n📋 TEST 4: Allow Only Categories Intent")
    print("-" * 80)

    text4 = "Von Amazon nur Bestellungen und Rechnungen zeigen"
    result4 = await parse_nlp_intent(text4, account_id)

    print(f"Input: \"{text4}\"")
    print(f"Intent Type: {result4.parsed_intent.intent_type}")
    print(f"Sender: {result4.parsed_intent.sender_name or result4.parsed_intent.sender_domain}")
    print(f"Categories: {result4.parsed_intent.categories}")
    print(f"Confidence: {result4.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result4.parsed_intent.reasoning}")
    print(f"Suggested Actions:")
    for action in result4.suggested_actions:
        print(f"  {action}")

    # ========================================================================
    # TEST 5: Set Trust Level Intent
    # ========================================================================
    print("\n📋 TEST 5: Set Trust Level Intent")
    print("-" * 80)

    text5 = "LinkedIn als vertrauenswürdig markieren"
    result5 = await parse_nlp_intent(text5, account_id)

    print(f"Input: \"{text5}\"")
    print(f"Intent Type: {result5.parsed_intent.intent_type}")
    print(f"Sender: {result5.parsed_intent.sender_name or result5.parsed_intent.sender_domain}")
    print(f"Trust Level: {result5.parsed_intent.trust_level}")
    print(f"Confidence: {result5.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result5.parsed_intent.reasoning}")
    print(f"Suggested Actions:")
    for action in result5.suggested_actions:
        print(f"  {action}")

    # ========================================================================
    # TEST 6: Mute Multiple Categories
    # ========================================================================
    print("\n📋 TEST 6: Mute Multiple Categories")
    print("-" * 80)

    text6 = "Keine Newsletter und Werbung von shop@zalando.de"
    result6 = await parse_nlp_intent(text6, account_id)

    print(f"Input: \"{text6}\"")
    print(f"Intent Type: {result6.parsed_intent.intent_type}")
    print(f"Sender Email: {result6.parsed_intent.sender_email}")
    print(f"Categories: {result6.parsed_intent.categories}")
    print(f"Confidence: {result6.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result6.parsed_intent.reasoning}")
    print(f"Suggested Actions:")
    for action in result6.suggested_actions:
        print(f"  {action}")

    # ========================================================================
    # TEST 7: Full Pipeline (Parse + Execute)
    # ========================================================================
    print("\n📋 TEST 7: Full Pipeline - Parse + Execute")
    print("-" * 80)

    text7 = "boss@company.com auf die Whitelist mit nur wichtig_todo und termine"
    result7 = await parse_nlp_intent(text7, account_id)

    print(f"Input: \"{text7}\"")
    print(f"Parsed Intent:")
    print(f"  Type: {result7.parsed_intent.intent_type}")
    print(f"  Sender: {result7.parsed_intent.sender_email}")
    print(f"  Categories: {result7.parsed_intent.categories}")
    print(f"  Confidence: {result7.parsed_intent.confidence:.2f}")

    # Execute the intent
    executor = IntentExecutor()
    exec_result = await executor.execute(
        intent=result7.parsed_intent,
        account_id=account_id,
        source_channel='test_script',
        confirmed=True
    )

    print(f"\nExecution Result:")
    print(f"  Success: {exec_result.success}")
    print(f"  Message: {exec_result.message}")
    if exec_result.sender_preference:
        print(f"  Sender Preference Created: {exec_result.sender_preference.sender_email}")
        print(f"    Trust Level: {exec_result.sender_preference.trust_level}")
        print(f"    Allowed Categories: {exec_result.sender_preference.allowed_categories}")
    if exec_result.user_preference_rule:
        print(f"  User Preference Rule Created: ID={exec_result.user_preference_rule.id}")
        print(f"    Pattern: {exec_result.user_preference_rule.pattern}")
        print(f"    Action: {exec_result.user_preference_rule.action}")

    # ========================================================================
    # TEST 8: Ambiguous/Unknown Intent
    # ========================================================================
    print("\n📋 TEST 8: Ambiguous/Unknown Intent")
    print("-" * 80)

    text8 = "Mach irgendwas mit den Emails"
    result8 = await parse_nlp_intent(text8, account_id)

    print(f"Input: \"{text8}\"")
    print(f"Intent Type: {result8.parsed_intent.intent_type}")
    print(f"Confidence: {result8.parsed_intent.confidence:.2f}")
    print(f"Reasoning: {result8.parsed_intent.reasoning}")
    print(f"Requires Confirmation: {result8.requires_confirmation}")
    print(f"Suggested Actions:")
    for action in result8.suggested_actions:
        print(f"  {action}")

    print("\n" + "=" * 80)
    print("✅ ALL NLP INTENT AGENT TESTS COMPLETED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_nlp_intent_agent())
