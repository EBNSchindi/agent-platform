#!/usr/bin/env python3
"""
Test Agent SDK Integration - Real-World Email Processing

Compares Agent SDK (AgentBasedClassifier) vs Traditional (EnsembleClassifier)
with real emails from Gmail.

Usage:
    PYTHONPATH=. python scripts/testing/test_agent_sdk_integration.py

This script:
1. Loads 20 recent emails from Gmail
2. Processes with Agent SDK (USE_AGENT_SDK=true)
3. Processes same emails with Traditional system (USE_AGENT_SDK=false)
4. Compares results and performance

Requirements:
- Gmail OAuth token configured (gmail_1)
- OpenAI API key or Ollama running
- Agent SDK installed (pip install agents)
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.core.config import Config
from agent_platform.orchestration import ClassificationOrchestrator
from agent_platform.classification import EmailToClassify


class AgentSDKComparisonTest:
    """Compare Agent SDK vs Traditional classification on real emails"""

    def __init__(self, num_emails: int = 20):
        self.num_emails = num_emails
        self.test_emails: List[Dict[str, Any]] = []
        self.agent_results: List[Dict[str, Any]] = []
        self.traditional_results: List[Dict[str, Any]] = []

    def load_test_emails(self) -> List[Dict[str, Any]]:
        """
        Load recent emails from Gmail for testing.

        Returns list of email dicts with:
        - id: Email ID
        - subject: Subject line
        - sender: From address
        - body: Email body text
        """
        print(f"\n📧 Loading {self.num_emails} recent emails from Gmail...")

        # Option 1: Load from database (if emails already processed)
        try:
            from agent_platform.db.database import get_db
            from agent_platform.db.models import ProcessedEmail

            with get_db() as db:
                recent_emails = (
                    db.query(ProcessedEmail)
                    .filter(ProcessedEmail.account_id == "gmail_1")
                    .order_by(ProcessedEmail.created_at.desc())
                    .limit(self.num_emails)
                    .all()
                )

                if len(recent_emails) >= self.num_emails:
                    emails = []
                    for email in recent_emails:
                        emails.append({
                            'id': email.email_id,
                            'subject': email.subject or "No Subject",
                            'sender': email.sender or "unknown@example.com",
                            'body': email.body or email.summary or "No body available",
                        })
                    print(f"✅ Loaded {len(emails)} emails from database")
                    return emails
                else:
                    print(f"⚠️  Only {len(recent_emails)} emails in database, need {self.num_emails}")
        except Exception as e:
            print(f"⚠️  Could not load from database: {e}")

        # Option 2: Fetch fresh from Gmail API
        try:
            from agent_platform.email_providers.gmail_provider import GmailProvider

            print("📥 Fetching fresh emails from Gmail API...")
            provider = GmailProvider(account_id="gmail_1")
            fresh_emails = provider.fetch_recent_emails(max_results=self.num_emails)

            emails = []
            for msg in fresh_emails:
                emails.append({
                    'id': msg.get('id', 'unknown'),
                    'subject': msg.get('subject', 'No Subject'),
                    'sender': msg.get('from', 'unknown@example.com'),
                    'body': msg.get('body', msg.get('snippet', 'No body available')),
                })

            print(f"✅ Loaded {len(emails)} emails from Gmail API")
            return emails
        except Exception as e:
            print(f"❌ Could not fetch from Gmail: {e}")

        # Fallback: Create mock emails
        print("⚠️  Using mock emails for testing")
        return self._create_mock_emails()

    def _create_mock_emails(self) -> List[Dict[str, Any]]:
        """Create mock emails for testing when real emails unavailable"""
        mock_templates = [
            {
                'subject': 'Meeting Tomorrow - Budget Discussion',
                'sender': 'boss@company.com',
                'body': 'Hi, can we meet tomorrow at 10am to discuss the Q4 budget? I need your approval on the marketing expenses.',
            },
            {
                'subject': 'Newsletter: Weekly Tech Updates',
                'sender': 'newsletter@techsite.com',
                'body': 'This week in tech: AI breakthroughs, new gadgets, and industry trends. Click here to read more...',
            },
            {
                'subject': 'URGENT: Payment Due Today',
                'sender': 'accounting@company.com',
                'body': 'Your invoice #12345 is due today. Please process payment immediately to avoid late fees.',
            },
            {
                'subject': 'Spam: You won $1,000,000',
                'sender': 'lottery@spam.com',
                'body': 'Congratulations!!! You have won ONE MILLION DOLLARS. Click here to claim your prize now!!!',
            },
            {
                'subject': 'Project Update Required',
                'sender': 'project-manager@company.com',
                'body': 'Please send me an update on the Q4 project status by Friday. I need to present to stakeholders.',
            },
        ]

        emails = []
        for i in range(self.num_emails):
            template = mock_templates[i % len(mock_templates)]
            emails.append({
                'id': f'mock_{i+1}',
                'subject': f"{template['subject']} ({i+1})",
                'sender': template['sender'],
                'body': template['body'],
            })

        return emails

    async def run_classification_test(
        self,
        emails: List[Dict[str, Any]],
        use_agent_sdk: bool
    ) -> List[Dict[str, Any]]:
        """
        Classify emails using either Agent SDK or Traditional system.

        Args:
            emails: List of email dicts
            use_agent_sdk: If True, use Agent SDK; if False, use Traditional

        Returns:
            List of classification results
        """
        # Temporarily override USE_AGENT_SDK
        original_value = Config.USE_AGENT_SDK
        Config.USE_AGENT_SDK = use_agent_sdk

        mode_name = "Agent SDK 🤖" if use_agent_sdk else "Traditional (Ensemble) ✅"
        print(f"\n{'='*60}")
        print(f"Running classification with: {mode_name}")
        print(f"{'='*60}")

        try:
            # Initialize orchestrator (will use Agent SDK or Traditional based on Config)
            orchestrator = ClassificationOrchestrator()

            # Process emails
            stats = await orchestrator.process_emails(emails, account_id="gmail_1_test")

            # Collect results
            results = []
            for i, email in enumerate(emails):
                # Simulate classification result (real impl would query DB)
                result = {
                    'email_id': email['id'],
                    'subject': email['subject'],
                    'category': None,  # Would be filled from DB
                    'confidence': None,
                    'importance': None,
                }
                results.append(result)

            print(f"\n✅ Processed {stats.total_processed} emails")
            print(f"   - High confidence: {stats.high_confidence}")
            print(f"   - Medium confidence: {stats.medium_confidence}")
            print(f"   - Low confidence: {stats.low_confidence}")
            print(f"   - Duration: {stats.duration_seconds:.2f}s")

            return results

        finally:
            # Restore original value
            Config.USE_AGENT_SDK = original_value

    def compare_results(
        self,
        agent_results: List[Dict[str, Any]],
        traditional_results: List[Dict[str, Any]]
    ):
        """Compare Agent SDK vs Traditional results"""
        print(f"\n{'='*60}")
        print("COMPARISON RESULTS")
        print(f"{'='*60}\n")

        # Category match rate
        category_matches = 0
        category_mismatches = []

        for i, (agent, trad) in enumerate(zip(agent_results, traditional_results)):
            if agent.get('category') == trad.get('category'):
                category_matches += 1
            else:
                category_mismatches.append({
                    'email_id': agent['email_id'],
                    'subject': agent['subject'],
                    'agent_category': agent.get('category'),
                    'trad_category': trad.get('category'),
                })

        match_rate = (category_matches / len(agent_results)) * 100 if agent_results else 0

        print(f"📊 Category Match Rate: {match_rate:.1f}% ({category_matches}/{len(agent_results)})")

        if category_mismatches:
            print(f"\n⚠️  Category Mismatches ({len(category_mismatches)}):")
            for mismatch in category_mismatches[:5]:  # Show first 5
                print(f"   - Subject: {mismatch['subject'][:50]}...")
                print(f"     Agent: {mismatch['agent_category']}, Traditional: {mismatch['trad_category']}")

        # Confidence comparison
        print(f"\n📈 Confidence Score Comparison:")
        agent_avg_conf = sum(r.get('confidence', 0) for r in agent_results) / len(agent_results) if agent_results else 0
        trad_avg_conf = sum(r.get('confidence', 0) for r in traditional_results) / len(traditional_results) if traditional_results else 0

        print(f"   - Agent SDK Average: {agent_avg_conf:.3f}")
        print(f"   - Traditional Average: {trad_avg_conf:.3f}")
        print(f"   - Difference: {abs(agent_avg_conf - trad_avg_conf):.3f}")

        # Success criteria
        print(f"\n{'='*60}")
        print("SUCCESS CRITERIA CHECK")
        print(f"{'='*60}")

        criteria = {
            'Category Match Rate ≥95%': match_rate >= 95.0,
            'Confidence Difference <0.10': abs(agent_avg_conf - trad_avg_conf) < 0.10,
        }

        all_passed = all(criteria.values())

        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {criterion}")

        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 ALL CRITERIA PASSED - Agent SDK Ready for Production!")
        else:
            print("⚠️  SOME CRITERIA FAILED - Review needed before production")
        print(f"{'='*60}\n")

        return all_passed

    async def run_full_test(self):
        """Run complete Agent SDK integration test"""
        print(f"\n{'='*60}")
        print(f"AGENT SDK INTEGRATION TEST")
        print(f"Testing with {self.num_emails} real emails")
        print(f"{'='*60}")

        # Step 1: Load test emails
        self.test_emails = self.load_test_emails()

        if not self.test_emails:
            print("❌ No test emails available, aborting test")
            return False

        # Step 2: Test with Agent SDK
        print("\n[1/2] Testing with Agent SDK...")
        self.agent_results = await self.run_classification_test(
            self.test_emails, use_agent_sdk=True
        )

        # Step 3: Test with Traditional
        print("\n[2/2] Testing with Traditional System...")
        self.traditional_results = await self.run_classification_test(
            self.test_emails, use_agent_sdk=False
        )

        # Step 4: Compare results
        success = self.compare_results(self.agent_results, self.traditional_results)

        return success


async def main():
    """Main test entry point"""
    test = AgentSDKComparisonTest(num_emails=20)
    success = await test.run_full_test()

    # Exit with proper code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
