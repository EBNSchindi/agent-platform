"""
Full Workflow Test
Tests complete email automation workflow across all accounts.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.core.config import Config, Mode
from agent_platform.db.database import init_db
from modules.email.module import register_email_module
from modules.email.agents.orchestrator import EmailOrchestrator
from modules.email.agents.backup import run_monthly_backup


async def main():
    """Test complete workflow"""

    print("\n" + "=" * 70)
    print("FULL EMAIL AUTOMATION WORKFLOW TEST")
    print("=" * 70)

    # Initialize
    print("\n🔧 Step 1: Initialize Platform")
    print("-" * 70)
    init_db()
    registry = register_email_module()
    registry.print_summary()

    # Show configuration
    print("\n⚙️  Step 2: Configuration Overview")
    print("-" * 70)
    print(f"Default Mode: {Config.DEFAULT_MODE.value.upper()}")
    print(f"Responder Confidence Threshold: {Config.RESPONDER_CONFIDENCE_THRESHOLD}")
    print(f"Inbox Check Interval: Every {Config.INBOX_CHECK_INTERVAL_HOURS} hour(s)")
    print(f"Monthly Backup: Day {Config.BACKUP_DAY_OF_MONTH} at {Config.BACKUP_HOUR}:00")
    print()

    # Show configured accounts
    print("Configured Email Accounts:")
    for account_id, account_config in Config.GMAIL_ACCOUNTS.items():
        if account_config['email']:
            mode = Config.get_account_mode(account_id)
            print(f"  ✅ {account_id}: {account_config['email']} (Mode: {mode.value})")
        else:
            print(f"  ⏭️  {account_id}: Not configured")

    if Config.IONOS_ACCOUNT['email']:
        mode = Config.get_account_mode('ionos')
        print(f"  ✅ ionos: {Config.IONOS_ACCOUNT['email']} (Mode: {mode.value})")
    else:
        print(f"  ⏭️  ionos: Not configured")

    if Config.BACKUP_ACCOUNT['email']:
        print(f"  📦 backup: {Config.BACKUP_ACCOUNT['email']}")
    else:
        print(f"  ⏭️  backup: Not configured")

    # Menu
    print("\n" + "=" * 70)
    print("WORKFLOW OPTIONS")
    print("=" * 70)
    print("\nWhat would you like to test?\n")
    print("1. Process Single Account (choose account + mode)")
    print("2. Process All Accounts (current modes)")
    print("3. Run Monthly Backup (all accounts)")
    print("4. Full Demo (classify → respond → backup)")
    print("5. Exit")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        await test_single_account()
    elif choice == "2":
        await test_all_accounts()
    elif choice == "3":
        await test_backup()
    elif choice == "4":
        await test_full_demo()
    elif choice == "5":
        print("\n👋 Goodbye!\n")
        return
    else:
        print("\n❌ Invalid choice")


async def test_single_account():
    """Test single account processing"""
    print("\n" + "=" * 70)
    print("SINGLE ACCOUNT TEST")
    print("=" * 70)

    # Select account
    print("\nAvailable accounts:")
    accounts = []
    for account_id, account_config in Config.GMAIL_ACCOUNTS.items():
        if account_config['email']:
            accounts.append(account_id)
            print(f"  {len(accounts)}. {account_id} ({account_config['email']})")

    if Config.IONOS_ACCOUNT['email']:
        accounts.append("ionos")
        print(f"  {len(accounts)}. ionos ({Config.IONOS_ACCOUNT['email']})")

    account_choice = input(f"\nSelect account (1-{len(accounts)}): ").strip()

    try:
        account_id = accounts[int(account_choice) - 1]
    except (ValueError, IndexError):
        print("❌ Invalid choice")
        return

    # Select mode
    print("\nSelect mode:")
    print("  1. DRAFT (generate drafts for review)")
    print("  2. AUTO_REPLY (send automatically if high confidence)")
    print("  3. MANUAL (classify and label only)")

    mode_choice = input("\nSelect mode (1-3): ").strip()

    mode_map = {"1": Mode.DRAFT, "2": Mode.AUTO_REPLY, "3": Mode.MANUAL}
    mode = mode_map.get(mode_choice, Mode.DRAFT)

    # Max emails
    max_emails = input("\nMax emails to process (default: 10): ").strip()
    max_emails = int(max_emails) if max_emails.isdigit() else 10

    # Process
    orchestrator = EmailOrchestrator()
    result = await orchestrator.process_account(account_id, max_emails, mode)

    print(f"\n✅ Processing complete! See summary above.")


async def test_all_accounts():
    """Test all accounts processing"""
    print("\n" + "=" * 70)
    print("ALL ACCOUNTS TEST")
    print("=" * 70)

    max_emails = input("\nMax emails per account (default: 10): ").strip()
    max_emails = int(max_emails) if max_emails.isdigit() else 10

    orchestrator = EmailOrchestrator()
    results = await orchestrator.process_all_accounts(max_emails)

    print(f"\n✅ All accounts processed! See summary above.")


async def test_backup():
    """Test backup functionality"""
    print("\n" + "=" * 70)
    print("BACKUP TEST")
    print("=" * 70)

    print("\n⚠️  Warning: This will backup emails to your backup account.")
    print("   For testing, we'll limit to 50 emails per account.\n")

    confirm = input("Proceed with backup test? (y/n): ").lower().strip()

    if confirm != 'y':
        print("❌ Backup cancelled")
        return

    results = await run_monthly_backup(max_emails_per_account=50)

    print(f"\n✅ Backup complete! See summary above.")


async def test_full_demo():
    """Full demonstration workflow"""
    print("\n" + "=" * 70)
    print("FULL DEMO WORKFLOW")
    print("=" * 70)

    print("\nThis demo will:")
    print("  1. Process all inboxes (classify + generate drafts)")
    print("  2. Show results for each account")
    print("  3. Optionally run a backup test\n")

    confirm = input("Proceed with full demo? (y/n): ").lower().strip()

    if confirm != 'y':
        print("❌ Demo cancelled")
        return

    # Step 1: Process inboxes
    print("\n📧 Step 1: Processing All Inboxes")
    print("=" * 70)

    orchestrator = EmailOrchestrator()
    results = await orchestrator.process_all_accounts(max_emails_per_account=5)

    # Step 2: Ask about backup
    print("\n📦 Step 2: Backup (Optional)")
    print("=" * 70)

    backup_choice = input("\nRun backup test (50 emails per account)? (y/n): ").lower().strip()

    if backup_choice == 'y':
        backup_results = await run_monthly_backup(max_emails_per_account=50)

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\n✅ Full workflow demonstration completed!")
    print("\nNext steps:")
    print("  - Review generated drafts in your email accounts")
    print("  - Adjust modes in .env or via Config.set_account_mode()")
    print("  - Run scripts/run_scheduler.py for automated operation\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
