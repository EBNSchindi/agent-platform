"""
Scheduler Jobs for Email Classification System

Defines scheduled jobs for:
1. Daily digest generation and sending
2. Feedback checking (detecting user actions)
3. Queue cleanup (removing old reviewed items)

These jobs are meant to be registered with APScheduler.
"""

from datetime import datetime
from typing import Optional

from agent_platform.review import DailyDigestGenerator, ReviewQueueManager
from agent_platform.feedback import FeedbackChecker


# ============================================================================
# DAILY DIGEST JOB
# ============================================================================

def send_daily_digest(
    account_id: Optional[str] = None,
    user_email: str = "user@example.com",
    hours_back: int = 24,
    max_items: int = 20,
):
    """
    Generate and send daily digest email to user.

    This job should run once per day (e.g., 9 AM) to send a summary
    of all pending review items.

    Args:
        account_id: Optional account ID to filter by (None = all accounts)
        user_email: Email address to send digest to
        hours_back: How many hours back to include items from
        max_items: Maximum items to include in digest

    Returns:
        Dictionary with status and statistics
    """
    print(f"\n{'=' * 70}")
    print(f"DAILY DIGEST JOB - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}\n")

    try:
        # Generate digest
        digest_generator = DailyDigestGenerator()

        digest = digest_generator.generate_digest(
            account_id=account_id,
            hours_back=hours_back,
            limit=max_items,
        )

        summary = digest['summary']

        if summary['total_items'] == 0:
            print("📭 No items to review - skipping digest")
            return {
                'status': 'skipped',
                'reason': 'no_items',
                'total_items': 0,
            }

        print(f"📧 Generated digest with {summary['total_items']} items")
        print(f"   Categories: {list(summary['by_category'].keys())}")

        # Send email (placeholder - would integrate with email sending)
        # In production, this would use an email service
        print(f"\n📤 Sending digest to {user_email}...")

        # Example pseudo-code for sending:
        """
        from modules.email.tools.gmail_tools import send_email

        send_email(
            to=user_email,
            subject=f"Daily Review Digest ({summary['total_items']} items)",
            html_body=digest['html'],
            text_body=digest['text'],
        )
        """

        # For now, just save to file for testing
        output_file = f"/tmp/daily_digest_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(digest['html'])

        print(f"✅ Digest saved to {output_file}")
        print(f"   (In production, this would be emailed to {user_email})")

        return {
            'status': 'sent',
            'total_items': summary['total_items'],
            'by_category': summary['by_category'],
            'output_file': output_file,
        }

    except Exception as e:
        print(f"❌ Error generating digest: {e}")
        import traceback
        traceback.print_exc()

        return {
            'status': 'error',
            'error': str(e),
        }


# ============================================================================
# FEEDBACK CHECKING JOB
# ============================================================================

def check_user_feedback(
    account_id: Optional[str] = None,
    hours_back: int = 1,
):
    """
    Check for user actions on emails (replies, archives, deletes, etc.).

    This job should run periodically (e.g., every hour) to detect user
    actions and track feedback for learning.

    Args:
        account_id: Optional account ID to check (None = all accounts)
        hours_back: How many hours back to check for actions

    Returns:
        Dictionary with statistics
    """
    print(f"\n{'=' * 70}")
    print(f"FEEDBACK CHECKING JOB - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}\n")

    try:
        checker = FeedbackChecker()

        if account_id:
            # Check single account
            print(f"🔍 Checking {account_id} for user actions...")
            stats = checker.check_account_for_feedback(
                account_id=account_id,
                hours_back=hours_back,
            )

            print(f"✅ Found {stats['actions_detected']} actions")
            if stats['actions_by_type']:
                print(f"   By type: {stats['actions_by_type']}")

            return {
                'status': 'completed',
                'accounts_checked': 1,
                'total_actions': stats['actions_detected'],
                'results': {account_id: stats},
            }

        else:
            # Check all accounts
            print(f"🔍 Checking all accounts for user actions...")
            results = checker.check_all_accounts(hours_back=hours_back)

            total_actions = sum(
                result.get('actions_detected', 0)
                for result in results.values()
                if isinstance(result, dict) and 'actions_detected' in result
            )

            print(f"✅ Checked {len(results)} accounts")
            print(f"   Total actions detected: {total_actions}")

            for acc_id, result in results.items():
                if isinstance(result, dict) and result.get('actions_detected', 0) > 0:
                    print(f"   {acc_id}: {result['actions_detected']} actions")

            return {
                'status': 'completed',
                'accounts_checked': len(results),
                'total_actions': total_actions,
                'results': results,
            }

    except Exception as e:
        print(f"❌ Error checking feedback: {e}")
        import traceback
        traceback.print_exc()

        return {
            'status': 'error',
            'error': str(e),
        }


