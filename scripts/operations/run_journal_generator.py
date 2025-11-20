"""
Operational Script: Journal Generator
Generates daily journals from events and memory-objects.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agent_platform.journal import JournalGenerator
from agent_platform.db.database import init_db


def setup_argparser():
    """Setup command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate daily email journals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate journal for today (gmail_1)
  python run_journal_generator.py gmail_1

  # Generate journal for specific date
  python run_journal_generator.py gmail_1 --date 2025-11-20

  # Generate for all accounts
  python run_journal_generator.py --all

  # Export to file
  python run_journal_generator.py gmail_1 --export

  # Specify output directory
  python run_journal_generator.py gmail_1 --export --output-dir ./my_journals
        """
    )

    parser.add_argument(
        'account_id',
        nargs='?',
        help='Account ID (e.g., gmail_1, gmail_2, gmail_3)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate journals for all configured accounts'
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Date to generate journal for (YYYY-MM-DD, default: today)'
    )

    parser.add_argument(
        '--export',
        action='store_true',
        help='Export journal to markdown file'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='journals',
        help='Directory to export journals (default: journals/)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output, only show errors'
    )

    return parser


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")


def export_journal_to_file(
    journal_entry,
    account_id: str,
    output_dir: str = 'journals'
) -> Path:
    """
    Export journal to markdown file.

    Args:
        journal_entry: JournalEntry object
        account_id: Account ID
        output_dir: Base directory for exports

    Returns:
        Path to exported file
    """
    # Create directory structure: journals/{account_id}/
    account_dir = Path(output_dir) / account_id
    account_dir.mkdir(parents=True, exist_ok=True)

    # Format filename: YYYY-MM-DD.md
    date_str = journal_entry.date.strftime('%Y-%m-%d')
    filename = f"{date_str}.md"
    filepath = account_dir / filename

    # Write markdown content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(journal_entry.content_markdown)

    return filepath


async def generate_journal_for_account(
    account_id: str,
    date: datetime,
    export: bool = False,
    output_dir: str = 'journals',
    quiet: bool = False
) -> bool:
    """
    Generate journal for a single account.

    Args:
        account_id: Account ID
        date: Date to generate journal for
        export: Whether to export to file
        output_dir: Directory for exports
        quiet: Suppress output

    Returns:
        True if successful, False otherwise
    """
    generator = JournalGenerator()

    if not quiet:
        date_str = date.strftime('%Y-%m-%d')
        print(f"\n📝 Generating journal for {account_id} ({date_str})...")

    try:
        # Generate journal
        journal = await generator.generate_daily_journal(
            account_id=account_id,
            date=date
        )

        if not quiet:
            print(f"✅ Journal generated successfully!")
            print(f"   - Journal ID: {journal.journal_id}")
            print(f"   - Title: {journal.title}")

            # Display summary statistics
            stats = journal.summary
            if stats:
                print(f"\n📊 Summary:")
                print(f"   - Emails processed: {stats.get('emails_processed', 0)}")
                print(f"   - Tasks created: {stats.get('tasks_created', 0)}")
                print(f"   - Decisions made: {stats.get('decisions_made', 0)}")
                print(f"   - Questions answered: {stats.get('questions_answered', 0)}")

        # Export to file if requested
        if export:
            filepath = export_journal_to_file(journal, account_id, output_dir)
            if not quiet:
                print(f"\n💾 Exported to: {filepath}")

        # Display journal content if not quiet and not exporting
        if not quiet and not export:
            print("\n" + "=" * 70)
            print(journal.content_markdown)
            print("=" * 70)

        return True

    except Exception as e:
        print(f"❌ Error generating journal for {account_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function."""
    parser = setup_argparser()
    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.account_id:
        parser.error("Either specify an account_id or use --all")

    if args.all and args.account_id:
        parser.error("Cannot specify both account_id and --all")

    # Initialize database
    if not args.quiet:
        print("=" * 70)
        print("JOURNAL GENERATOR")
        print("=" * 70)
        print("\n🔧 Initializing database...")

    init_db()

    # Parse date
    if args.date:
        date = parse_date(args.date)
    else:
        date = datetime.now()

    # Determine accounts to process
    if args.all:
        # Default accounts (can be extended to read from config)
        accounts = ['gmail_1', 'gmail_2', 'gmail_3']
        if not args.quiet:
            print(f"\n📧 Generating journals for all accounts: {', '.join(accounts)}")
    else:
        accounts = [args.account_id]

    # Generate journals
    success_count = 0
    failed_count = 0

    for account_id in accounts:
        success = await generate_journal_for_account(
            account_id=account_id,
            date=date,
            export=args.export,
            output_dir=args.output_dir,
            quiet=args.quiet
        )

        if success:
            success_count += 1
        else:
            failed_count += 1

    # Summary
    if not args.quiet:
        print("\n" + "=" * 70)
        print(f"✅ Successfully generated: {success_count}")
        if failed_count > 0:
            print(f"❌ Failed: {failed_count}")
        print("=" * 70)

    # Exit with error code if any failed
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
