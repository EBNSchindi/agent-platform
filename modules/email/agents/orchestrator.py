"""
Email Orchestrator
Main workflow coordinator for email processing across all accounts.
Handles Draft, Auto-Reply, and Manual modes.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from agent_platform.core.config import Config, Mode
from agent_platform.core.registry import get_registry
from modules.email.tools.gmail_tools import (
    fetch_unread_emails_tool,
    create_draft_tool,
    apply_label_tool,
    archive_email_tool,
    get_gmail_service
)
from modules.email.tools.ionos_tools import (
    fetch_ionos_emails,
    create_ionos_draft,
    archive_ionos_email
)
from modules.email.agents.classifier import classify_emails_batch, EmailClassification
from modules.email.agents.responder import generate_response, EmailResponse


# ============================================================================
# STRUCTURED OUTPUTS
# ============================================================================

class EmailProcessingResult(BaseModel):
    """Result of processing a single email"""
    email_id: str
    account_id: str
    subject: str
    sender: str

    # Classification
    category: str
    confidence: float
    should_reply: bool

    # Actions taken
    action: str  # "draft_created", "auto_replied", "labeled_only", "skipped"
    label_applied: Optional[str] = None
    draft_id: Optional[str] = None

    # Timestamps
    processed_at: datetime = Field(default_factory=datetime.now)

    # Metadata
    mode_used: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccountProcessingResult(BaseModel):
    """Result of processing an entire account"""
    account_id: str
    account_type: str  # gmail or ionos
    mode: str

    total_emails: int
    processed: int

    # Breakdown by action
    drafts_created: int = 0
    auto_replied: int = 0
    labeled_only: int = 0
    spam_filtered: int = 0
    skipped: int = 0
    errors: int = 0

    results: List[EmailProcessingResult] = Field(default_factory=list)

    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


# ============================================================================
# EMAIL ORCHESTRATOR
# ============================================================================

class EmailOrchestrator:
    """
    Main orchestrator for email processing.
    Coordinates classification, response generation, and actions based on mode.
    """

    def __init__(self):
        self.registry = get_registry()
        self.classifier = self.registry.get_agent("email.classifier")
        self.responder = self.registry.get_agent("email.responder")

        if not self.classifier:
            raise RuntimeError("Classifier agent not found. Did you register the email module?")
        if not self.responder:
            raise RuntimeError("Responder agent not found. Did you register the email module?")

    async def process_account(
        self,
        account_id: str,
        max_emails: int = 10,
        mode: Optional[Mode] = None
    ) -> AccountProcessingResult:
        """
        Process emails for a single account.

        Args:
            account_id: Account identifier (gmail_1, gmail_2, gmail_3, ionos)
            max_emails: Maximum number of emails to process
            mode: Override default mode for this account

        Returns:
            AccountProcessingResult with processing summary
        """
        start_time = datetime.now()

        # Determine mode
        if mode is None:
            mode = Config.get_account_mode(account_id)

        # Determine account type
        account_type = "ionos" if account_id == "ionos" else "gmail"

        print(f"\n{'=' * 70}")
        print(f"Processing Account: {account_id.upper()}")
        print(f"Mode: {mode.value.upper()}")
        print(f"{'=' * 70}\n")

        # Fetch emails
        emails = await self._fetch_emails(account_id, account_type, max_emails)

        if not emails:
            print(f"📭 No unread emails in {account_id}")
            return AccountProcessingResult(
                account_id=account_id,
                account_type=account_type,
                mode=mode.value,
                total_emails=0,
                processed=0,
                finished_at=datetime.now()
            )

        print(f"📧 Found {len(emails)} unread emails")

        # Classify emails
        print(f"🔍 Classifying emails...\n")
        classifications = await classify_emails_batch(emails, self.classifier)

        # Process each email based on mode
        results = []
        stats = {
            'drafts_created': 0,
            'auto_replied': 0,
            'labeled_only': 0,
            'spam_filtered': 0,
            'skipped': 0,
            'errors': 0
        }

        for email, classification in zip(emails, classifications):
            try:
                result = await self._process_single_email(
                    email=email,
                    classification=classification,
                    account_id=account_id,
                    account_type=account_type,
                    mode=mode
                )
                results.append(result)

                # Update stats
                if result.action == "draft_created":
                    stats['drafts_created'] += 1
                elif result.action == "auto_replied":
                    stats['auto_replied'] += 1
                elif result.action == "labeled_only":
                    stats['labeled_only'] += 1
                elif result.action == "spam_filtered":
                    stats['spam_filtered'] += 1
                elif result.action == "skipped":
                    stats['skipped'] += 1

            except Exception as e:
                print(f"❌ Error processing email {email.get('id', 'unknown')}: {e}")
                stats['errors'] += 1

        # Create result summary
        account_result = AccountProcessingResult(
            account_id=account_id,
            account_type=account_type,
            mode=mode.value,
            total_emails=len(emails),
            processed=len(results),
            drafts_created=stats['drafts_created'],
            auto_replied=stats['auto_replied'],
            labeled_only=stats['labeled_only'],
            spam_filtered=stats['spam_filtered'],
            skipped=stats['skipped'],
            errors=stats['errors'],
            results=results,
            started_at=start_time,
            finished_at=datetime.now()
        )

        self._print_account_summary(account_result)

        return account_result

    async def _fetch_emails(
        self,
        account_id: str,
        account_type: str,
        max_emails: int
    ) -> List[Dict]:
        """Fetch emails from account"""
        if account_type == "ionos":
            return fetch_ionos_emails(max_emails)
        else:
            return fetch_unread_emails_tool(account_id, max_emails)

    async def _process_single_email(
        self,
        email: Dict,
        classification: EmailClassification,
        account_id: str,
        account_type: str,
        mode: Mode
    ) -> EmailProcessingResult:
        """Process a single email based on classification and mode"""

        email_id = email.get('id', 'unknown')
        subject = email.get('subject', 'No Subject')[:60]
        sender = email.get('sender', 'Unknown')[:50]

        print(f"📬 {subject}")
        print(f"   From: {sender}")
        print(f"   Category: {classification.category} ({classification.confidence:.0%})")

        # Initialize result
        result = EmailProcessingResult(
            email_id=email_id,
            account_id=account_id,
            subject=subject,
            sender=sender,
            category=classification.category,
            confidence=classification.confidence,
            should_reply=classification.should_reply,
            mode_used=mode.value,
            action="skipped"
        )

        # SPAM: Always filter regardless of mode
        if classification.category == "spam":
            print(f"   🗑️  Spam detected - filtering")

            if account_type == "gmail":
                apply_label_tool(account_id, email_id, "Spam")
                archive_email_tool(account_id, email_id)
            else:
                archive_ionos_email(email_id)

            result.action = "spam_filtered"
            result.label_applied = "Spam"
            print()
            return result

        # Apply suggested label
        if classification.suggested_label:
            if account_type == "gmail":
                apply_label_tool(account_id, email_id, classification.suggested_label)
            result.label_applied = classification.suggested_label

        # MODE-SPECIFIC PROCESSING

        # MANUAL MODE: Only label, no drafts
        if mode == Mode.MANUAL:
            print(f"   🏷️  Manual mode - labeled only")
            result.action = "labeled_only"
            print()
            return result

        # Check if should generate response
        if not classification.should_reply:
            print(f"   ⏭️  No reply needed")
            result.action = "labeled_only"
            print()
            return result

        # Generate response
        print(f"   ✍️  Generating response...")
        response = await generate_response(
            email=email,
            classification=classification.__dict__
        )

        print(f"   📝 Response generated (tone: {response.tone}, confidence: {response.confidence_score:.0%})")

        # DRAFT MODE: Always create draft
        if mode == Mode.DRAFT:
            print(f"   💾 Creating draft...")

            if account_type == "gmail":
                draft_result = create_draft_tool(
                    account_id=account_id,
                    to=sender,
                    subject=response.subject,
                    body=response.body
                )
            else:
                draft_result = create_ionos_draft(
                    to=sender,
                    subject=response.subject,
                    body=response.body
                )

            if draft_result['status'] == 'success':
                print(f"   ✅ Draft created")
                result.action = "draft_created"
                result.draft_id = draft_result.get('draft_id')
            else:
                print(f"   ❌ Draft creation failed: {draft_result.get('message')}")
                result.action = "skipped"

            print()
            return result

        # AUTO-REPLY MODE: Send if high confidence, otherwise draft
        if mode == Mode.AUTO_REPLY:
            threshold = Config.RESPONDER_CONFIDENCE_THRESHOLD

            if response.confidence_score >= threshold and not response.requires_review:
                print(f"   📤 Auto-replying (high confidence)...")

                if account_type == "gmail":
                    service = get_gmail_service(
                        account_id,
                        Config.GMAIL_ACCOUNTS[account_id]['credentials_path'],
                        Config.GMAIL_ACCOUNTS[account_id]['token_path']
                    )
                    send_result = service.send_email(
                        to=sender,
                        subject=response.subject,
                        body=response.body
                    )
                else:
                    from modules.email.tools.ionos_tools import send_ionos_email
                    send_result = send_ionos_email(
                        to=sender,
                        subject=response.subject,
                        body=response.body
                    )

                if send_result['status'] == 'success':
                    print(f"   ✅ Reply sent")
                    result.action = "auto_replied"
                else:
                    print(f"   ❌ Send failed: {send_result.get('message')}")
                    result.action = "skipped"
            else:
                print(f"   💾 Confidence too low ({response.confidence_score:.0%}) - creating draft instead")

                if account_type == "gmail":
                    draft_result = create_draft_tool(
                        account_id=account_id,
                        to=sender,
                        subject=response.subject,
                        body=response.body
                    )
                else:
                    draft_result = create_ionos_draft(
                        to=sender,
                        subject=response.subject,
                        body=response.body
                    )

                if draft_result['status'] == 'success':
                    print(f"   ✅ Draft created for review")
                    result.action = "draft_created"
                    result.draft_id = draft_result.get('draft_id')
                else:
                    print(f"   ❌ Draft creation failed")
                    result.action = "skipped"

            print()
            return result

        print()
        return result

    def _print_account_summary(self, result: AccountProcessingResult):
        """Print summary for account processing"""
        print(f"\n{'=' * 70}")
        print(f"SUMMARY: {result.account_id.upper()}")
        print(f"{'=' * 70}")
        print(f"Mode: {result.mode.upper()}")
        print(f"Total emails: {result.total_emails}")
        print(f"Processed: {result.processed}")
        print(f"Duration: {result.duration_seconds:.1f}s" if result.duration_seconds else "Duration: N/A")
        print()
        print(f"Actions:")
        print(f"  📝 Drafts created: {result.drafts_created}")
        print(f"  📤 Auto-replied: {result.auto_replied}")
        print(f"  🏷️  Labeled only: {result.labeled_only}")
        print(f"  🗑️  Spam filtered: {result.spam_filtered}")
        print(f"  ⏭️  Skipped: {result.skipped}")
        if result.errors > 0:
            print(f"  ❌ Errors: {result.errors}")
        print()

    async def process_all_accounts(
        self,
        max_emails_per_account: int = 10
    ) -> List[AccountProcessingResult]:
        """
        Process all configured accounts in parallel.

        Args:
            max_emails_per_account: Max emails to process per account

        Returns:
            List of AccountProcessingResult for all accounts
        """
        print("\n" + "=" * 70)
        print("MULTI-ACCOUNT EMAIL PROCESSING")
        print("=" * 70)

        # Collect all configured accounts
        accounts = []

        # Gmail accounts
        for account_id, account_config in Config.GMAIL_ACCOUNTS.items():
            if account_config['email']:  # Only if configured
                accounts.append((account_id, "gmail"))

        # Ionos account
        if Config.IONOS_ACCOUNT['email']:
            accounts.append(("ionos", "ionos"))

        print(f"\n📧 Found {len(accounts)} configured accounts")
        print(f"   Accounts: {', '.join(acc[0] for acc in accounts)}")

        # Process all accounts in parallel
        tasks = [
            self.process_account(account_id, max_emails_per_account)
            for account_id, _ in accounts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, AccountProcessingResult)]

        # Print overall summary
        self._print_overall_summary(valid_results)

        return valid_results

    def _print_overall_summary(self, results: List[AccountProcessingResult]):
        """Print overall summary across all accounts"""
        print("\n" + "=" * 70)
        print("OVERALL SUMMARY")
        print("=" * 70)

        total_emails = sum(r.total_emails for r in results)
        total_drafts = sum(r.drafts_created for r in results)
        total_auto_replied = sum(r.auto_replied for r in results)
        total_spam = sum(r.spam_filtered for r in results)

        print(f"Total emails processed: {total_emails}")
        print(f"  📝 Drafts created: {total_drafts}")
        print(f"  📤 Auto-replied: {total_auto_replied}")
        print(f"  🗑️  Spam filtered: {total_spam}")
        print()

        print("Per-account breakdown:")
        for result in results:
            print(f"  {result.account_id}: {result.total_emails} emails, {result.drafts_created} drafts, {result.spam_filtered} spam")

        print("=" * 70 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def process_inbox(account_id: str, max_emails: int = 10, mode: Optional[Mode] = None):
    """
    Convenience function to process a single account's inbox.

    Usage:
        await process_inbox("gmail_1", max_emails=5, mode=Mode.DRAFT)
    """
    orchestrator = EmailOrchestrator()
    return await orchestrator.process_account(account_id, max_emails, mode)


async def process_all_inboxes(max_emails_per_account: int = 10):
    """
    Convenience function to process all accounts.

    Usage:
        results = await process_all_inboxes(max_emails_per_account=10)
    """
    orchestrator = EmailOrchestrator()
    return await orchestrator.process_all_accounts(max_emails_per_account)
