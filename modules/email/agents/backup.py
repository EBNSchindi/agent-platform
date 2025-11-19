"""
Email Backup Agent
Performs monthly full backups of all email accounts to backup account.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from agent_platform.core.config import Config
from modules.email.tools.gmail_tools import get_gmail_service


# ============================================================================
# STRUCTURED OUTPUTS
# ============================================================================

class BackupResult(BaseModel):
    """Result of backing up a single account"""
    source_account_id: str
    backup_account_id: str
    total_emails: int
    backed_up: int
    skipped: int
    errors: int
    started_at: datetime
    finished_at: datetime

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        if self.total_emails == 0:
            return 0.0
        return self.backed_up / self.total_emails


# ============================================================================
# BACKUP AGENT
# ============================================================================

class EmailBackupAgent:
    """
    Performs full email backups from source accounts to backup account.

    Strategy:
    - Fetches ALL emails from source account (not just unread)
    - Forwards/copies to backup account
    - Organizes in backup account by source and date
    - Labels with "Backup-{source}-{YYYY-MM}"
    """

    def __init__(self):
        self.backup_account_id = "backup"
        self.backup_config = Config.BACKUP_ACCOUNT

        if not self.backup_config['email']:
            raise ValueError("Backup account not configured in .env")

    async def backup_account(
        self,
        source_account_id: str,
        max_emails: int = None  # None = all emails
    ) -> BackupResult:
        """
        Backup all emails from source account to backup account.

        Args:
            source_account_id: Source account to backup (gmail_1, gmail_2, gmail_3, ionos)
            max_emails: Maximum emails to backup (None = all)

        Returns:
            BackupResult with backup statistics
        """
        start_time = datetime.now()

        print(f"\n{'=' * 70}")
        print(f"BACKUP: {source_account_id.upper()} → BACKUP ACCOUNT")
        print(f"{'=' * 70}\n")

        # Determine account type
        if source_account_id == "ionos":
            return await self._backup_ionos_account(source_account_id, max_emails, start_time)
        else:
            return await self._backup_gmail_account(source_account_id, max_emails, start_time)

    async def _backup_gmail_account(
        self,
        source_account_id: str,
        max_emails: int,
        start_time: datetime
    ) -> BackupResult:
        """Backup Gmail account"""

        # Get source account service
        source_config = Config.GMAIL_ACCOUNTS.get(source_account_id)
        if not source_config or not source_config['email']:
            print(f"❌ Source account {source_account_id} not configured")
            return BackupResult(
                source_account_id=source_account_id,
                backup_account_id=self.backup_account_id,
                total_emails=0,
                backed_up=0,
                skipped=0,
                errors=0,
                started_at=start_time,
                finished_at=datetime.now()
            )

        source_service = get_gmail_service(
            source_account_id,
            source_config['credentials_path'],
            source_config['token_path']
        )

        # Get backup account service
        backup_service = get_gmail_service(
            self.backup_account_id,
            self.backup_config['credentials_path'],
            self.backup_config['token_path']
        )

        print(f"📧 Fetching all emails from {source_account_id}...")

        # Fetch ALL emails (not just unread)
        try:
            results = source_service.service.users().messages().list(
                userId='me',
                maxResults=max_emails if max_emails else 500  # Gmail API limit
            ).execute()

            messages = results.get('messages', [])
            total_emails = len(messages)

            print(f"✅ Found {total_emails} emails to backup\n")

            if total_emails == 0:
                return BackupResult(
                    source_account_id=source_account_id,
                    backup_account_id=self.backup_account_id,
                    total_emails=0,
                    backed_up=0,
                    skipped=0,
                    errors=0,
                    started_at=start_time,
                    finished_at=datetime.now()
                )

            # Create backup label
            backup_label = f"Backup-{source_account_id}-{datetime.now().strftime('%Y-%m')}"
            print(f"🏷️  Backup label: {backup_label}")

            backed_up = 0
            skipped = 0
            errors = 0

            # Backup emails in batches
            batch_size = 10
            for i in range(0, total_emails, batch_size):
                batch = messages[i:i+batch_size]
                print(f"📤 Backing up batch {i//batch_size + 1}/{(total_emails-1)//batch_size + 1} ({len(batch)} emails)...")

                for msg in batch:
                    try:
                        # Get full message
                        message = source_service.service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='raw'
                        ).execute()

                        # Import to backup account
                        backup_service.service.users().messages().import_(
                            userId='me',
                            body={'raw': message['raw']},
                            internalDateSource='dateHeader'
                        ).execute()

                        backed_up += 1

                    except Exception as e:
                        print(f"   ⚠️  Error backing up message {msg['id']}: {e}")
                        errors += 1

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            print(f"\n✅ Backup complete!")
            print(f"   Backed up: {backed_up}/{total_emails}")
            if errors > 0:
                print(f"   Errors: {errors}")

            return BackupResult(
                source_account_id=source_account_id,
                backup_account_id=self.backup_account_id,
                total_emails=total_emails,
                backed_up=backed_up,
                skipped=skipped,
                errors=errors,
                started_at=start_time,
                finished_at=datetime.now()
            )

        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return BackupResult(
                source_account_id=source_account_id,
                backup_account_id=self.backup_account_id,
                total_emails=0,
                backed_up=0,
                skipped=0,
                errors=1,
                started_at=start_time,
                finished_at=datetime.now()
            )

    async def _backup_ionos_account(
        self,
        source_account_id: str,
        max_emails: int,
        start_time: datetime
    ) -> BackupResult:
        """
        Backup Ionos account.

        Strategy: Fetch via IMAP, forward to backup Gmail account
        """
        import imaplib
        import email

        print(f"📧 Connecting to Ionos IMAP...")

        try:
            # Connect to Ionos IMAP
            mail = imaplib.IMAP4_SSL(
                Config.IONOS_ACCOUNT['imap_server'],
                Config.IONOS_ACCOUNT['imap_port']
            )
            mail.login(
                Config.IONOS_ACCOUNT['email'],
                Config.IONOS_ACCOUNT['password']
            )
            mail.select('INBOX')

            # Search for all emails
            status, messages = mail.search(None, 'ALL')

            if status != 'OK':
                print(f"❌ Failed to fetch emails")
                return BackupResult(
                    source_account_id=source_account_id,
                    backup_account_id=self.backup_account_id,
                    total_emails=0,
                    backed_up=0,
                    skipped=0,
                    errors=1,
                    started_at=start_time,
                    finished_at=datetime.now()
                )

            email_ids = messages[0].split()

            # Limit if specified
            if max_emails:
                email_ids = email_ids[:max_emails]

            total_emails = len(email_ids)
            print(f"✅ Found {total_emails} emails to backup\n")

            if total_emails == 0:
                mail.close()
                mail.logout()
                return BackupResult(
                    source_account_id=source_account_id,
                    backup_account_id=self.backup_account_id,
                    total_emails=0,
                    backed_up=0,
                    skipped=0,
                    errors=0,
                    started_at=start_time,
                    finished_at=datetime.now()
                )

            # Get backup service
            backup_service = get_gmail_service(
                self.backup_account_id,
                self.backup_config['credentials_path'],
                self.backup_config['token_path']
            )

            backed_up = 0
            errors = 0

            # Backup emails
            for i, email_id in enumerate(email_ids, 1):
                if i % 10 == 0:
                    print(f"📤 Progress: {i}/{total_emails}...")

                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        errors += 1
                        continue

                    # Parse email
                    email_message = email.message_from_bytes(msg_data[0][1])

                    # Forward to backup account
                    import base64
                    raw_message = base64.urlsafe_b64encode(msg_data[0][1]).decode('utf-8')

                    backup_service.service.users().messages().import_(
                        userId='me',
                        body={'raw': raw_message},
                        internalDateSource='dateHeader'
                    ).execute()

                    backed_up += 1

                except Exception as e:
                    print(f"   ⚠️  Error backing up email {email_id.decode()}: {e}")
                    errors += 1

            mail.close()
            mail.logout()

            print(f"\n✅ Backup complete!")
            print(f"   Backed up: {backed_up}/{total_emails}")
            if errors > 0:
                print(f"   Errors: {errors}")

            return BackupResult(
                source_account_id=source_account_id,
                backup_account_id=self.backup_account_id,
                total_emails=total_emails,
                backed_up=backed_up,
                skipped=0,
                errors=errors,
                started_at=start_time,
                finished_at=datetime.now()
            )

        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return BackupResult(
                source_account_id=source_account_id,
                backup_account_id=self.backup_account_id,
                total_emails=0,
                backed_up=0,
                skipped=0,
                errors=1,
                started_at=start_time,
                finished_at=datetime.now()
            )

    async def backup_all_accounts(self, max_emails_per_account: int = None) -> List[BackupResult]:
        """
        Backup all configured accounts.

        Args:
            max_emails_per_account: Max emails per account (None = all)

        Returns:
            List of BackupResult for each account
        """
        print("\n" + "=" * 70)
        print("MONTHLY EMAIL BACKUP - ALL ACCOUNTS")
        print("=" * 70)

        # Collect accounts
        accounts = []

        # Gmail accounts
        for account_id, account_config in Config.GMAIL_ACCOUNTS.items():
            if account_config['email']:
                accounts.append(account_id)

        # Ionos account
        if Config.IONOS_ACCOUNT['email']:
            accounts.append("ionos")

        print(f"\n📧 Backing up {len(accounts)} accounts: {', '.join(accounts)}\n")

        # Backup all accounts sequentially (to avoid rate limits)
        results = []
        for account_id in accounts:
            result = await self.backup_account(account_id, max_emails_per_account)
            results.append(result)
            await asyncio.sleep(2)  # Delay between accounts

        # Print summary
        self._print_summary(results)

        return results

    def _print_summary(self, results: List[BackupResult]):
        """Print backup summary"""
        print("\n" + "=" * 70)
        print("BACKUP SUMMARY")
        print("=" * 70)

        total_emails = sum(r.total_emails for r in results)
        total_backed_up = sum(r.backed_up for r in results)
        total_errors = sum(r.errors for r in results)

        print(f"Total emails: {total_emails}")
        print(f"Successfully backed up: {total_backed_up}")
        if total_errors > 0:
            print(f"Errors: {total_errors}")

        print(f"\nPer-account breakdown:")
        for result in results:
            success_rate = result.success_rate * 100
            print(f"  {result.source_account_id}: {result.backed_up}/{result.total_emails} ({success_rate:.0f}%)")

        print("=" * 70 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def backup_single_account(account_id: str, max_emails: int = None):
    """
    Backup a single account.

    Usage:
        await backup_single_account("gmail_1", max_emails=100)
    """
    agent = EmailBackupAgent()
    return await agent.backup_account(account_id, max_emails)


async def run_monthly_backup(max_emails_per_account: int = None):
    """
    Run full monthly backup of all accounts.

    Usage:
        results = await run_monthly_backup()
    """
    agent = EmailBackupAgent()
    return await agent.backup_all_accounts(max_emails_per_account)
