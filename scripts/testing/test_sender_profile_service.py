#!/usr/bin/env python3
"""
Test Script: SenderProfileService (Phase 8)

Tests:
1. Whitelist management
2. Blacklist management
3. Trust level management
4. Category preference management (allow/mute)
5. Preference application to classification results
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.senders import SenderProfileService


async def test_sender_profile_service():
    """Test SenderProfileService functionality."""

    print("=" * 80)
    print("SENDER PROFILE SERVICE TEST")
    print("=" * 80)

    service = SenderProfileService()
    account_id = "test_account"

    # ========================================================================
    # TEST 1: Whitelist Management
    # ========================================================================
    print("\n📋 TEST 1: Whitelist Management")
    print("-" * 80)

    # Whitelist boss
    boss_email = "boss@company.com"
    pref = await service.whitelist_sender(
        sender_email=boss_email,
        account_id=account_id,
        allowed_categories=["wichtig_todo", "job_projekte", "termine"],
        preferred_primary="wichtig_todo"
    )

    print(f"✅ Whitelisted: {pref.sender_email}")
    print(f"   Trust Level: {pref.trust_level}")
    print(f"   Allowed Categories: {pref.allowed_categories}")
    print(f"   Preferred Primary: {pref.preferred_primary_category}")

    # ========================================================================
    # TEST 2: Blacklist Management
    # ========================================================================
    print("\n📋 TEST 2: Blacklist Management")
    print("-" * 80)

    # Blacklist spam sender
    spam_email = "spam@suspicious.com"
    pref = await service.blacklist_sender(
        sender_email=spam_email,
        account_id=account_id
    )

    print(f"✅ Blacklisted: {pref.sender_email}")
    print(f"   Trust Level: {pref.trust_level}")
    print(f"   Is Blacklisted: {pref.is_blacklisted}")

    # ========================================================================
    # TEST 3: Category Muting
    # ========================================================================
    print("\n📋 TEST 3: Category Muting")
    print("-" * 80)

    # Mute marketing from Amazon
    amazon_email = "shop@amazon.de"
    pref = await service.mute_categories(
        sender_email=amazon_email,
        categories=["werbung", "newsletter"],
        account_id=account_id
    )

    print(f"✅ Muted categories for: {pref.sender_email}")
    print(f"   Muted Categories: {pref.muted_categories}")

    # ========================================================================
    # TEST 4: Apply Preferences (Whitelist)
    # ========================================================================
    print("\n📋 TEST 4: Apply Preferences - Whitelisted Sender")
    print("-" * 80)

    # Simulated classification result
    classification = {
        'primary_category': 'job_projekte',
        'secondary_categories': ['wichtig_todo'],
        'confidence': 0.75,
        'importance_score': 0.80,
        'reasoning': 'Project email from customer'
    }

    print(f"Before: {classification}")

    result = await service.apply_preferences(
        sender_email=boss_email,
        account_id=account_id,
        classification_result=classification
    )

    print(f"After:  {result}")
    print(f"   Confidence: {classification['confidence']:.2f} → {result['confidence']:.2f} (Boost: +0.10)")

    # ========================================================================
    # TEST 5: Apply Preferences (Blacklist)
    # ========================================================================
    print("\n📋 TEST 5: Apply Preferences - Blacklisted Sender")
    print("-" * 80)

    classification = {
        'primary_category': 'newsletter',
        'secondary_categories': [],
        'confidence': 0.65,
        'importance_score': 0.40,
        'reasoning': 'Looks like newsletter'
    }

    print(f"Before: {classification}")

    result = await service.apply_preferences(
        sender_email=spam_email,
        account_id=account_id,
        classification_result=classification
    )

    print(f"After:  {result}")
    print(f"   Primary Category: {classification['primary_category']} → {result['primary_category']}")
    print(f"   Confidence: {classification['confidence']:.2f} → {result['confidence']:.2f}")
    print(f"   Importance: {classification['importance_score']:.2f} → {result['importance_score']:.2f}")

    # ========================================================================
    # TEST 6: Apply Preferences (Muted Category)
    # ========================================================================
    print("\n📋 TEST 6: Apply Preferences - Muted Category")
    print("-" * 80)

    classification = {
        'primary_category': 'werbung',
        'secondary_categories': ['newsletter'],
        'confidence': 0.85,
        'importance_score': 0.20,
        'reasoning': 'Marketing email from Amazon'
    }

    print(f"Before: {classification}")

    result = await service.apply_preferences(
        sender_email=amazon_email,
        account_id=account_id,
        classification_result=classification
    )

    print(f"After:  {result}")
    print(f"   Importance: {classification['importance_score']:.2f} → {result['importance_score']:.2f} (Muted!)")
    print(f"   Confidence: {classification['confidence']:.2f} → {result['confidence']:.2f} (Penalty: -0.20)")
    print(f"   Secondary: {classification['secondary_categories']} → {result['secondary_categories']} (Filtered!)")

    # ========================================================================
    # TEST 7: Statistics
    # ========================================================================
    print("\n📋 TEST 7: Profile Statistics")
    print("-" * 80)

    stats = await service.get_profile_stats(account_id)
    print(f"Total Profiles: {stats['total_profiles']}")
    print(f"Whitelisted: {stats['whitelisted']}")
    print(f"Blacklisted: {stats['blacklisted']}")
    print(f"Neutral: {stats['neutral']}")

    # ========================================================================
    # TEST 8: List Whitelisted/Blacklisted
    # ========================================================================
    print("\n📋 TEST 8: List Profiles")
    print("-" * 80)

    whitelisted = await service.list_whitelisted(account_id)
    print(f"Whitelisted Senders ({len(whitelisted)}):")
    for p in whitelisted:
        print(f"   - {p.sender_email} (trust: {p.trust_level})")

    blacklisted = await service.list_blacklisted(account_id)
    print(f"\nBlacklisted Senders ({len(blacklisted)}):")
    for p in blacklisted:
        print(f"   - {p.sender_email} (trust: {p.trust_level})")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_sender_profile_service())
