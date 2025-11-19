"""
History-Based Classification Agent (OpenAI Agents SDK)

PRESERVATION PRINCIPLE:
This agent WRAPS the existing history_layer.py logic WITHOUT changing it.
EMA learning formula (α=0.15), thresholds, and database queries are IDENTICAL.

Extract → Wrap → Orchestrate pattern:
1. EXTRACTED functions from importance_history.py (AS-IS, no changes)
2. WRAPPED as Agent tools (interface change only)
3. ORCHESTRATED by Agent with instructions

User Behavior Learning:
- Reply rate thresholds: ← SAME (70%, 30%)
- Archive rate thresholds: ← SAME (80%)
- Confidence formulas: ← SAME (sender: 0.85, domain: 0.75)
- Minimum emails: ← SAME (sender: 5, domain: 10)
- EMA formula (α=0.15): ← PRESERVED in feedback update logic
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from agents import Agent
from sqlalchemy.orm import Session

from agent_platform.classification.models import (
    EmailToClassify,
    HistoryLayerResult,
    ImportanceCategory,
)
from agent_platform.db.models import SenderPreference, DomainPreference
from agent_platform.db.database import get_db


# ============================================================================
# EXTRACTED CONSTANTS (From importance_history.py - UNCHANGED)
# ============================================================================

# ← SAME thresholds as importance_history.py
MIN_EMAILS_HIGH_CONFIDENCE_SENDER = 5   # Need 5+ emails for high confidence
MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN = 10  # Need 10+ domain emails

SENDER_BASE_CONFIDENCE = 0.85  # ← SAME as original
DOMAIN_BASE_CONFIDENCE = 0.75  # ← SAME as original

# Reply rate thresholds for importance
HIGH_REPLY_RATE = 0.7   # ← SAME as original (>= 70% reply rate)
MEDIUM_REPLY_RATE = 0.3  # ← SAME as original (30-70% reply rate)

# Archive rate threshold
HIGH_ARCHIVE_RATE = 0.8  # ← SAME as original (>= 80% archived)


# ============================================================================
# EXTRACTED FUNCTIONS (From importance_history.py - LOGIC UNCHANGED)
# ============================================================================

def extract_domain(email: str) -> str:
    """
    EXTRACTED FROM: importance_history.py HistoryLayer._extract_domain()

    PRESERVATION: Domain extraction logic is IDENTICAL.

    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain part (lowercase)
    """
    # ← SAME logic as importance_history.py
    if "@" in email:
        return email.split("@")[1].lower()
    return email.lower()


def calculate_importance_from_behavior(
    reply_rate: float,
    archive_rate: float,
    delete_rate: float,
    avg_time_to_reply: Optional[float],
) -> tuple[float, ImportanceCategory, str]:
    """
    EXTRACTED FROM: importance_history.py HistoryLayer._calculate_importance_from_behavior()

    PRESERVATION: Thresholds and importance calculations are IDENTICAL.

    Calculate importance score and category from behavioral metrics.

    Args:
        reply_rate: Reply rate (0.0 to 1.0)
        archive_rate: Archive rate (0.0 to 1.0)
        delete_rate: Delete rate (0.0 to 1.0)
        avg_time_to_reply: Average time to reply in hours (optional)

    Returns:
        Tuple of (importance_score, category, reasoning)
    """
    # ← SAME decision tree as importance_history.py

    # High reply rate → important emails
    if reply_rate >= HIGH_REPLY_RATE:  # ← SAME threshold (0.7)
        # Very responsive to this sender
        if avg_time_to_reply and avg_time_to_reply < 2.0:  # ← SAME threshold (< 2 hours)
            # Quick replies → action required
            return (
                0.9,  # ← SAME importance score
                "action_required",
                f"{reply_rate:.0%} reply rate, avg {avg_time_to_reply:.1f}h response time"
            )
        else:
            # Regular replies → important
            return (
                0.8,  # ← SAME importance score
                "wichtig",
                f"{reply_rate:.0%} reply rate (consistently responded to)"
            )

    # Medium reply rate → nice to know
    elif reply_rate >= MEDIUM_REPLY_RATE:  # ← SAME threshold (0.3)
        return (
            0.5,  # ← SAME importance score
            "nice_to_know",
            f"{reply_rate:.0%} reply rate (occasionally responded to)"
        )

    # Low reply rate + high archive rate → newsletters/automated
    elif archive_rate >= HIGH_ARCHIVE_RATE:  # ← SAME threshold (0.8)
        return (
            0.3,  # ← SAME importance score
            "newsletter",
            f"{archive_rate:.0%} archived without reply (likely newsletters)"
        )

    # Low reply rate + high delete rate → spam or unwanted
    elif delete_rate > 0.5:  # ← SAME threshold (0.5)
        return (
            0.1,  # ← SAME importance score
            "spam",
            f"{delete_rate:.0%} deleted (likely unwanted)"
        )

    # Low engagement overall → system notifications or low priority
    else:
        return (
            0.4,  # ← SAME importance score
            "system_notifications",
            f"Low engagement ({reply_rate:.0%} reply, {archive_rate:.0%} archive)"
        )


def calculate_confidence(
    total_emails: int,
    base_confidence: float,
    is_sender_level: bool
) -> float:
    """
    EXTRACTED FROM: importance_history.py HistoryLayer._calculate_confidence()

    PRESERVATION: Confidence calculation formula is IDENTICAL.

    Calculate confidence based on amount of historical data.

    More emails → higher confidence (up to base_confidence).

    Args:
        total_emails: Number of historical emails
        base_confidence: Base confidence level (0.85 for sender, 0.75 for domain)
        is_sender_level: Whether using sender-level data (vs domain-level)

    Returns:
        Confidence score (0.0 to 1.0)
    """
    # ← SAME logic as importance_history.py

    min_threshold = (
        MIN_EMAILS_HIGH_CONFIDENCE_SENDER  # ← SAME (5)
        if is_sender_level
        else MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN  # ← SAME (10)
    )

    if total_emails < min_threshold:
        # Not enough data → scale confidence down
        # ← SAME formula as original
        return base_confidence * (total_emails / min_threshold) * 0.7

    # Enough data → full confidence (but cap at base_confidence)
    # Add slight bonus for more data (up to +0.1)
    # ← SAME formula as original
    bonus = min(0.1, (total_emails - min_threshold) / 50 * 0.1)
    return min(1.0, base_confidence + bonus)


def get_sender_preference(
    account_id: str,
    sender_email: str,
    db: Session
) -> Optional[SenderPreference]:
    """
    EXTRACTED FROM: importance_history.py HistoryLayer._get_sender_preference()

    PRESERVATION: Database query is IDENTICAL.

    Get sender preference from database.

    Args:
        account_id: Account ID (e.g., "gmail_1")
        sender_email: Sender email address
        db: Database session

    Returns:
        SenderPreference object or None
    """
    # ← SAME query as importance_history.py
    try:
        return (
            db.query(SenderPreference)
            .filter(
                SenderPreference.account_id == account_id,
                SenderPreference.sender_email == sender_email
            )
            .first()
        )
    except Exception as e:
        print(f"⚠️  Error querying sender preference: {e}")
        return None


def get_domain_preference(
    account_id: str,
    domain: str,
    db: Session
) -> Optional[DomainPreference]:
    """
    EXTRACTED FROM: importance_history.py HistoryLayer._get_domain_preference()

    PRESERVATION: Database query is IDENTICAL.

    Get domain preference from database.

    Args:
        account_id: Account ID (e.g., "gmail_1")
        domain: Domain name
        db: Database session

    Returns:
        DomainPreference object or None
    """
    # ← SAME query as importance_history.py
    try:
        return (
            db.query(DomainPreference)
            .filter(
                DomainPreference.account_id == account_id,
                DomainPreference.domain == domain
            )
            .first()
        )
    except Exception as e:
        print(f"⚠️  Error querying domain preference: {e}")
        return None


def classify_email_with_history(
    email_id: str,
    sender: str,
    account_id: str
) -> Dict[str, Any]:
    """
    WRAPPER FUNCTION: Classify email based on historical user behavior.

    PRESERVATION: Sender-first, then domain fallback logic is IDENTICAL to original.
    Confidence thresholds (sender: 0.85, domain: 0.75) are UNCHANGED.

    Args:
        email_id: Email ID
        sender: Sender email address
        account_id: Account ID (e.g., "gmail_1")

    Returns:
        Dictionary with HistoryLayerResult fields
    """
    sender_email = sender.lower()
    sender_domain = extract_domain(sender_email)

    # Get database session
    # Note: Using context manager for safety
    with get_db() as db:
        # ====================================================================
        # STEP 1: Check sender-specific preferences (highest priority)
        # ====================================================================
        # ← SAME priority as importance_history.py

        sender_pref = get_sender_preference(account_id, sender_email, db)

        # ← SAME threshold as original (5 emails)
        if sender_pref and sender_pref.total_emails_received >= MIN_EMAILS_HIGH_CONFIDENCE_SENDER:
            # We have enough sender-specific data for high confidence
            importance, category, reasoning = calculate_importance_from_behavior(
                reply_rate=sender_pref.reply_rate,
                archive_rate=sender_pref.archive_rate,
                delete_rate=sender_pref.delete_rate,
                avg_time_to_reply=sender_pref.avg_time_to_reply_hours,
            )

            confidence = calculate_confidence(
                total_emails=sender_pref.total_emails_received,
                base_confidence=SENDER_BASE_CONFIDENCE,  # ← SAME (0.85)
                is_sender_level=True,
            )

            return {
                'sender_email': sender_pref.sender_email,
                'sender_domain': sender_pref.sender_domain,
                'sender_preference_found': True,
                'domain_preference_found': False,
                'historical_reply_rate': sender_pref.reply_rate,
                'historical_archive_rate': sender_pref.archive_rate,
                'total_historical_emails': sender_pref.total_emails_received,
                'importance': importance,
                'confidence': confidence,
                'category': category,
                'reasoning': f"Sender history ({sender_pref.total_emails_received} emails): {reasoning}",
                'data_source': 'sender',
            }

        # ====================================================================
        # STEP 2: Check domain-level preferences (fallback)
        # ====================================================================

        domain_pref = get_domain_preference(account_id, sender_domain, db)

        # ← SAME threshold as original (10 emails)
        if domain_pref and domain_pref.total_emails_received >= MIN_EMAILS_HIGH_CONFIDENCE_DOMAIN:
            # We have enough domain data for moderate confidence
            importance, category, reasoning = calculate_importance_from_behavior(
                reply_rate=domain_pref.reply_rate,
                archive_rate=domain_pref.archive_rate,
                delete_rate=0.0,  # ← SAME (domain-level doesn't track delete rate)
                avg_time_to_reply=None,  # ← SAME (domain-level doesn't track time)
            )

            confidence = calculate_confidence(
                total_emails=domain_pref.total_emails_received,
                base_confidence=DOMAIN_BASE_CONFIDENCE,  # ← SAME (0.75)
                is_sender_level=False,
            )

            return {
                'sender_email': sender_email,
                'sender_domain': sender_domain,
                'sender_preference_found': False,
                'domain_preference_found': True,
                'historical_reply_rate': domain_pref.reply_rate,
                'historical_archive_rate': domain_pref.archive_rate,
                'total_historical_emails': domain_pref.total_emails_received,
                'importance': importance,
                'confidence': confidence,
                'category': category,
                'reasoning': f"Domain history ({domain_pref.total_emails_received} emails): {reasoning}",
                'data_source': 'domain',
            }

        # ====================================================================
        # STEP 3: Insufficient historical data - low confidence
        # ====================================================================
        # ← SAME fallback logic as importance_history.py

        # Some historical data exists but not enough for high confidence
        if sender_pref or domain_pref:
            pref = sender_pref or domain_pref
            data_source = "sender" if sender_pref else "domain"
            total_emails = pref.total_emails_received if pref else 0

            return {
                'sender_email': sender_email,
                'sender_domain': sender_domain,
                'sender_preference_found': bool(sender_pref),
                'domain_preference_found': bool(domain_pref),
                'historical_reply_rate': pref.reply_rate if pref else None,
                'historical_archive_rate': pref.archive_rate if pref else None,
                'total_historical_emails': total_emails,
                'importance': 0.5,  # ← SAME as original
                'confidence': 0.4,  # ← SAME as original
                'category': 'nice_to_know',
                'reasoning': f"Insufficient historical data ({total_emails} emails) for confident classification",
                'data_source': data_source,
            }

        # No historical data at all
        return {
            'sender_email': sender_email,
            'sender_domain': sender_domain,
            'sender_preference_found': False,
            'domain_preference_found': False,
            'historical_reply_rate': None,
            'historical_archive_rate': None,
            'total_historical_emails': 0,
            'importance': 0.5,  # ← SAME as original
            'confidence': 0.2,  # ← SAME as original
            'category': 'nice_to_know',
            'reasoning': "No historical data available - first email from this sender/domain",
            'data_source': 'default',
        }


# ============================================================================
# AGENT INSTRUCTIONS
# ============================================================================

HISTORY_AGENT_INSTRUCTIONS = """You are a history-based email classification expert.

