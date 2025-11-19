"""
History-Based Importance Classification Layer

Learns from user behavior patterns stored in sender_preferences and
domain_preferences tables. NO LLM calls - pure database lookups.

High confidence when:
- Sender has >= 5 historical emails with clear patterns (confidence: 0.85)
- Domain has >= 10 historical emails with clear patterns (confidence: 0.75)

Uses metrics:
- Reply rate (% of emails replied to)
- Archive rate (% of emails archived without reply)
- Delete rate (% of emails deleted)
- Average time to reply (urgency indicator)
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from agent_platform.classification.models import (
    EmailToClassify,
    HistoryLayerResult,
    ImportanceCategory,
)
from agent_platform.db.models import SenderPreference, DomainPreference
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
        # STEP 1: Check sender-specific preferences (highest priority)
        # ====================================================================

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
                category="nice_to_know",
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
            category="nice_to_know",
            reasoning="No historical data available - first email from this sender/domain",
            data_source="default",
        )

    # ========================================================================
    # DATABASE QUERY METHODS
    # ========================================================================

    def _get_sender_preference(
        self, account_id: str, sender_email: str
    ) -> Optional[SenderPreference]:
        """Get sender preference from database."""
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

    def _classify_from_sender_preference(
        self, pref: SenderPreference, email: EmailToClassify
    ) -> HistoryLayerResult:
        """
        Classify based on sender-specific historical data.

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
                # Quick replies → action required
                return (
                    0.9,
                    "action_required",
                    f"{reply_rate:.0%} reply rate, avg {avg_time_to_reply:.1f}h response time"
                )
            else:
                # Regular replies → important
                return (
                    0.8,
                    "wichtig",
                    f"{reply_rate:.0%} reply rate (consistently responded to)"
                )

        # Medium reply rate → nice to know
        elif reply_rate >= self.MEDIUM_REPLY_RATE:
            return (
                0.5,
                "nice_to_know",
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

        # Low engagement overall → system notifications or low priority
        else:
            return (
                0.4,
                "system_notifications",
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
