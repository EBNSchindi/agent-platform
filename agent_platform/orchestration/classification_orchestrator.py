"""
Classification Orchestrator (Phase 2: Ensemble System)

Orchestrates the complete email classification workflow:
1. Fetch emails from account
2. Classify using EnsembleClassifier (All 3 layers parallel + weighted combination)
3. Route based on confidence:
   - High (≥0.90): Auto-action (label, archive)
   - Medium (0.65-0.90): Add to review queue
   - Low (<0.65): Mark for manual review
4. Save ProcessedEmail records
5. Return statistics

This integrates all components:
- EnsembleClassifier (Phase 2 - NEW)
- ExtractionAgent (Phase 1)
- ReviewQueueManager (Phase 1)

Legacy Support:
- Can optionally use LegacyClassifier (early-stopping) via use_legacy=True
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent_platform.db.models import ProcessedEmail
from agent_platform.db.database import get_db
from agent_platform.classification import (
    EnsembleClassifier,
    LegacyClassifier,
    EmailToClassify,
    ScoringWeights,
)
from agent_platform.extraction import ExtractionAgent
from agent_platform.review import ReviewQueueManager


class EmailProcessingStats(BaseModel):
    """Statistics for email processing"""
    account_id: str
    total_processed: int = 0

    # By confidence level
    high_confidence: int = 0      # ≥0.85
    medium_confidence: int = 0    # 0.6-0.85
    low_confidence: int = 0       # <0.6

    # By action
    auto_labeled: int = 0
    added_to_review: int = 0
    marked_manual: int = 0

    # By category
    by_category: Dict[str, int] = Field(default_factory=dict)

    # Extraction stats (NEW)
    emails_with_extractions: int = 0
    total_tasks_extracted: int = 0
    total_decisions_extracted: int = 0
    total_questions_extracted: int = 0

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class ClassificationOrchestrator:
    """
    Orchestrates the complete email classification workflow (Phase 2).

    Integrates:
    - EnsembleClassifier (All 3 layers parallel + weighted combination) - DEFAULT
    - LegacyClassifier (Early-stopping) - Optional for backwards compatibility
    - ReviewQueueManager (for medium-confidence items)
    - ProcessedEmail database tracking
    """

    # Confidence thresholds (Phase 2 - adjusted for ensemble system)
    HIGH_CONFIDENCE_THRESHOLD = 0.90  # Raised from 0.85 (ensemble provides higher confidence)
    MEDIUM_CONFIDENCE_THRESHOLD = 0.65  # Raised from 0.60 (better separation)

    def __init__(
        self,
        db: Optional[Session] = None,
        use_legacy: bool = False,
        ensemble_weights: Optional[ScoringWeights] = None,
        smart_llm_skip: bool = False,
        gmail_service: Optional[Any] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            db: Optional database session
            use_legacy: If True, use LegacyClassifier (early-stopping) instead of EnsembleClassifier
            ensemble_weights: Optional custom weights for ensemble scoring (ignored if use_legacy=True)
            smart_llm_skip: If True, enable Smart LLM skip optimization (~60-70% cost savings)
            gmail_service: Optional GmailService instance for Gmail API operations (Phase 2)
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        # Initialize classifier (Ensemble or Legacy)
        self.use_legacy = use_legacy

        if use_legacy:
            print("⚠️  Using LegacyClassifier (early-stopping architecture)")
            self.classifier = LegacyClassifier(db=self.db)
        else:
            print("✅ Using EnsembleClassifier (parallel layers + weighted combination)")
            self.classifier = EnsembleClassifier(
                db=self.db,
                weights=ensemble_weights,
                smart_llm_skip=smart_llm_skip
            )

        # Initialize other components
        self.extraction_agent = ExtractionAgent()
        self.queue_manager = ReviewQueueManager(db=self.db)
        self.gmail_service = gmail_service  # Phase 2: Gmail automation

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN PROCESSING METHOD
    # ========================================================================

    async def process_emails(
        self,
        emails: List[Dict[str, Any]],
        account_id: str,
    ) -> EmailProcessingStats:
        """
        Process a batch of emails through the classification workflow.

        Args:
            emails: List of email dictionaries with:
                - id: Email ID
                - subject: Email subject
                - sender: Sender email address
                - body: Email body text
                - received_at: When email was received (optional)
            account_id: Account ID (e.g., gmail_1)

        Returns:
            EmailProcessingStats with processing results
        """
        stats = EmailProcessingStats(account_id=account_id)

        print(f"\n{'=' * 70}")
        print(f"CLASSIFICATION ORCHESTRATOR: {account_id.upper()}")
        print(f"{'=' * 70}\n")
        print(f"📧 Processing {len(emails)} emails...")

        for email in emails:
            await self._process_single_email(email, account_id, stats)

        stats.finished_at = datetime.utcnow()

        self._print_stats(stats)

        return stats

    def _get_classification_attrs(self, classification):
        """
        Extract attributes from classification result.

        Supports both EnsembleClassification (final_*) and LegacyClassification (*).
        """
        category = getattr(classification, 'final_category', None) or classification.category
        importance = getattr(classification, 'final_importance', None) or classification.importance
        confidence = getattr(classification, 'final_confidence', None) or classification.confidence

        return category, importance, confidence

    async def _process_single_email(
        self,
        email: Dict[str, Any],
        account_id: str,
        stats: EmailProcessingStats,
    ):
        """Process a single email through the workflow."""
        email_id = email.get('id', 'unknown')
        subject = email.get('subject', 'No Subject')
        sender = email.get('sender', 'Unknown')
        body = email.get('body', '')
        snippet = email.get('snippet', body[:200] if body else '')
        received_at = email.get('received_at', datetime.utcnow())

        # Phase 2.4: Detect attachments (from Gmail payload or email metadata)
        has_attachments = email.get('has_attachments', False)
        attachment_count = email.get('attachment_count', 0)
        attachments_metadata = email.get('attachments_metadata', [])

        # Infer from Gmail 'parts' if not explicitly provided
        if not has_attachments and 'parts' in email:
            parts = email.get('parts', [])
            attachment_parts = [p for p in parts if p.get('filename')]
            if attachment_parts:
                has_attachments = True
                attachment_count = len(attachment_parts)
                attachments_metadata = [
                    {
                        'filename': p.get('filename'),
                        'size': p.get('size', 0),
                        'mime_type': p.get('mimeType', 'unknown')
                    }
                    for p in attachment_parts
                ]

        print(f"\n📬 {subject[:60]}")
        print(f"   From: {sender[:50]}")
        if has_attachments:
            print(f"   📎 Attachments: {attachment_count}")

        # Create EmailToClassify
        email_to_classify = EmailToClassify(
            email_id=email_id,
            account_id=account_id,
            sender=sender,
            subject=subject,
            body=body,
            received_at=received_at,
            has_attachments=has_attachments,  # Phase 2.4: Pass to classifier
        )

        # Step 1: Classify email
        print(f"   🔍 Classifying...")
        classification = await self.classifier.classify(email_to_classify)

        # Extract attributes (supports both Ensemble and Legacy)
        category, importance, confidence = self._get_classification_attrs(classification)

        # Phase 2.4: Priority boost for attachments (+10% importance if has attachments)
        if has_attachments and importance < 1.0:
            original_importance = importance
            importance = min(1.0, importance + 0.10)  # Boost by 10%, cap at 1.0
            print(f"   📎 Attachment boost: {original_importance:.0%} → {importance:.0%}")
        layer_used = getattr(classification, 'layer_used', 'ensemble')

        print(f"   📊 Category: {category}")
        print(f"   ⚖️  Importance: {importance:.0%}")
        print(f"   🎯 Confidence: {confidence:.0%}")
        print(f"   🏷️  Layer: {layer_used}")

        # Determine storage level (Datenhaltungs-Strategie)
        storage_level = self._determine_storage_level(category, importance, confidence)
        print(f"   💾 Storage Level: {storage_level}")

        # Update stats
        stats.total_processed += 1
        stats.by_category[category] = stats.by_category.get(category, 0) + 1

        # Route based on confidence
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            # HIGH CONFIDENCE: Auto-action
            stats.high_confidence += 1
            await self._handle_high_confidence(
                email, classification, category, account_id, stats
            )

        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            # MEDIUM CONFIDENCE: Review queue
            stats.medium_confidence += 1
            await self._handle_medium_confidence(
                email, classification, category, confidence, account_id, stats
            )

        else:
            # LOW CONFIDENCE: Manual review
            stats.low_confidence += 1
            await self._handle_low_confidence(
                email, classification, category, account_id, stats
            )

        # Save ProcessedEmail record FIRST (needed for FK linkage)
        # Add attachment metadata to email dict for _save_processed_email
        email_with_attachments = {
            **email,
            'has_attachments': has_attachments,
            'attachment_count': attachment_count,
            'attachments_metadata': attachments_metadata,
        }
        processed_email_id = self._save_processed_email(
            email_with_attachments, classification, account_id, storage_level, body
        )

        # Step 2: Extract information AND persist to Memory-Objects (conditional based on storage_level)
        if storage_level in ['full', 'summary']:
            print(f"   🔎 Extracting information...")
            extraction = await self.extraction_agent.extract_and_persist(
                email_to_classify,
                processed_email_id=processed_email_id,
                storage_level=storage_level
            )

            print(f"   📋 Extracted & Persisted: {extraction.task_count} tasks, "
                  f"{extraction.decision_count} decisions, "
                  f"{extraction.question_count} questions")

            # Update extraction stats
            if extraction.total_items > 0:
                stats.emails_with_extractions += 1
            stats.total_tasks_extracted += extraction.task_count
            stats.total_decisions_extracted += extraction.decision_count
            stats.total_questions_extracted += extraction.question_count
        else:
            # storage_level = 'minimal' → Skip extraction
            print(f"   ⏭️  Skipping extraction (minimal storage)")
            extraction = None

    # ========================================================================
    # CONFIDENCE-BASED ROUTING
    # ========================================================================

    async def _handle_high_confidence(
        self,
        email: Dict[str, Any],
        classification,
        category: str,
        account_id: str,
        stats: EmailProcessingStats,
    ):
        """
        Handle high-confidence classification (≥0.90).

        Phase 2 Enhancement: Actually applies Gmail labels with emojis and logs events.

        Args:
            email: Email dictionary
            classification: Classification result
            category: Email category
            account_id: Account ID (e.g., gmail_1)
            stats: Processing statistics
        """
        print(f"   ✅ HIGH CONFIDENCE → Auto-action")

        # Get emoji label for category
        label = self._get_label_for_category(category)
        print(f"   🏷️  Label: {label}")

        # Phase 2: Apply label via Gmail API (if gmail_service available)
        gmail_label_applied = None
        if self.gmail_service:
            try:
                result = self.gmail_service.apply_label(email['id'], label)
                if result.get('status') == 'success':
                    gmail_label_applied = label
                    print(f"   ✅ Label applied successfully")

                    # Log GMAIL_LABEL_APPLIED event
                    from agent_platform.events import log_event, EventType

                    log_event(
                        event_type=EventType.GMAIL_LABEL_APPLIED,
                        account_id=account_id,
                        email_id=email['id'],
                        payload={
                            'label_name': label,
                            'category': category,
                            'confidence': getattr(classification, 'final_confidence', getattr(classification, 'confidence', 0.0)),
                        },
                        extra_metadata={
                            'gmail_result': result,
                        }
                    )
                else:
                    print(f"   ⚠️  Failed to apply label: {result.get('message')}")
            except Exception as e:
                print(f"   ❌ Error applying label: {e}")

        # Phase 2.2: Auto-archive for newsletter/spam (Phase 2 Requirement)
        gmail_archived = False
        if self.gmail_service and category in ['newsletter', 'spam']:
            try:
                result = self.gmail_service.archive_email(email['id'])
                if result.get('status') == 'success':
                    gmail_archived = True
                    print(f"   📥 Email archived automatically ({category})")

                    # Log GMAIL_ARCHIVED event
                    from agent_platform.events import log_event, EventType

                    log_event(
                        event_type=EventType.GMAIL_ARCHIVED,
                        account_id=account_id,
                        email_id=email['id'],
                        payload={
                            'category': category,
                            'reason': f'Auto-archive for {category}',
                            'confidence': getattr(classification, 'final_confidence', getattr(classification, 'confidence', 0.0)),
                        },
                        extra_metadata={
                            'gmail_result': result,
                        }
                    )
                else:
                    print(f"   ⚠️  Failed to archive: {result.get('message')}")
            except Exception as e:
                print(f"   ❌ Error archiving email: {e}")

        # Phase 2.3: Auto-mark-as-read for low-priority emails (Phase 2 Requirement)
        gmail_marked_read = False
        if self.gmail_service and category in ['newsletter', 'spam', 'system_notifications']:
            try:
                result = self.gmail_service.mark_as_read(email['id'])
                if result.get('status') == 'success':
                    gmail_marked_read = True
                    print(f"   ✅ Email marked as read ({category})")

                    # Log GMAIL_MARKED_READ event
                    from agent_platform.events import log_event, EventType

                    log_event(
                        event_type=EventType.GMAIL_MARKED_READ,
                        account_id=account_id,
                        email_id=email['id'],
                        payload={
                            'category': category,
                            'reason': f'Auto-mark-read for {category}',
                            'confidence': getattr(classification, 'final_confidence', getattr(classification, 'confidence', 0.0)),
                        },
                        extra_metadata={
                            'gmail_result': result,
                        }
                    )
                else:
                    print(f"   ⚠️  Failed to mark as read: {result.get('message')}")
            except Exception as e:
                print(f"   ❌ Error marking as read: {e}")

        # Update ProcessedEmail record with Gmail action info
        if gmail_label_applied or gmail_archived or gmail_marked_read:
            try:
                from agent_platform.db.database import get_db
                from agent_platform.db.models import ProcessedEmail

                with get_db() as db:
                    processed_email = db.query(ProcessedEmail).filter(
                        ProcessedEmail.email_id == email['id'],
                        ProcessedEmail.account_id == account_id
                    ).order_by(ProcessedEmail.created_at.desc()).first()

                    if processed_email:
                        if gmail_label_applied:
                            processed_email.gmail_label_applied = gmail_label_applied
                        if gmail_archived:
                            processed_email.gmail_archived = True
                        if gmail_marked_read:
                            processed_email.gmail_marked_read = True
                        db.commit()
            except Exception as e:
                print(f"   ⚠️  Failed to update ProcessedEmail with Gmail actions: {e}")

        stats.auto_labeled += 1

    async def _handle_medium_confidence(
        self,
        email: Dict[str, Any],
        classification,
        category: str,
        confidence: float,
        account_id: str,
        stats: EmailProcessingStats,
    ):
        """Handle medium-confidence classification (0.6-0.85)."""
        print(f"   ⚠️  MEDIUM CONFIDENCE → Review queue")

        # Add to review queue
        self.queue_manager.add_to_queue(
            email_id=email.get('id'),
            account_id=account_id,
            subject=email.get('subject'),
            sender=email.get('sender'),
            snippet=email.get('snippet', email.get('body', '')[:200]),
            classification=classification,
        )

        print(f"   📋 Added to review queue")
        stats.added_to_review += 1

    async def _handle_low_confidence(
        self,
        email: Dict[str, Any],
        classification,
        category: str,
        account_id: str,
        stats: EmailProcessingStats,
    ):
        """Handle low-confidence classification (<0.6)."""
        print(f"   ⚠️  LOW CONFIDENCE → Manual review")

        # Mark for manual review
        # In practice, this would be flagged in the UI or sent to a special queue
        print(f"   🔍 Marked for manual review")
        stats.marked_manual += 1

    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================

    def _save_processed_email(
        self,
        email: Dict[str, Any],
        classification,
        account_id: str,
        storage_level: str,
        body: str,
    ) -> int:
        """
        Save ProcessedEmail record to database with storage_level logic.

        Args:
            email: Email dictionary
            classification: Classification result
            account_id: Account ID string
            storage_level: Storage level ('full', 'summary', 'minimal')
            body: Email body text

        Returns:
            processed_email.id (needed for FK linkage with memory objects)
        """
        # Determine account_id for database (integer foreign key)
        # For now, use a placeholder - in production, this would lookup the account ID
        # from email_accounts table
        db_account_id = 1  # Placeholder

        # Extract attributes (supports both Ensemble and Legacy)
        category, importance, confidence = self._get_classification_attrs(classification)
        layer_used = getattr(classification, 'layer_used', 'ensemble')

        # Get LLM provider (different for ensemble vs legacy)
        llm_provider = None
        if hasattr(classification, 'llm_score') and classification.llm_score:
            llm_provider = classification.llm_score.llm_provider
        elif hasattr(classification, 'llm_provider_used'):
            llm_provider = classification.llm_provider_used
        else:
            llm_provider = f"{layer_used}_only"

        # Conditional body storage based on storage_level
        body_text = body if storage_level == 'full' else None
        body_html = email.get('body_html') if storage_level == 'full' else None

        # Phase 2.4: Extract attachment metadata from email
        has_attachments = email.get('has_attachments', False)
        attachment_count = email.get('attachment_count', 0)
        attachments_metadata = email.get('attachments_metadata', {})

        processed_email = ProcessedEmail(
            account_id=db_account_id,
            email_id=email.get('id'),
            sender=email.get('sender'),
            subject=email.get('subject'),
            received_at=email.get('received_at', datetime.utcnow()),
            processed_at=datetime.utcnow(),
            category=category,
            importance_score=importance,
            classification_confidence=confidence,
            llm_provider_used=llm_provider,
            rule_layer_hint=getattr(classification, 'reasoning', None) if layer_used == "rules" else None,
            history_layer_hint=getattr(classification, 'reasoning', None) if layer_used == "history" else None,

            # Phase 1: Storage level and conditional body storage
            storage_level=storage_level,
            body_text=body_text,
            body_html=body_html,
            summary=None,  # Will be set by extraction agent

            # Phase 2.4: Attachment metadata
            has_attachments=has_attachments,
            attachment_count=attachment_count,
            attachments_metadata=attachments_metadata,

            extra_metadata={
                'layer_used': layer_used,
                'processing_time_ms': getattr(classification, 'processing_time_ms', 0),
                'reasoning': getattr(classification, 'reasoning', getattr(classification, 'combined_reasoning', '')),
                'low_confidence': confidence < self.MEDIUM_CONFIDENCE_THRESHOLD,
            }
        )

        self.db.add(processed_email)
        self.db.commit()
        self.db.refresh(processed_email)  # Get the generated ID

        return processed_email.id

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _determine_storage_level(self, category: str, importance: float, confidence: float) -> str:
        """
        Determine storage level based on classification (Datenhaltungs-Strategie).

        REQ-001: Standardized Email Storage
        All emails are now stored with 'full' storage level, regardless of category or importance.
        This ensures complete data availability for all emails (body + attachments + extractions).

        Args:
            category: Email category from classification (unused, kept for API compatibility)
            importance: Importance score (0.0-1.0) (unused, kept for API compatibility)
            confidence: Classification confidence (0.0-1.0) (unused, kept for API compatibility)

        Returns:
            Always returns 'full'
        """
        return 'full'

    def _get_label_for_category(self, category: str) -> str:
        """
        Map category to Gmail label with emoji.

        Phase 2 Enhancement: Uses emoji labels for better visual recognition.

        Args:
            category: Email category from classification

        Returns:
            Gmail label name with emoji prefix
        """
        label_map = {
            "wichtig": "🔴 Wichtig",
            "action_required": "⚡ Action Required",
            "nice_to_know": "📘 Nice to Know",
            "newsletter": "📰 Newsletter",
            "spam": "🗑️ Spam",
            "system_notifications": "🔔 System",
        }
        return label_map.get(category, "❓ Uncategorized")

    def _print_stats(self, stats: EmailProcessingStats):
        """Print processing statistics."""
        print(f"\n{'=' * 70}")
        print(f"PROCESSING SUMMARY: {stats.account_id.upper()}")
        print(f"{'=' * 70}")
        print(f"Total Processed: {stats.total_processed}")
        print(f"Duration: {stats.duration_seconds:.1f}s" if stats.duration_seconds else "Duration: N/A")

        print(f"\n📊 By Confidence Level:")
        print(f"   High (≥0.85):   {stats.high_confidence:>3} ({stats.high_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   High (≥0.85):     0")
        print(f"   Medium (0.6-0.85): {stats.medium_confidence:>3} ({stats.medium_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   Medium (0.6-0.85):  0")
        print(f"   Low (<0.6):     {stats.low_confidence:>3} ({stats.low_confidence/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   Low (<0.6):      0")

        print(f"\n🎬 Actions Taken:")
        print(f"   Auto-labeled:     {stats.auto_labeled:>3}")
        print(f"   Review queue:     {stats.added_to_review:>3}")
        print(f"   Manual review:    {stats.marked_manual:>3}")

        if stats.by_category:
            print(f"\n📁 By Category:")
            for category, count in sorted(
                stats.by_category.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"   {category:20s}: {count:>3}")

        # Extraction statistics (NEW)
        print(f"\n📋 Extraction Results:")
        print(f"   Emails with items: {stats.emails_with_extractions:>3} ({stats.emails_with_extractions/stats.total_processed*100:.0f}%)" if stats.total_processed > 0 else "   Emails with items:   0")
        print(f"   Tasks extracted:   {stats.total_tasks_extracted:>3}")
        print(f"   Decisions extracted: {stats.total_decisions_extracted:>3}")
        print(f"   Questions extracted: {stats.total_questions_extracted:>3}")
        print(f"   Total items:       {stats.total_tasks_extracted + stats.total_decisions_extracted + stats.total_questions_extracted:>3}")

        print(f"{'=' * 70}\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def process_account_emails(
    emails: List[Dict[str, Any]],
    account_id: str,
) -> EmailProcessingStats:
    """
    Convenience function to process emails for an account.

    Usage:
        emails = [
            {
                'id': 'msg_123',
                'subject': 'Meeting Tomorrow',
                'sender': 'boss@company.com',
                'body': 'Can we meet at 10am?',
                'received_at': datetime.utcnow(),
            },
            ...
        ]

        stats = await process_account_emails(emails, 'gmail_1')

    Args:
        emails: List of email dictionaries
        account_id: Account ID

    Returns:
        EmailProcessingStats
    """
    orchestrator = ClassificationOrchestrator()
    return await orchestrator.process_emails(emails, account_id)
