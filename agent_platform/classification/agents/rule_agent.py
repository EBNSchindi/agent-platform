"""
Rule-Based Classification Agent (OpenAI Agents SDK)

PRESERVATION PRINCIPLE:
This agent WRAPS the existing rule_layer.py logic WITHOUT changing it.
Pattern matching, thresholds, and confidence scores are IDENTICAL to the original.

Extract → Wrap → Orchestrate pattern:
1. EXTRACTED functions from importance_rules.py (AS-IS, no changes)
2. WRAPPED as Agent tools (interface change only)
3. ORCHESTRATED by Agent with instructions

Pattern Matching Logic:
- Spam detection: ← SAME keywords, patterns, thresholds (score >= 3)
- Auto-reply detection: ← SAME keywords, patterns (score >= 2)
- Newsletter detection: ← SAME keywords, sender patterns (score >= 2)
- System notifications: ← SAME sender patterns (score >= 2)
- Confidence scores: ← SAME (0.95 spam, 0.90 auto-reply, 0.85 newsletter, 0.80 system)
"""

import re
from typing import List, Tuple, Dict, Any
from pydantic import BaseModel, Field
from agents import Agent, FunctionTool

from agent_platform.classification.models import (
    EmailToClassify,
    RuleLayerResult,
    ImportanceCategory,
)


# ============================================================================
# EXTRACTED CONSTANTS (From importance_rules.py - UNCHANGED)
# ============================================================================

# ← SAME spam keywords as importance_rules.py
SPAM_KEYWORDS = [
    # German spam keywords
    "gewinnspiel", "gratis", "kostenlos", "viagra", "casino",
    "kredit ohne schufa", "geld verdienen", "abnehmen", "diät",
    "vergrößerung", "potenzmittel", "schnell reich werden",

    # English spam keywords
    "free money", "get rich quick", "enlarge", "weight loss",
    "buy now", "limited time offer", "act now", "click here",
    "congratulations you won", "nigerian prince", "inheritance",

    # Phishing indicators
    "verify your account", "confirm your identity", "suspended account",
    "urgent action required", "click immediately", "reset password now",
]

# ← SAME spam subject patterns as importance_rules.py
SPAM_SUBJECT_PATTERNS = [
    r"RE:\s*RE:\s*RE:",  # Multiple RE: (often spam)
    r"\$\$\$",            # Dollar signs
    r"!!!{3,}",           # Multiple exclamation marks
    r"WIN\s*WIN\s*WIN",   # Repeated "WIN"
    r"100%\s*FREE",       # "100% FREE"
    r"[A-Z]{10,}",        # Excessive caps
]

# ← SAME auto-reply keywords as importance_rules.py
AUTO_REPLY_KEYWORDS = [
    # German
    "automatische antwort", "abwesenheitsnotiz", "nicht im büro",
    "außer haus", "bin nicht erreichbar", "urlaubsmodus",

    # English
    "out of office", "automatic reply", "auto-reply", "away message",
    "vacation responder", "do not reply", "automated message",
    "this is an automated", "unattended mailbox",
]

# ← SAME auto-reply subject patterns as importance_rules.py
AUTO_REPLY_SUBJECTS = [
    r"^(out of office|ooo|abwesenheit):",
    r"^auto(matic)?\s*reply:",
    r"^away:",
    r"^urlaubsmodus:",
]

# ← SAME newsletter keywords as importance_rules.py
NEWSLETTER_KEYWORDS = [
    # Unsubscribe links (strong indicator)
    "unsubscribe", "abbestellen", "abmelden",
    "manage preferences", "einstellungen verwalten",

    # Newsletter-specific
    "newsletter", "rundbrief", "this week in",
    "monthly digest", "weekly update",

    # Marketing
    "special offer", "sonderangebot", "exklusiv für sie",
    "just for you", "personalized recommendations",
]

# ← SAME newsletter sender patterns as importance_rules.py
NEWSLETTER_SENDER_PATTERNS = [
    r"newsletter@",
    r"marketing@",
    r"news@",
    r"info@",
    r"noreply@",
    r"no-reply@",
    r"notifications?@",
]

# ← SAME system sender patterns as importance_rules.py
SYSTEM_SENDER_PATTERNS = [
    r"noreply@",
    r"no-reply@",
    r"donotreply@",
    r"do-not-reply@",
    r"notifications?@",
    r"alerts?@",
    r"system@",
    r"admin@",
    r"support@",
    r"service@",
]

