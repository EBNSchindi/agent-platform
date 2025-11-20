"""
Email Automation Scheduler
Runs automated tasks on schedule:
- Hourly inbox checks
- Monthly backups
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from agent_platform.core.config import Config
from agent_platform.db.database import init_db
from modules.email.module import register_email_module
from modules.email.agents.orchestrator import process_all_inboxes
from modules.email.agents.backup import run_monthly_backup
from agent_platform.journal import JournalGenerator


# ============================================================================
# SCHEDULED TASKS
# ============================================================================

async def scheduled_inbox_check():
    """
    Scheduled task: Check all inboxes and process emails.
    Runs every N hours (configured in .env)
    """
    print("\n" + "=" * 70)
    print(f"SCHEDULED INBOX CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        results = await process_all_inboxes(max_emails_per_account=20)

        # Log summary
        total_processed = sum(r.total_emails for r in results)
        total_drafts = sum(r.drafts_created for r in results)
        total_spam = sum(r.spam_filtered for r in results)

        print(f"\n✅ Inbox check completed:")
        print(f"   Processed: {total_processed} emails")
        print(f"   Drafts created: {total_drafts}")
        print(f"   Spam filtered: {total_spam}")

    except Exception as e:
        print(f"\n❌ Error during inbox check: {e}")
        import traceback
        traceback.print_exc()


async def scheduled_monthly_backup():
    """
    Scheduled task: Backup all accounts.
    Runs on 1st day of month at 3 AM (configured in .env)
    """
    print("\n" + "=" * 70)
    print(f"SCHEDULED MONTHLY BACKUP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        results = await run_monthly_backup(max_emails_per_account=None)  # Backup all

        # Log summary
        total_backed_up = sum(r.backed_up for r in results)

        print(f"\n✅ Monthly backup completed:")
        print(f"   Total emails backed up: {total_backed_up}")

    except Exception as e:
        print(f"\n❌ Error during backup: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# SCHEDULER SETUP
# ============================================================================

def setup_scheduler() -> AsyncIOScheduler:
    """
    Configure and return scheduler with all tasks.

    Returns:
        Configured AsyncIOScheduler instance
    """
    scheduler = AsyncIOScheduler()

    # Task 1: Hourly inbox check
    inbox_check_interval = Config.INBOX_CHECK_INTERVAL_HOURS
    scheduler.add_job(
        scheduled_inbox_check,
        trigger=IntervalTrigger(hours=inbox_check_interval),
        id='inbox_check',
        name=f'Check inboxes every {inbox_check_interval} hour(s)',
        replace_existing=True
    )

    print(f"✅ Scheduled: Inbox check every {inbox_check_interval} hour(s)")

    # Task 2: Monthly backup
    backup_day = Config.BACKUP_DAY_OF_MONTH
    backup_hour = Config.BACKUP_HOUR

    scheduler.add_job(
        scheduled_monthly_backup,
        trigger=CronTrigger(day=backup_day, hour=backup_hour, minute=0),
        id='monthly_backup',
        name=f'Monthly backup on day {backup_day} at {backup_hour}:00',
        replace_existing=True
    )

    print(f"✅ Scheduled: Monthly backup on day {backup_day} at {backup_hour}:00")

    # Task 3: Daily journal generation
    journal_hour = Config.JOURNAL_GENERATION_HOUR

    scheduler.add_job(
        scheduled_journal_generation,
        trigger=CronTrigger(hour=journal_hour, minute=0),  # Daily at configured hour
        id='journal_generation',
        name=f'Daily journal generation at {journal_hour}:00',
        replace_existing=True
    )

    print(f"✅ Scheduled: Daily journal generation at {journal_hour}:00")

    # Task 4: Daily spam cleanup (optional - archives old spam)
    scheduler.add_job(
        scheduled_spam_cleanup,
        trigger=CronTrigger(hour=2, minute=0),  # 2 AM daily
        id='spam_cleanup',
        name='Daily spam cleanup at 2:00 AM',
        replace_existing=True
    )

    print(f"✅ Scheduled: Daily spam cleanup at 2:00 AM")

    return scheduler


async def scheduled_spam_cleanup():
    """
    Scheduled task: Archive old spam emails.
    Runs daily at 2 AM.
    """
    print("\n" + "=" * 70)
    print(f"SCHEDULED SPAM CLEANUP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        # This is a placeholder - you can implement spam archiving logic here
        print("🗑️  Spam cleanup not yet implemented")
        print("   (Future: archive spam older than 30 days)")

    except Exception as e:
        print(f"❌ Error during spam cleanup: {e}")


async def scheduled_journal_generation():
    """
    Scheduled task: Generate daily journals for all accounts.
    Runs daily at configured hour (default: 8 PM).
    """
    print("\n" + "=" * 70)
    print(f"SCHEDULED JOURNAL GENERATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        generator = JournalGenerator()

        # All accounts to generate journals for
        accounts = ['gmail_1', 'gmail_2', 'gmail_3']

        success_count = 0
        failed_count = 0

        for account_id in accounts:
            try:
                print(f"\n📝 Generating journal for {account_id}...")

                # Generate journal (for today)
                journal = await generator.generate_daily_journal(
                    account_id=account_id,
                    date=None  # Today
                )

                # Export to file
                from pathlib import Path
                filepath = generator.export_to_file(
                    journal_entry=journal,
                    account_id=account_id,
                    output_dir='journals'
                )

                print(f"✅ Journal generated and exported: {filepath}")
                success_count += 1

            except Exception as e:
                print(f"❌ Failed to generate journal for {account_id}: {str(e)}")
                failed_count += 1

        # Summary
        print(f"\n✅ Journal generation completed:")
        print(f"   Success: {success_count}")
        if failed_count > 0:
            print(f"   Failed: {failed_count}")

    except Exception as e:
        print(f"\n❌ Error during journal generation: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main():
    """
    Main scheduler loop.
    Runs continuously until stopped with Ctrl+C.
    """
    print("\n" + "=" * 70)
    print("EMAIL AUTOMATION SCHEDULER")
    print("=" * 70)

    # Initialize platform
    print("\n🔧 Initializing platform...")
    init_db()
    register_email_module()

    # Setup scheduler
    print("\n🕐 Setting up scheduler...\n")
    scheduler = setup_scheduler()

    # Start scheduler
    print("\n🚀 Starting scheduler...")
    print("   Press Ctrl+C to stop\n")

    scheduler.start()

    # Print next run times
    print("Next scheduled runs:")
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            print(f"  - {job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "=" * 70)
    print("SCHEDULER RUNNING")
    print("=" * 70)
    print("\nℹ️  The scheduler will run tasks automatically at scheduled times.")
    print("   Check logs above for next execution times.\n")

    # Run inbox check immediately on startup (optional)
    run_now = input("Run inbox check now? (y/n): ").lower().strip()
    if run_now == 'y':
        await scheduled_inbox_check()

    # Keep scheduler running
    try:
        # Run forever
        while True:
            await asyncio.sleep(60)  # Check every minute

    except (KeyboardInterrupt, SystemExit):
        print("\n\n🛑 Stopping scheduler...")
        scheduler.shutdown()
        print("✅ Scheduler stopped\n")


# ============================================================================
# CLI COMMANDS
# ============================================================================

def print_help():
    """Print help message"""
    print("""
