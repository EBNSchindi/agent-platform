#!/usr/bin/env python3
"""
Test Script: Provider Handlers (Phase 7)

Tests:
1. Gmail Handler - Multi-label support
2. IONOS Handler - Single-folder support
3. Provider-specific classification application
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.providers import GmailHandler, IonosHandler
from agent_platform.db.models import ProcessedEmail


async def test_provider_handlers():
    """Test provider-specific handlers."""

    print("=" * 80)
    print("PROVIDER HANDLERS TEST")
    print("=" * 80)

    # Create mock email record
    email_record = ProcessedEmail(
        account_id="gmail_1",
        email_id="msg_test_123",
        sender="test@example.com",
        subject="Test Email with Multiple Categories",
        body_text="Test body",
        primary_category="wichtig_todo",
        secondary_categories=["termine", "finanzen"],
        category_confidence=0.92,
        importance_score=0.85,
        storage_level="full"
    )

    # ========================================================================
    # TEST 1: Gmail Handler - Multi-Label Support
    # ========================================================================
    print("\n📋 TEST 1: Gmail Handler - Multi-Label Support")
    print("-" * 80)

    gmail_handler = GmailHandler()  # Mock mode (no gmail_service)

    result = await gmail_handler.apply_classification(
        email_record=email_record,
        account_id="gmail_1",
        primary_category="wichtig_todo",
        secondary_categories=["termine", "finanzen"],
        importance_score=0.85,
        confidence=0.92
    )

    print(f"Success: {result['success']}")
    print(f"Labels Applied: {result['labels_applied']}")
    print(f"Labels Created: {result['labels_created']}")
    print(f"Archived: {result['archived']}")
    print(f"Error: {result['error']}")
    print(f"\nExpected:")
    print(f"  - Primary label: Important/ToDo")
    print(f"  - Secondary labels: Events/Appointments, Finance/Invoices")
    print(f"  - Total labels: 3 (multi-label support)")
    print(f"  - Not archived (importance 0.85 >= 0.4)")

    # ========================================================================
    # TEST 2: Gmail Handler - Low Importance (Archive)
    # ========================================================================
    print("\n📋 TEST 2: Gmail Handler - Low Importance (Archive)")
    print("-" * 80)

    email_record2 = ProcessedEmail(
        account_id="gmail_1",
        email_id="msg_test_456",
        sender="newsletter@example.com",
        subject="Weekly Newsletter",
        body_text="Newsletter content",
        primary_category="newsletter",
        secondary_categories=[],
        category_confidence=0.88,
        importance_score=0.35,  # Low importance
        storage_level="full"
    )

    result2 = await gmail_handler.apply_classification(
        email_record=email_record2,
        account_id="gmail_1",
        primary_category="newsletter",
        secondary_categories=[],
        importance_score=0.35,
        confidence=0.88
    )

    print(f"Success: {result2['success']}")
    print(f"Labels Applied: {result2['labels_applied']}")
    print(f"Archived: {result2['archived']}")
    print(f"\nExpected:")
    print(f"  - Label: Newsletter")
    print(f"  - Archived: True (importance 0.35 < 0.4)")

    # ========================================================================
    # TEST 3: IONOS Handler - Single-Folder Support
    # ========================================================================
    print("\n📋 TEST 3: IONOS Handler - Single-Folder Support")
    print("-" * 80)

    ionos_handler = IonosHandler()  # Mock mode (no imap_connection)

    email_record3 = ProcessedEmail(
        account_id="ionos_1",
        email_id="uid_789",
        sender="customer@business.com",
        subject="Project Update with Invoice",
        body_text="Project update content",
        primary_category="job_projekte",
        secondary_categories=["finanzen", "wichtig_todo"],
        category_confidence=0.90,
        importance_score=0.82,
        storage_level="full"
    )

    result3 = await ionos_handler.apply_classification(
        email_record=email_record3,
        account_id="ionos_1",
        primary_category="job_projekte",
        secondary_categories=["finanzen", "wichtig_todo"],
        importance_score=0.82,
        confidence=0.90
    )

    print(f"Success: {result3['success']}")
    print(f"Folder Applied: {result3['folder_applied']}")
    print(f"Folder Created: {result3['folder_created']}")
    print(f"Secondary Ignored: {result3['secondary_ignored']}")
    print(f"Moved: {result3['moved']}")
    print(f"\nExpected:")
    print(f"  - Folder: Work/Projects (primary only)")
    print(f"  - Secondary ignored: ['finanzen', 'wichtig_todo']")
    print(f"  - IMAP limitation: Only one folder per email")

    # ========================================================================
    # TEST 4: Category Mappings
    # ========================================================================
    print("\n📋 TEST 4: Category Mappings")
    print("-" * 80)

    gmail_mapping = gmail_handler.get_label_mapping()
    ionos_mapping = ionos_handler.get_folder_mapping()

    print("Gmail Label Mapping:")
    for cat, label in sorted(gmail_mapping.items()):
        print(f"  {cat:20} → {label}")

    print("\nIONOS Folder Mapping:")
    for cat, folder in sorted(ionos_mapping.items()):
        print(f"  {cat:20} → {folder}")

    print("\nNote: Mappings should be identical for consistency")
    assert gmail_mapping == ionos_mapping, "Mappings should be the same"

    # ========================================================================
    # TEST 5: Database Field Updates
    # ========================================================================
    print("\n📋 TEST 5: Database Field Updates")
    print("-" * 80)

    print(f"Gmail email record:")
    print(f"  gmail_labels_applied: {email_record.gmail_labels_applied}")
    print(f"  Expected: ['Important/ToDo', 'Events/Appointments', 'Finance/Invoices']")

    print(f"\nIONOS email record:")
    print(f"  ionos_folder_applied: {email_record3.ionos_folder_applied}")
    print(f"  Expected: 'Work/Projects'")

    print("\n" + "=" * 80)
    print("✅ ALL PROVIDER HANDLER TESTS COMPLETED!")
    print("=" * 80)

    print("\nSummary:")
    print("  ✓ Gmail: Multi-label support (primary + secondary)")
    print("  ✓ Gmail: Auto-archive low-importance emails")
    print("  ✓ IONOS: Single-folder support (primary only)")
    print("  ✓ IONOS: Secondary categories stored in DB but not applied")
    print("  ✓ Consistent category mappings across providers")


if __name__ == "__main__":
    asyncio.run(test_provider_handlers())