# ← SAME system keywords as importance_rules.py
SYSTEM_KEYWORDS = [
    "password reset", "passwort zurücksetzen",
    "verification code", "bestätigungscode",
    "account created", "konto erstellt",
    "order confirmation", "bestellbestätigung",
    "shipping notification", "versandbenachrichtigung",
    "invoice", "rechnung",
]


# ============================================================================
# EXTRACTED FUNCTIONS (From importance_rules.py - LOGIC UNCHANGED)
# ============================================================================

def check_spam_patterns(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    EXTRACTED FROM: importance_rules.py RuleLayer._check_spam_patterns()

    PRESERVATION: Keywords, patterns, and threshold (score >= 3) are IDENTICAL to original.

    Check for spam patterns in email content.

    Args:
        subject: Email subject line
        body: Email body content
        sender: Sender email address

    Returns:
        Dictionary with:
        - is_spam: bool (True if score >= 3)
        - score: int (spam score)
        - matches: List[str] (matched patterns)
    """
    # ← SAME pattern matching logic as importance_rules.py
    text = f"{subject} {body}".lower()
    score = 0
    matches = []

    # Check spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword in text:
            score += 1
            matches.append(f"keyword:{keyword}")

    # Compile regex patterns
    spam_subject_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in SPAM_SUBJECT_PATTERNS
    ]

    # Check subject patterns (regex)
    for pattern in spam_subject_patterns:
        if pattern.search(subject):
            score += 2  # ← SAME weight as original (regex patterns are stronger)
            matches.append(f"pattern:{pattern.pattern}")

    # Check for excessive caps in subject (> 50%)
    if subject:
        caps_ratio = sum(1 for c in subject if c.isupper()) / len(subject)
        if caps_ratio > 0.5 and len(subject) > 10:
            score += 1
            matches.append("excessive_caps")

    # ← SAME threshold as importance_rules.py (score >= 3 = spam)
    return {
        'is_spam': score >= 3,
        'score': score,
        'matches': matches
    }


def check_auto_reply_patterns(subject: str, body: str) -> Dict[str, Any]:
    """
    EXTRACTED FROM: importance_rules.py RuleLayer._check_auto_reply_patterns()

    PRESERVATION: Keywords, patterns, and threshold (score >= 2) are IDENTICAL to original.

    Check for auto-reply patterns.

    Returns:
        Dictionary with:
        - is_auto_reply: bool (True if score >= 2)
        - score: int (auto-reply score)
        - matches: List[str] (matched patterns)
    """
    # ← SAME logic as importance_rules.py
    text = f"{subject} {body}".lower()
    score = 0
    matches = []

    # Check auto-reply keywords
    for keyword in AUTO_REPLY_KEYWORDS:
        if keyword in text:
            score += 2  # ← SAME weight as original (strong signal)
            matches.append(f"keyword:{keyword}")

    # Compile subject patterns
    auto_reply_subjects = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in AUTO_REPLY_SUBJECTS
    ]

    # Check subject patterns
    for pattern in auto_reply_subjects:
        if pattern.search(subject):
            score += 3  # ← SAME weight as original (very strong signal)
            matches.append(f"subject_pattern")
            break  # Only count once

    # ← SAME threshold as importance_rules.py (score >= 2 = auto-reply)
    return {
        'is_auto_reply': score >= 2,
        'score': score,
        'matches': matches
    }


def check_newsletter_patterns(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    EXTRACTED FROM: importance_rules.py RuleLayer._check_newsletter_patterns()

    PRESERVATION: Keywords, sender patterns, and threshold (score >= 2) are IDENTICAL.

    Check for newsletter patterns.

    Returns:
        Dictionary with:
        - is_newsletter: bool (True if score >= 2)
        - score: int (newsletter score)
        - matches: List[str] (matched patterns)
    """
    # ← SAME logic as importance_rules.py
    text = f"{subject} {body}".lower()
    score = 0
    matches = []

    # Check newsletter keywords
    for keyword in NEWSLETTER_KEYWORDS:
        if keyword in text:
            score += 1
            matches.append(f"keyword:{keyword}")
            # ← SAME special handling for unsubscribe (very strong signal)
            if keyword in ["unsubscribe", "abbestellen"]:
                score += 1

    # Compile sender patterns
    newsletter_sender_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in NEWSLETTER_SENDER_PATTERNS
    ]

    # Check sender patterns
    for pattern in newsletter_sender_patterns:
        if pattern.search(sender):
            score += 2  # ← SAME weight as original
            matches.append(f"sender:{pattern.pattern}")
            break

    # ← SAME threshold as importance_rules.py (score >= 2 = newsletter)
    return {
        'is_newsletter': score >= 2,
        'score': score,
        'matches': matches
    }