# ============================================================================
# QUEUE CLEANUP JOB
# ============================================================================

def cleanup_review_queue(
    days_to_keep: int = 30,
):
    """
    Clean up old reviewed items from the review queue.

    This job should run periodically (e.g., daily) to keep the
    review queue database clean.

    Args:
        days_to_keep: How many days to keep reviewed items

    Returns:
        Dictionary with cleanup statistics
    """
    print(f"\n{'=' * 70}")
    print(f"QUEUE CLEANUP JOB - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}\n")

    try:
        queue_manager = ReviewQueueManager()

        print(f"🧹 Cleaning up items older than {days_to_keep} days...")
        deleted_count = queue_manager.cleanup_old_reviewed_items(
            days_to_keep=days_to_keep
        )

        print(f"✅ Deleted {deleted_count} old items")

        return {
            'status': 'completed',
            'items_deleted': deleted_count,
            'days_to_keep': days_to_keep,
        }

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()

        return {
            'status': 'error',
            'error': str(e),
        }


# ============================================================================
# SCHEDULER SETUP EXAMPLE
# ============================================================================

def setup_scheduler():
    """
    Example setup for APScheduler with all jobs.

    Usage:
        from agent_platform.orchestration.scheduler_jobs import setup_scheduler

        scheduler = setup_scheduler()
        scheduler.start()

    Returns:
        Configured AsyncIOScheduler
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    # Daily digest - every day at 9 AM
    scheduler.add_job(
        send_daily_digest,
        trigger='cron',
        hour=9,
        minute=0,
        id='daily_digest',
        kwargs={
            'user_email': 'user@example.com',
            'hours_back': 24,
            'max_items': 20,
        }
    )

    # Feedback checking - every hour
    scheduler.add_job(
        check_user_feedback,
        trigger='interval',
        hours=1,
        id='feedback_check',
        kwargs={
            'hours_back': 1,
        }
    )

    # Queue cleanup - daily at 2 AM
    scheduler.add_job(
        cleanup_review_queue,
        trigger='cron',
        hour=2,
        minute=0,
        id='queue_cleanup',
        kwargs={
            'days_to_keep': 30,
        }
    )

    print("✅ Scheduler configured with 3 jobs:")
    print("   1. Daily Digest - Every day at 9 AM")
    print("   2. Feedback Check - Every hour")
    print("   3. Queue Cleanup - Daily at 2 AM")

    return scheduler


# ============================================================================
# MANUAL JOB EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Manual execution for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scheduler_jobs.py <job_name>")
        print("Jobs: digest, feedback, cleanup")
        sys.exit(1)

    job_name = sys.argv[1].lower()

    if job_name == "digest":
        result = send_daily_digest()
        print(f"\nResult: {result}")

    elif job_name == "feedback":
        result = check_user_feedback()
        print(f"\nResult: {result}")

    elif job_name == "cleanup":
        result = cleanup_review_queue()
        print(f"\nResult: {result}")

    else:
        print(f"Unknown job: {job_name}")
        sys.exit(1)
