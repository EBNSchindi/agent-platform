"""
Sender Profile Service (Phase 8)

Manages sender profiles with:
- Whitelist/Blacklist management
- Trust levels (trusted, neutral, suspicious, blocked)
- Category preferences (allowed/muted categories per sender)
- Preference application during classification

Usage:
    from agent_platform.senders import SenderProfileService

    service = SenderProfileService()

    # Whitelist sender
    await service.whitelist_sender("boss@company.com", account_id="gmail_1")

    # Mute marketing from Amazon
    await service.mute_categories("shop@amazon.de", ["werbung", "newsletter"], "gmail_1")

    # Apply preferences during classification
    result = await service.apply_preferences(email, classification_result)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from agent_platform.db.database import get_db
from agent_platform.db.models import SenderPreference
from agent_platform.classification.models import EmailCategory, CATEGORY_IMPORTANCE_MAP


class SenderProfileService:
    """
    Service for managing sender profiles and applying preferences.

    Features:
    - Whitelist/Blacklist management
    - Trust level management
    - Category preference management (allow/mute)
    - Preference application during classification
    """

    def __init__(self):
        """Initialize sender profile service."""
        pass

    # ========================================================================
    # WHITELIST / BLACKLIST MANAGEMENT
    # ========================================================================

    async def whitelist_sender(
        self,
        sender_email: str,
        account_id: str,
        allowed_categories: Optional[List[str]] = None,
        preferred_primary: Optional[str] = None
    ) -> SenderPreference:
        """
        Add sender to whitelist (trusted senders).

        Whitelisted senders:
        - Get trust_level = 'trusted'
        - Get confidence boost during classification (+0.10)
        - Skip spam checks
        - Can have allowed categories specified

        Args:
            sender_email: Sender email address
            account_id: Account ID (gmail_1, gmail_2, etc.)
            allowed_categories: Optional list of allowed categories
            preferred_primary: Optional preferred primary category

        Returns:
            Updated SenderPreference object
        """
        with get_db() as db:
            # Get or create sender preference
            sender_domain = sender_email.split('@')[1] if '@' in sender_email else sender_email

            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if not pref:
                pref = SenderPreference(
                    account_id=account_id,
                    sender_email=sender_email,
                    sender_domain=sender_domain,
                )
                db.add(pref)

            # Set whitelist flags
            pref.is_whitelisted = True
            pref.is_blacklisted = False
            pref.trust_level = 'trusted'

            # Set category preferences if provided
            if allowed_categories is not None:
                pref.allowed_categories = allowed_categories

            if preferred_primary:
                pref.preferred_primary_category = preferred_primary

            db.commit()
            db.refresh(pref)

            # Expunge to allow access outside session
            db.expunge(pref)

            return pref

    async def blacklist_sender(
        self,
        sender_email: str,
        account_id: str
    ) -> SenderPreference:
        """
        Add sender to blacklist (blocked senders).

        Blacklisted senders:
        - Get trust_level = 'blocked'
        - All emails automatically classified as spam
        - Confidence = 0.99
        - Importance = 0.0

        Args:
            sender_email: Sender email address
            account_id: Account ID

        Returns:
            Updated SenderPreference object
        """
        with get_db() as db:
            sender_domain = sender_email.split('@')[1] if '@' in sender_email else sender_email

            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if not pref:
                pref = SenderPreference(
                    account_id=account_id,
                    sender_email=sender_email,
                    sender_domain=sender_domain,
                )
                db.add(pref)

            # Set blacklist flags
            pref.is_blacklisted = True
            pref.is_whitelisted = False
            pref.trust_level = 'blocked'

            db.commit()
            db.refresh(pref)

            # Expunge to allow access outside session
            db.expunge(pref)

            return pref

    async def remove_from_whitelist(
        self,
        sender_email: str,
        account_id: str
    ) -> SenderPreference:
        """Remove sender from whitelist (set to neutral)."""
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if pref:
                pref.is_whitelisted = False
                pref.trust_level = 'neutral'
                db.commit()
                db.refresh(pref)

            return pref

    async def remove_from_blacklist(
        self,
        sender_email: str,
        account_id: str
    ) -> SenderPreference:
        """Remove sender from blacklist (set to neutral)."""
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if pref:
                pref.is_blacklisted = False
                pref.trust_level = 'neutral'
                db.commit()
                db.refresh(pref)

            return pref

    # ========================================================================
    # TRUST LEVEL MANAGEMENT
    # ========================================================================

    async def set_trust_level(
        self,
        sender_email: str,
        account_id: str,
        trust_level: str  # 'trusted', 'neutral', 'suspicious', 'blocked'
    ) -> SenderPreference:
        """
        Set trust level for sender.

        Trust levels:
        - trusted: High trust, confidence boost (+0.10)
        - neutral: Normal trust, no modification
        - suspicious: Low trust, confidence penalty (-0.10)
        - blocked: No trust, always spam

        Args:
            sender_email: Sender email address
            account_id: Account ID
            trust_level: Trust level (trusted, neutral, suspicious, blocked)

        Returns:
            Updated SenderPreference object
        """
        with get_db() as db:
            sender_domain = sender_email.split('@')[1] if '@' in sender_email else sender_email

            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if not pref:
                pref = SenderPreference(
                    account_id=account_id,
                    sender_email=sender_email,
                    sender_domain=sender_domain,
                )
                db.add(pref)

            pref.trust_level = trust_level

            # Update whitelist/blacklist flags accordingly
            if trust_level == 'trusted':
                pref.is_whitelisted = True
                pref.is_blacklisted = False
            elif trust_level == 'blocked':
                pref.is_blacklisted = True
                pref.is_whitelisted = False
            else:
                pref.is_whitelisted = False
                pref.is_blacklisted = False

            db.commit()
            db.refresh(pref)

            # Expunge to allow access outside session
            db.expunge(pref)

            return pref

    # ========================================================================
    # CATEGORY PREFERENCE MANAGEMENT
    # ========================================================================

    async def set_category_preferences(
        self,
        sender_email: str,
        account_id: str,
        allowed_categories: Optional[List[str]] = None,
        muted_categories: Optional[List[str]] = None
    ) -> SenderPreference:
        """
        Set category preferences for sender.

        - allowed_categories: Only these categories are allowed from this sender
        - muted_categories: These categories are ignored from this sender

        Args:
            sender_email: Sender email address
            account_id: Account ID
            allowed_categories: List of allowed category names
            muted_categories: List of muted category names

        Returns:
            Updated SenderPreference object
        """
        with get_db() as db:
            sender_domain = sender_email.split('@')[1] if '@' in sender_email else sender_email

            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if not pref:
                pref = SenderPreference(
                    account_id=account_id,
                    sender_email=sender_email,
                    sender_domain=sender_domain,
                )
                db.add(pref)

            if allowed_categories is not None:
                pref.allowed_categories = allowed_categories

            if muted_categories is not None:
                pref.muted_categories = muted_categories

            db.commit()
            db.refresh(pref)

            # Expunge to allow access outside session
            db.expunge(pref)

            return pref

    async def mute_categories(
        self,
        sender_email: str,
        categories: List[str],
        account_id: str
    ) -> SenderPreference:
        """
        Mute specific categories from sender.

        Muted categories:
        - Get importance reduced to 0.10
        - Confidence reduced by -0.20
        - Effectively ignored

        Args:
            sender_email: Sender email address
            categories: List of category names to mute
            account_id: Account ID

        Returns:
            Updated SenderPreference object
        """
        return await self.set_category_preferences(
            sender_email=sender_email,
            account_id=account_id,
            muted_categories=categories
        )

    async def allow_only_categories(
        self,
        sender_email: str,
        categories: List[str],
        account_id: str
    ) -> SenderPreference:
        """
        Allow only specific categories from sender.

        Args:
            sender_email: Sender email address
            categories: List of allowed category names
            account_id: Account ID

        Returns:
            Updated SenderPreference object
        """
        return await self.set_category_preferences(
            sender_email=sender_email,
            account_id=account_id,
            allowed_categories=categories
        )

    # ========================================================================
    # PREFERENCE APPLICATION
    # ========================================================================

    async def get_sender_profile(
        self,
        sender_email: str,
        account_id: str
    ) -> Optional[SenderPreference]:
        """
        Get sender profile if exists.

        Args:
            sender_email: Sender email address
            account_id: Account ID

        Returns:
            SenderPreference object or None
        """
        with get_db() as db:
            pref = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            ).first()

            if pref:
                db.expunge(pref)  # Allow access outside session

            return pref

    async def apply_preferences(
        self,
        sender_email: str,
        account_id: str,
        classification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply sender preferences to classification result.

        Modifies:
        - Confidence (trust level boost/penalty)
        - Importance (muted categories reduction)
        - Primary category (blacklist → spam)
        - Secondary categories (filtered by allowed/muted)

        Args:
            sender_email: Sender email address
            account_id: Account ID
            classification_result: Dict with:
                - primary_category: str
                - secondary_categories: List[str]
                - confidence: float
                - importance_score: float
                - reasoning: str

        Returns:
            Modified classification result
        """
        profile = await self.get_sender_profile(sender_email, account_id)

        if not profile:
            # No preferences - return unchanged
            return classification_result

        # Create a copy to avoid modifying original
        result = classification_result.copy()

        # ====================================================================
        # BLACKLIST CHECK (highest priority)
        # ====================================================================
        if profile.is_blacklisted or profile.trust_level == 'blocked':
            result['primary_category'] = 'spam'
            result['secondary_categories'] = []
            result['confidence'] = 0.99
            result['importance_score'] = 0.0
            result['reasoning'] = f"Sender blacklisted. Original: {result.get('reasoning', 'N/A')}"
            return result

        # ====================================================================
        # WHITELIST / TRUST LEVEL BOOST
        # ====================================================================
        if profile.is_whitelisted or profile.trust_level == 'trusted':
            # Boost confidence
            result['confidence'] = min(1.0, result.get('confidence', 0.5) + 0.10)
            result['reasoning'] = f"[Trusted sender] {result.get('reasoning', '')}"

        elif profile.trust_level == 'suspicious':
            # Reduce confidence
            result['confidence'] = max(0.0, result.get('confidence', 0.5) - 0.10)
            result['reasoning'] = f"[Suspicious sender] {result.get('reasoning', '')}"

        # ====================================================================
        # CATEGORY FILTERING (allowed/muted)
        # ====================================================================

        # Get category lists (default to empty if None)
        allowed = profile.allowed_categories or []
        muted = profile.muted_categories or []

        # Check if primary category is muted
        primary_cat = result.get('primary_category')
        if primary_cat in muted:
            # Reduce importance drastically
            result['importance_score'] = 0.10
            result['confidence'] = max(0.0, result.get('confidence', 0.5) - 0.20)
            result['reasoning'] = f"[Category muted] {result.get('reasoning', '')}"

        # Filter secondary categories (remove muted ones)
        secondary = result.get('secondary_categories', [])
        if muted:
            filtered_secondary = [cat for cat in secondary if cat not in muted]
            result['secondary_categories'] = filtered_secondary

        # Check if primary category is in allowed list (if allowed list is set)
        if allowed and primary_cat not in allowed:
            # Category not allowed - reduce importance
            result['importance_score'] = max(0.10, result.get('importance_score', 0.5) * 0.3)
            result['reasoning'] = f"[Category not allowed] {result.get('reasoning', '')}"

        # ====================================================================
        # PREFERRED PRIMARY CATEGORY (suggestion)
        # ====================================================================
        if profile.preferred_primary_category and result.get('confidence', 0) < 0.70:
            # If confidence is low, consider using preferred category
            # (This is a suggestion, not enforced)
            result['reasoning'] += f" (Preferred: {profile.preferred_primary_category})"

        return result

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def list_whitelisted(self, account_id: str) -> List[SenderPreference]:
        """List all whitelisted senders for account."""
        with get_db() as db:
            prefs = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.is_whitelisted == True
            ).all()

            # Expunge all objects to allow access outside session
            for pref in prefs:
                db.expunge(pref)

            return prefs

    async def list_blacklisted(self, account_id: str) -> List[SenderPreference]:
        """List all blacklisted senders for account."""
        with get_db() as db:
            prefs = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.is_blacklisted == True
            ).all()

            # Expunge all objects to allow access outside session
            for pref in prefs:
                db.expunge(pref)

            return prefs

    async def get_profile_stats(self, account_id: str) -> Dict[str, int]:
        """Get statistics about sender profiles."""
        with get_db() as db:
            total = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id
            ).count()

            whitelisted = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.is_whitelisted == True
            ).count()

            blacklisted = db.query(SenderPreference).filter(
                SenderPreference.account_id == account_id,
                SenderPreference.is_blacklisted == True
            ).count()

            return {
                'total_profiles': total,
                'whitelisted': whitelisted,
                'blacklisted': blacklisted,
                'neutral': total - whitelisted - blacklisted
            }
