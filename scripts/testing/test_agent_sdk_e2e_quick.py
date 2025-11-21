#!/usr/bin/env python3
"""
Quick E2E Test: Agent SDK Integration
Tests complete workflow with 2-3 real emails using Agent SDK.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.core.config import Config
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.classification import EmailToClassify


async def test_agent_sdk_e2e():
    """E2E Test: 3 emails with Agent SDK"""

    print("\n" + "="*70)
    print("E2E TEST: Agent SDK Integration")
    print("="*70)

    # Test emails (realistic samples)
    test_emails = [
        {
            'id': 'test_1',
            'subject': 'URGENT: Payment Due Today',
            'sender': 'accounting@company.com',
            'body': 'Your invoice #12345 is due today. Please process payment immediately.',
        },
        {
            'id': 'test_2',
            'subject': 'Newsletter: Weekly Tech Updates',
            'sender': 'newsletter@techsite.com',
            'body': 'This week in tech: AI breakthroughs, new gadgets. Click to read more...',
        },
        {
            'id': 'test_3',
            'subject': 'Meeting Tomorrow',
            'sender': 'colleague@company.com',
            'body': 'Can we meet at 10am tomorrow to discuss the project timeline?',
        },
    ]

    # Test with Agent SDK
    print("\n[1/2] Testing with Agent SDK enabled...")
    Config.USE_AGENT_SDK = True

    try:
        orchestrator_agent = ClassificationOrchestrator()
        stats_agent = await orchestrator_agent.process_emails(test_emails, account_id="test_agent")

        print(f"\n✅ Agent SDK Results:")
        print(f"   - Total processed: {stats_agent.total_processed}")
        print(f"   - High confidence: {stats_agent.high_confidence}")
        print(f"   - Medium confidence: {stats_agent.medium_confidence}")
        print(f"   - Low confidence: {stats_agent.low_confidence}")
        print(f"   - Duration: {stats_agent.duration_seconds:.2f}s")

        agent_success = stats_agent.total_processed == 3

    except Exception as e:
        print(f"\n❌ Agent SDK Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        agent_success = False

    # Test with Traditional (comparison)
    print("\n[2/2] Testing with Traditional system...")
    Config.USE_AGENT_SDK = False

    try:
        orchestrator_trad = ClassificationOrchestrator()
        stats_trad = await orchestrator_trad.process_emails(test_emails, account_id="test_trad")

        print(f"\n✅ Traditional Results:")
        print(f"   - Total processed: {stats_trad.total_processed}")
        print(f"   - High confidence: {stats_trad.high_confidence}")
        print(f"   - Medium confidence: {stats_trad.medium_confidence}")
        print(f"   - Low confidence: {stats_trad.low_confidence}")
        print(f"   - Duration: {stats_trad.duration_seconds:.2f}s")

        trad_success = stats_trad.total_processed == 3

    except Exception as e:
        print(f"\n❌ Traditional Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        trad_success = False

    # Final verdict
    print("\n" + "="*70)
    print("E2E TEST RESULTS")
    print("="*70)

    if agent_success and trad_success:
        print("✅ BOTH SYSTEMS WORKING - E2E Test PASSED")
        print(f"\n   Agent SDK:     {stats_agent.total_processed}/3 emails processed in {stats_agent.duration_seconds:.2f}s")
        print(f"   Traditional:   {stats_trad.total_processed}/3 emails processed in {stats_trad.duration_seconds:.2f}s")
        print(f"\n   Performance: Agent SDK is {stats_agent.duration_seconds/stats_trad.duration_seconds:.2f}x vs Traditional")
        return True
    else:
        print("❌ E2E TEST FAILED")
        if not agent_success:
            print("   - Agent SDK: FAILED")
        if not trad_success:
            print("   - Traditional: FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_agent_sdk_e2e())
    sys.exit(0 if success else 1)
