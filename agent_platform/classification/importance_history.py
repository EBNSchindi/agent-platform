"""
History-Based Importance Classification Layer

Learns from BIDIRECTIONAL user behavior patterns stored in contact_preferences table.
NO LLM calls - pure database lookups.

Key Improvements (Bidirectional Tracking):
- Tracks BOTH incoming (received) and outgoing (sent) emails
- Uses contact_importance (weighted: 40% outgoing, 30% reply, 20% initiation, 10% incoming)
- Considers relationship_type (proactive, reactive, bidirectional, one_way_*)

High confidence when:
- Contact has >= 5 total exchanged emails with clear patterns (confidence: 0.85)
- Domain has >= 10 historical emails with clear patterns (confidence: 0.75)

Uses bidirectional metrics:
- Reply rate (% of their emails I reply to)
- Initiation rate (% of emails where I start conversation)
- Sent reply rate (% of my emails they reply to)
- Contact importance (weighted combination)
- Relationship type (proactive/reactive/bidirectional/one_way)
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from agent_platform.classification.models import (
    EmailToClassify,
    HistoryLayerResult,
    ImportanceCategory,
)
from agent_platform.db.models import ContactPreference, SenderPreference, DomainPreference
from agent_platform.db.database import get_db


class HistoryLayer:
    """
    History-based classification layer - learns from user behavior.

    Queries sender_preferences and domain_preferences tables to find
    patterns in how the user has historically handled emails from this
    sender/domain.
    """

    # Confidence thresholds
    MIN_EMAILS_HIGH_CONFIDENCE_SENDER = 5   # Need 5+ emails for high confidence
    MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN = 10  # Need 10+ domain emails

    SENDER_BASE_CONFIDENCE = 0.85  # Higher confidence for sender-specific data
    DOMAIN_BASE_CONFIDENCE = 0.75  # Lower confidence for domain-level data

    # Reply rate thresholds for importance
    HIGH_REPLY_RATE = 0.7   # >= 70% reply rate → wichtig/action_required
    MEDIUM_REPLY_RATE = 0.3  # 30-70% reply rate → nice_to_know
    # < 30% reply rate → newsletter/system_notifications

    # Archive rate thresholds
    HIGH_ARCHIVE_RATE = 0.8  # >= 80% archived → low importance

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize history layer.

        Args:
            db: Optional database session (will create one if not provided)
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN CLASSIFICATION METHOD
    # ========================================================================

    def classify(
        self,
        email: EmailToClassify,
        account_id: Optional[str] = None
    ) -> HistoryLayerResult:
        """
        Classify email based on historical user behavior.

        Checks sender preferences first, then domain preferences if no
        sender data available.

        Args:
            email: Email to classify
            account_id: Account ID (defaults to email.account_id)

        Returns:
            HistoryLayerResult with classification based on historical data
        """
        account_id = account_id or email.account_id
        sender_email = email.sender.lower()
        sender_domain = self._extract_domain(sender_email)

        # ====================================================================
        # STEP 1: Check contact preferences (bidirectional - highest priority)
        # ====================================================================

        contact_pref = self._get_contact_preference(account_id, sender_email)

        if contact_pref and contact_pref.total_emails_exchanged >= self.MIN_EMAILS_HIGH_CONFIDENCE_SENDER:
            # We have enough bidirectional data for high confidence
            return self._classify_from_contact_preference(contact_pref, email)

        # FALLBACK: Try legacy SenderPreference (for backwards compatibility)
        sender_pref = self._get_sender_preference(account_id, sender_email)

        if sender_pref and sender_pref.total_emails_received >= self.MIN_EMAILS_HIGH_CONFIDENCE_SENDER:
            # We have enough sender-specific data for high confidence
            return self._classify_from_sender_preference(sender_pref, email)

        # ====================================================================
        # STEP 2: Check domain-level preferences (fallback)
        # ====================================================================

        domain_pref = self._get_domain_preference(account_id, sender_domain)

        if domain_pref and domain_pref.total_emails_received >= self.MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN:
            # We have enough domain data for moderate confidence
            return self._classify_from_domain_preference(domain_pref, email)

        # ====================================================================
        # STEP 3: Insufficient historical data - low confidence
        # ====================================================================

        # Some historical data exists but not enough for high confidence
        if sender_pref or domain_pref:
            pref = sender_pref or domain_pref
            data_source = "sender" if sender_pref else "domain"

            return HistoryLayerResult(
                sender_email=sender_email,
                sender_domain=sender_domain,
                sender_preference_found=bool(sender_pref),
                domain_preference_found=bool(domain_pref),
                historical_reply_rate=pref.reply_rate if pref else None,
                historical_archive_rate=pref.archive_rate if pref else None,
                total_historical_emails=pref.total_emails_received if pref else 0,
                importance=0.5,  # Neutral importance
                confidence=0.4,  # Low-medium confidence (not enough data)
                category="newsletter",  # Neutral fallback
                reasoning=f"Insufficient historical data ({pref.total_emails_received if pref else 0} emails) for confident classification",
                data_source=data_source,
            )

        # No historical data at all
        return HistoryLayerResult(
            sender_email=sender_email,
            sender_domain=sender_domain,
            sender_preference_found=False,
            domain_preference_found=False,
            historical_reply_rate=None,
            historical_archive_rate=None,
            total_historical_emails=0,
            importance=0.5,  # Neutral
            confidence=0.2,  # Very low confidence - needs LLM layer
            category="newsletter",  # Neutral fallback
            reasoning="No historical data available - first email from this sender/domain",
            data_source="default",
        )

    # ========================================================================
    # DATABASE QUERY METHODS
    # ========================================================================

    def _get_contact_preference(
        self, account_id: str, contact_email: str
    ) -> Optional[ContactPreference]:
        """Get contact preference (bidirectional) from database."""
        if not self.db:
            return None

        try:
            return (
                self.db.query(ContactPreference)
                .filter(
                    ContactPreference.account_id == account_id,
                    ContactPreference.contact_email == contact_email
                )
                .first()
            )
        except Exception as e:
            print(f"⚠️  Error querying contact preference: {e}")
            return None

    def _get_sender_preference(
        self, account_id: str, sender_email: str
    ) -> Optional[SenderPreference]:
        """Get sender preference from database (legacy fallback)."""
        if not self.db:
            return None

        try:
            return (
                self.db.query(SenderPreference)
                .filter(
                    SenderPreference.account_id == account_id,
                    SenderPreference.sender_email == sender_email
                )
                .first()
            )
        except Exception as e:
            print(f"⚠️  Error querying sender preference: {e}")
            return None

    def _get_domain_preference(
        self, account_id: str, domain: str
    ) -> Optional[DomainPreference]:
        """Get domain preference from database."""
        if not self.db:
            return None

        try:
            return (
                self.db.query(DomainPreference)
                .filter(
                    DomainPreference.account_id == account_id,
                    DomainPreference.domain == domain
                )
                .first()
            )
        except Exception as e:
            print(f"⚠️  Error querying domain preference: {e}")
            return None

    # ========================================================================
    # CLASSIFICATION FROM PREFERENCES
    # ========================================================================

    def _classify_from_contact_preference(
        self, pref: ContactPreference, email: EmailToClassify
    ) -> HistoryLayerResult:
        """
        Classify based on BIDIRECTIONAL contact history.

        Uses both incoming and outgoing email patterns for higher accuracy.
        Considers:
        - Contact importance (weighted: 40% outgoing, 30% reply, 20% initiation, 10% incoming)
        - Relationship type (proactive, reactive, bidirectional, one_way_*)
        - Reply patterns (both directions)
        """
        # Use contact_importance directly (already calculated with bidirectional weights)
        importance = pref.contact_importance

        # Boost importance for proactive/bidirectional relationships
        relationship_boost = {
            "proactive": 0.1,       # I initiate a lot → important contact
            "bidirectional": 0.05,  # Active communication → moderately important
            "reactive": 0.0,        # I only reply → use base importance
            "one_way_incoming": -0.1,  # They spam, I don't reply → less important
            "one_way_outgoing": 0.0,   # I reach out, they don't reply → neutral
        }
        importance += relationship_boost.get(pref.relationship_type, 0.0)
        importance = max(0.0, min(1.0, importance))  # Clamp to [0, 1]

        # Map importance to category
        category, category_reasoning = self._map_importance_to_category(
            importance=importance,
            reply_rate=pref.reply_rate,
            relationship_type=pref.relationship_type,
        )

        # High confidence for bidirectional data
        confidence = self._calculate_confidence(
            total_emails=pref.total_emails_exchanged,
            base_confidence=self.SENDER_BASE_CONFIDENCE,
            is_sender_level=True,
        )

        # Build reasoning string
        reasoning_parts = [
            f"{pref.total_emails_exchanged} exchanged",
            f"{pref.total_emails_received} received, {pref.total_emails_sent} sent",
            f"{pref.relationship_type} relationship",
            category_reasoning,
        ]

        return HistoryLayerResult(
            sender_email=pref.contact_email,
            sender_domain=pref.contact_domain,
            sender_preference_found=True,  # Using contact pref
            domain_preference_found=False,
            historical_reply_rate=pref.reply_rate,
            historical_archive_rate=0.0,  # Not tracked in ContactPreference
            total_historical_emails=pref.total_emails_exchanged,
            importance=importance,
            confidence=confidence,
            category=category,
            reasoning=f"Bidirectional history: {', '.join(reasoning_parts)}",
            data_source="contact",  # New data source type
        )

    def _classify_from_sender_preference(
        self, pref: SenderPreference, email: EmailToClassify
    ) -> HistoryLayerResult:
        """
        Classify based on sender-specific historical data (LEGACY fallback).

        High confidence classification based on reply/archive patterns.
        """
        # Calculate importance from behavioral patterns
        importance, category, reasoning = self._calculate_importance_from_behavior(
            reply_rate=pref.reply_rate,
            archive_rate=pref.archive_rate,
            delete_rate=pref.delete_rate,
            avg_time_to_reply=pref.avg_time_to_reply_hours,
        )

        # Confidence based on amount of historical data
        confidence = self._calculate_confidence(
            total_emails=pref.total_emails_received,
            base_confidence=self.SENDER_BASE_CONFIDENCE,
            is_sender_level=True,
        )

        return HistoryLayerResult(
            sender_email=pref.sender_email,
            sender_domain=pref.sender_domain,
            sender_preference_found=True,
            domain_preference_found=False,
            historical_reply_rate=pref.reply_rate,
            historical_archive_rate=pref.archive_rate,
            total_historical_emails=pref.total_emails_received,
            importance=importance,
            confidence=confidence,
            category=category,
            reasoning=f"Sender history ({pref.total_emails_received} emails): {reasoning}",
            data_source="sender",
        )

    def _classify_from_domain_preference(
        self, pref: DomainPreference, email: EmailToClassify
    ) -> HistoryLayerResult:
        """
        Classify based on domain-level historical data.

        Moderate confidence classification (less specific than sender-level).
        """
        # Calculate importance from domain patterns
        importance, category, reasoning = self._calculate_importance_from_behavior(
            reply_rate=pref.reply_rate,
            archive_rate=pref.archive_rate,
            delete_rate=0.0,  # Domain-level doesn't track delete rate
            avg_time_to_reply=None,
        )

        # Lower confidence for domain-level data
        confidence = self._calculate_confidence(
            total_emails=pref.total_emails_received,
            base_confidence=self.DOMAIN_BASE_CONFIDENCE,
            is_sender_level=False,
        )

        sender_domain = self._extract_domain(email.sender)

        return HistoryLayerResult(
            sender_email=email.sender,
            sender_domain=sender_domain,
            sender_preference_found=False,
            domain_preference_found=True,
            historical_reply_rate=pref.reply_rate,
            historical_archive_rate=pref.archive_rate,
            total_historical_emails=pref.total_emails_received,
            importance=importance,
            confidence=confidence,
            category=category,
            reasoning=f"Domain history ({pref.total_emails_received} emails): {reasoning}",
            data_source="domain",
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _calculate_importance_from_behavior(
        self,
        reply_rate: float,
        archive_rate: float,
        delete_rate: float,
        avg_time_to_reply: Optional[float],
    ) -> Tuple[float, ImportanceCategory, str]:
        """
        Calculate importance score and category from behavioral metrics.

        Returns:
            (importance_score, category, reasoning)
        """
        # High reply rate → important emails
        if reply_rate >= self.HIGH_REPLY_RATE:
            # Very responsive to this sender
            if avg_time_to_reply and avg_time_to_reply < 2.0:  # < 2 hours
                # Quick replies → wichtig_todo (important with action)
                return (
                    0.9,
                    "wichtig_todo",
                    f"{reply_rate:.0%} reply rate, avg {avg_time_to_reply:.1f}h response time"
                )
            else:
                # Regular replies → important
                return (
                    0.8,
                    "wichtig_todo",
                    f"{reply_rate:.0%} reply rate (consistently responded to)"
                )

        # Medium reply rate → persoenlich (personal/occasional communication)
        elif reply_rate >= self.MEDIUM_REPLY_RATE:
            return (
                0.5,
                "persoenlich",  # Personal communication category
                f"{reply_rate:.0%} reply rate (occasionally responded to)"
            )

        # Low reply rate + high archive rate → newsletters/automated
        elif archive_rate >= self.HIGH_ARCHIVE_RATE:
            return (
                0.3,
                "newsletter",
                f"{archive_rate:.0%} archived without reply (likely newsletters)"
            )

        # Low reply rate + high delete rate → spam or unwanted
        elif delete_rate > 0.5:
            return (
                0.1,
                "spam",
                f"{delete_rate:.0%} deleted (likely unwanted)"
            )

        # Low engagement overall → newsletter or low priority
        else:
            return (
                0.4,
                "newsletter",
                f"Low engagement ({reply_rate:.0%} reply, {archive_rate:.0%} archive)"
            )

    def _calculate_confidence(
        self, total_emails: int, base_confidence: float, is_sender_level: bool
    ) -> float:
        """
        Calculate confidence based on amount of historical data.

        More emails → higher confidence (up to base_confidence).
        """
        min_threshold = (
            self.MIN_EMAILS_HIGH_CONFIDENCE_SENDER
            if is_sender_level
            else self.MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN
        )

        if total_emails < min_threshold:
            # Not enough data → scale confidence down
            return base_confidence * (total_emails / min_threshold) * 0.7

        # Enough data → full confidence (but cap at base_confidence)
        # Add slight bonus for more data (up to +0.1)
        bonus = min(0.1, (total_emails - min_threshold) / 50 * 0.1)
        return min(1.0, base_confidence + bonus)

    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if "@" in email:
            return email.split("@")[1].lower()
        return email.lower()

    def _map_importance_to_category(
        self,
        importance: float,
        reply_rate: float,
        relationship_type: str,
    ) -> Tuple[ImportanceCategory, str]:
        """
        Map importance score to category based on bidirectional metrics.

        Args:
            importance: Contact importance score (0.0-1.0)
            reply_rate: Reply rate (0.0-1.0)
            relationship_type: Relationship type (proactive, reactive, etc.)

        Returns:
            (category, reasoning)
        """
        # Very high importance (>=0.8) → wichtig_todo
        if importance >= 0.8:
            if relationship_type == "proactive":
                return "wichtig_todo", "high importance, I initiate frequently"
            elif reply_rate > 0.7:
                return "wichtig_todo", "high importance, very responsive"
            else:
                return "job_projekte", "high importance, work-related contact"

        # High importance (0.6-0.8) → job_projekte or persoenlich
        elif importance >= 0.6:
            if relationship_type in ["proactive", "bidirectional"]:
                return "job_projekte", "regular active communication"
            else:
                return "persoenlich", "moderate importance, personal contact"

        # Medium importance (0.4-0.6) → persoenlich
        elif importance >= 0.4:
            return "persoenlich", "moderate importance, occasional communication"

        # Low importance (0.2-0.4) → newsletter
        elif importance >= 0.2:
            if relationship_type == "one_way_incoming":
                return "newsletter", "low importance, one-way communication"
            else:
                return "newsletter", "low importance, infrequent contact"

        # Very low importance (<0.2) → newsletter or spam
        else:
            if relationship_type == "one_way_incoming" and reply_rate < 0.1:
                return "spam", "very low importance, never replied"
            else:
                return "newsletter", "very low importance"