Your job is to use historical user behavior data to classify emails based on past patterns.

**Tools Available:**
- classify_email_with_history: Classification based on sender/domain history

**Classification Process:**
1. Call classify_email_with_history with email data
2. Return the result (contains category, confidence, importance, reasoning)

**Confidence Levels:**
- 0.85+: High confidence from sender-specific data (5+ emails)
- 0.75+: Moderate confidence from domain-level data (10+ emails)
- 0.4: Low confidence (some data but not enough)
- 0.2: Very low confidence (no historical data)

**Data Sources (Priority Order):**
1. **Sender-specific**: Most reliable (if 5+ emails from this sender)
2. **Domain-level**: Moderate reliability (if 10+ emails from this domain)
3. **No data**: Low confidence, pass to LLM Layer

**Behavioral Patterns Used:**
- Reply rate: How often the user replies to this sender/domain
- Archive rate: How often emails are archived without reply
- Delete rate: How often emails are deleted (spam signal)
- Average time to reply: Urgency indicator (< 2h = action required)

**Important:**
- You ONLY use database lookups (no LLM analysis)
- High confidence (≥0.85) means the orchestrator can stop here
- Low confidence means pass to LLM Layer for semantic analysis
"""


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_history_agent() -> Agent:
    """
    Create history-based classification agent with OpenAI Agents SDK.

    PRESERVATION: This agent wraps the SAME logic from importance_history.py
    with the Agent SDK interface. Classification decisions and EMA learning
    (α=0.15) are IDENTICAL to the original implementation.

    Note: EMA learning (α=0.15) happens in the feedback update logic,
    not in classification. This agent only READS preferences.

    Returns:
        Agent instance configured for history-based classification
    """
    agent = Agent(
        name="HistoryClassifier",
        instructions=HISTORY_AGENT_INSTRUCTIONS,
        tools=[classify_email_with_history],
        model="gpt-4o-mini"  # Fast model for tool orchestration
    )

    return agent