def check_system_notification_patterns(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    EXTRACTED FROM: importance_rules.py RuleLayer._check_system_notification_patterns()

    PRESERVATION: Keywords, sender patterns, and threshold (score >= 2) are IDENTICAL.

    Check for system notification patterns.

    Returns:
        Dictionary with:
        - is_system: bool (True if score >= 2)
        - score: int (system score)
        - matches: List[str] (matched patterns)
    """
    # ← SAME logic as importance_rules.py
    text = f"{subject} {body}".lower()
    score = 0
    matches = []

    # Check system keywords
    for keyword in SYSTEM_KEYWORDS:
        if keyword in text:
            score += 1
            matches.append(f"keyword:{keyword}")

    # Compile sender patterns
    system_sender_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in SYSTEM_SENDER_PATTERNS
    ]

    # Check sender patterns (strong signal for system emails)
    for pattern in system_sender_patterns:
        if pattern.search(sender):
            score += 2  # ← SAME weight as original
            matches.append(f"sender:{pattern.pattern}")
            break

    # ← SAME threshold as importance_rules.py (score >= 2 = system)
    return {
        'is_system': score >= 2,
        'score': score,
        'matches': matches
    }


def classify_email_with_rules(
    email_id: str,
    subject: str,
    body: str,
    sender: str
) -> Dict[str, Any]:
    """
    WRAPPER FUNCTION: Orchestrates all pattern checks with SAME priority order as original.

    PRESERVATION: Check order and confidence scores are IDENTICAL to importance_rules.py:
    1. Spam (confidence: 0.95)
    2. Auto-reply (confidence: 0.90)
    3. Newsletter (confidence: 0.85)
    4. System notification (confidence: 0.80)

    Returns:
        Dictionary with RuleLayerResult fields
    """
    matched_rules = []
    spam_signals = []
    auto_reply_signals = []
    newsletter_signals = []

    # ====================================================================
    # CHECK 1: SPAM DETECTION (Highest priority - confidence: 0.95)
    # ====================================================================
    # ← SAME priority order as importance_rules.py

    spam_result = check_spam_patterns(subject, body, sender)
    if spam_result['score'] > 0:
        spam_signals.extend(spam_result['matches'])
        matched_rules.append("spam_detection")

        # ← SAME threshold as importance_rules.py (score >= 3)
        if spam_result['is_spam']:
            return {
                'matched_rules': matched_rules,
                'importance': 0.0,  # ← SAME as original
                'confidence': 0.95,  # ← SAME as original
                'category': 'spam',
                'reasoning': f"Spam detected: {', '.join(spam_result['matches'][:3])}",
                'spam_signals': spam_signals,
                'auto_reply_signals': [],
                'newsletter_signals': [],
            }

    # ====================================================================
    # CHECK 2: AUTO-REPLY DETECTION (Confidence: 0.90)
    # ====================================================================

    auto_reply_result = check_auto_reply_patterns(subject, body)
    if auto_reply_result['score'] > 0:
        auto_reply_signals.extend(auto_reply_result['matches'])
        matched_rules.append("auto_reply_detection")

        # ← SAME threshold as importance_rules.py (score >= 2)
        if auto_reply_result['is_auto_reply']:
            return {
                'matched_rules': matched_rules,
                'importance': 0.1,  # ← SAME as original
                'confidence': 0.90,  # ← SAME as original
                'category': 'system_notifications',
                'reasoning': f"Auto-reply detected: {', '.join(auto_reply_result['matches'])}",
                'spam_signals': spam_signals,
                'auto_reply_signals': auto_reply_signals,
                'newsletter_signals': [],
            }

    # ====================================================================
    # CHECK 3: NEWSLETTER DETECTION (Confidence: 0.85)
    # ====================================================================

    newsletter_result = check_newsletter_patterns(subject, body, sender)
    if newsletter_result['score'] > 0:
        newsletter_signals.extend(newsletter_result['matches'])
        matched_rules.append("newsletter_detection")

        # ← SAME threshold as importance_rules.py (score >= 2)
        if newsletter_result['is_newsletter']:
            return {
                'matched_rules': matched_rules,
                'importance': 0.3,  # ← SAME as original
                'confidence': 0.85,  # ← SAME as original
                'category': 'newsletter',
                'reasoning': f"Newsletter detected: {', '.join(newsletter_result['matches'][:2])}",
                'spam_signals': spam_signals,
                'auto_reply_signals': auto_reply_signals,
                'newsletter_signals': newsletter_signals,
            }

    # ====================================================================
    # CHECK 4: SYSTEM NOTIFICATION (Confidence: 0.80)
    # ====================================================================

    system_result = check_system_notification_patterns(subject, body, sender)
    # ← SAME threshold as importance_rules.py (score >= 2)
    if system_result['is_system']:
        matched_rules.append("system_notification")

        return {
            'matched_rules': matched_rules,
            'importance': 0.4,  # ← SAME as original
            'confidence': 0.80,  # ← SAME as original
            'category': 'system_notifications',
            'reasoning': f"System notification: {', '.join(system_result['matches'][:2])}",
            'spam_signals': spam_signals,
            'auto_reply_signals': auto_reply_signals,
            'newsletter_signals': newsletter_signals,
        }

    # ====================================================================
    # NO HIGH-CONFIDENCE MATCH - Return low confidence
    # ====================================================================
    # ← SAME fallback logic as importance_rules.py

    # Some weak signals detected but not enough for high confidence
    if spam_result['score'] > 0 or newsletter_result['score'] > 0:
        return {
            'matched_rules': matched_rules or ["no_clear_pattern"],
            'importance': 0.5,  # ← SAME as original
            'confidence': 0.3,  # ← SAME as original
            'category': 'nice_to_know',
            'reasoning': "Weak patterns detected, needs deeper analysis",
            'spam_signals': spam_signals,
            'auto_reply_signals': auto_reply_signals,
            'newsletter_signals': newsletter_signals,
        }

    # No clear patterns at all
    return {
        'matched_rules': ["no_pattern_match"],
        'importance': 0.5,  # ← SAME as original
        'confidence': 0.2,  # ← SAME as original
        'category': 'nice_to_know',
        'reasoning': "No clear rule patterns matched",
        'spam_signals': [],
        'auto_reply_signals': [],
        'newsletter_signals': [],
    }


# ============================================================================
# AGENT INSTRUCTIONS
# ============================================================================

RULE_AGENT_INSTRUCTIONS = """You are a rule-based email classification expert.

Your job is to use the pattern matching tools to classify emails quickly and accurately.

**Tools Available:**
- classify_email_with_rules: Main classification function using pattern matching

**Classification Process:**
1. Call classify_email_with_rules with the email data
2. Return the result (contains category, confidence, importance, reasoning)

**Confidence Levels:**
- 0.95: Spam (clear spam patterns detected)
- 0.90: Auto-reply (clear auto-reply patterns)
- 0.85: Newsletter (clear newsletter patterns)
- 0.80: System notification (clear system patterns)
- 0.2-0.3: Low confidence (no clear patterns, needs next layer)

**Important:**
- You ONLY use pattern matching (no LLM analysis)
- High confidence (≥0.85) means the orchestrator can stop here
- Low confidence means pass to History Layer for deeper analysis
"""


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_rule_agent() -> Agent:
    """
    Create rule-based classification agent with OpenAI Agents SDK.

    PRESERVATION: This agent wraps the SAME logic from importance_rules.py
    with the Agent SDK interface. Classification decisions are IDENTICAL.

    Returns:
        Agent instance configured for rule-based classification
    """
    # Pass function directly as tool - Agent SDK will auto-wrap it
    agent = Agent(
        name="RuleClassifier",
        instructions=RULE_AGENT_INSTRUCTIONS,
        tools=[classify_email_with_rules],
        model="gpt-4o-mini"  # Fast model for tool orchestration
    )

    return agent