Email Automation Scheduler

Usage:
  python scripts/run_scheduler.py           Start the scheduler
  python scripts/run_scheduler.py --help    Show this help

Scheduled Tasks:
  1. Inbox Check:
     - Frequency: Every {inbox_check} hour(s)
     - Actions: Classify emails, generate drafts, filter spam

  2. Monthly Backup:
     - Frequency: Day {backup_day} of month at {backup_hour}:00
     - Actions: Backup all emails to backup account

  3. Journal Generation:
     - Frequency: Daily at {journal_hour}:00
     - Actions: Generate daily journals, export to markdown files

  4. Spam Cleanup:
     - Frequency: Daily at 2:00 AM
     - Actions: Archive old spam emails

Configuration:
  Edit .env to change:
    INBOX_CHECK_INTERVAL_HOURS={inbox_check}
    BACKUP_DAY_OF_MONTH={backup_day}
    BACKUP_HOUR={backup_hour}
    JOURNAL_GENERATION_HOUR={journal_hour}

Stop Scheduler:
  Press Ctrl+C
    """.format(
        inbox_check=Config.INBOX_CHECK_INTERVAL_HOURS,
        backup_day=Config.BACKUP_DAY_OF_MONTH,
        backup_hour=Config.BACKUP_HOUR,
        journal_hour=Config.JOURNAL_GENERATION_HOUR
    ))


if __name__ == "__main__":
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_help()
        sys.exit(0)

    # Run scheduler
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
