"""
Rule-Based Importance Classification Layer

Fast pattern matching using keywords, sender patterns, and heuristics.
NO LLM calls - pure Python logic for speed and efficiency.

High confidence when clear patterns are detected:
- Spam keywords → spam (confidence: 0.95)
- Auto-reply patterns → system_notifications (confidence: 0.90)
- Newsletter patterns → newsletter (confidence: 0.85)
- No-reply addresses → system_notifications (confidence: 0.80)

Low/medium confidence otherwise - passes to History Layer.
"""

import re
from typing import List, Tuple
from agent_platform.classification.models import (
    EmailToClassify,
    RuleLayerResult,
    ImportanceCategory,
)


class RuleLayer:
    """
    Rule-based classification layer - fast pattern matching.

    Uses keyword matching, regex patterns, and heuristics to classify emails
    without LLM calls. High confidence when clear patterns match.
    """

    # ========================================================================
    # SPAM DETECTION PATTERNS
    # ========================================================================

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

    SPAM_SUBJECT_PATTERNS = [
        r"RE:\s*RE:\s*RE:",  # Multiple RE: (often spam)
        r"\$\$\$",            # Dollar signs
        r"!!!{3,}",           # Multiple exclamation marks
        r"WIN\s*WIN\s*WIN",   # Repeated "WIN"
        r"100%\s*FREE",       # "100% FREE"
        r"[A-Z]{10,}",        # Excessive caps
    ]

    # ========================================================================
    # AUTO-REPLY / AUTOMATED EMAIL PATTERNS
    # ========================================================================

    AUTO_REPLY_KEYWORDS = [
        # German
        "automatische antwort", "abwesenheitsnotiz", "nicht im büro",
        "außer haus", "bin nicht erreichbar", "urlaubsmodus",

        # English
        "out of office", "automatic reply", "auto-reply", "away message",
        "vacation responder", "do not reply", "automated message",
        "this is an automated", "unattended mailbox",
    ]

    AUTO_REPLY_SUBJECTS = [
        r"^(out of office|ooo|abwesenheit):",
        r"^auto(matic)?\s*reply:",
        r"^away:",
        r"^urlaubsmodus:",
    ]

    # ========================================================================
    # NEWSLETTER PATTERNS
    # ========================================================================

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

    NEWSLETTER_SENDER_PATTERNS = [
        r"newsletter@",
        r"marketing@",
        r"news@",
        r"info@",
        r"noreply@",
        r"no-reply@",
        r"notifications?@",
    ]

    # ========================================================================
    # SYSTEM NOTIFICATION PATTERNS
    # ========================================================================

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

    SYSTEM_KEYWORDS = [
        "password reset", "passwort zurücksetzen",
        "verification code", "bestätigungscode",
        "account created", "konto erstellt",
        "order confirmation", "bestellbestätigung",
        "shipping notification", "versandbenachrichtigung",
        "invoice", "rechnung",
    ]

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    def __init__(self):
        """Initialize the rule layer with compiled patterns for efficiency."""
        # Compile regex patterns once for performance
        self.spam_subject_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SPAM_SUBJECT_PATTERNS
        ]

        self.auto_reply_subjects = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.AUTO_REPLY_SUBJECTS
        ]

        self.newsletter_sender_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.NEWSLETTER_SENDER_PATTERNS
        ]

        self.system_sender_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SYSTEM_SENDER_PATTERNS
        ]

    # ========================================================================
    # MAIN CLASSIFICATION METHOD
    # ========================================================================

    def classify(self, email: EmailToClassify) -> RuleLayerResult:
        """
        Classify email using rule-based patterns.

        Returns high confidence when clear patterns match, low/medium
        confidence otherwise (requiring History or LLM layer).

        Args:
            email: Email to classify

        Returns:
            RuleLayerResult with classification and matched rules
        """
        matched_rules = []
        spam_signals = []
        auto_reply_signals = []
        newsletter_signals = []

        # Combine subject + body for analysis
        text = f"{email.subject} {email.body}".lower()

        # ====================================================================
        # CHECK 1: SPAM DETECTION (Highest priority - confidence: 0.95)
        # ====================================================================

        spam_score, spam_matches = self._check_spam_patterns(email, text)
        if spam_score > 0:
            spam_signals.extend(spam_matches)
            matched_rules.append("spam_detection")

            if spam_score >= 3:  # High confidence spam
                return RuleLayerResult(
                    matched_rules=matched_rules,
                    importance=0.0,
                    confidence=0.95,
                    category="spam",
                    reasoning=f"Spam detected: {', '.join(spam_matches[:3])}",
                    spam_signals=spam_signals,
                    auto_reply_signals=[],
                    newsletter_signals=[],
                )

        # ====================================================================
        # CHECK 2: AUTO-REPLY DETECTION (Confidence: 0.70 - lowered for learning)
        # ====================================================================

        auto_reply_score, auto_matches = self._check_auto_reply_patterns(email, text)
        if auto_reply_score > 0:
            auto_reply_signals.extend(auto_matches)
            matched_rules.append("auto_reply_detection")

            if auto_reply_score >= 2:  # Likely auto-reply
                return RuleLayerResult(
                    matched_rules=matched_rules,
                    importance=0.1,
                    confidence=0.70,  # ❗ LOWERED from 0.90 → more emails to History/LLM
                    category="newsletter",  # Auto-replies are informational
                    reasoning=f"Likely auto-reply (check history): {', '.join(auto_matches)}",
                    spam_signals=spam_signals,
                    auto_reply_signals=auto_reply_signals,
                    newsletter_signals=[],
                )

        # ====================================================================
        # CHECK 3: NEWSLETTER DETECTION (Confidence: 0.65 - lowered for learning)
        # ====================================================================

        newsletter_score, newsletter_matches = self._check_newsletter_patterns(email, text)
        if newsletter_score > 0:
            newsletter_signals.extend(newsletter_matches)
            matched_rules.append("newsletter_detection")

            if newsletter_score >= 2:  # Likely newsletter
                return RuleLayerResult(
                    matched_rules=matched_rules,
                    importance=0.3,
                    confidence=0.65,  # ❗ LOWERED from 0.85 → History can override
                    category="newsletter",
                    reasoning=f"Likely newsletter (check preferences): {', '.join(newsletter_matches[:2])}",
                    spam_signals=spam_signals,
                    auto_reply_signals=auto_reply_signals,
                    newsletter_signals=newsletter_signals,
                )

        # ====================================================================
        # CHECK 4: SYSTEM NOTIFICATION (Confidence: 0.50 - very low, let LLM decide)
        # ====================================================================

        system_score, system_matches = self._check_system_notification_patterns(email, text)
        if system_score >= 2:  # Possible system notification
            matched_rules.append("system_notification")

            return RuleLayerResult(
                matched_rules=matched_rules,
                importance=0.4,
                confidence=0.50,  # ❗ LOWERED from 0.80 → LLM/History decides importance
                category="newsletter",  # System notifications (password resets, confirmations) are informational
                reasoning=f"Possible system notification (pass to LLM): {', '.join(system_matches[:2])}",
                spam_signals=spam_signals,
                auto_reply_signals=auto_reply_signals,
                newsletter_signals=newsletter_signals,
            )

        # ====================================================================
        # NO HIGH-CONFIDENCE MATCH - Return low confidence
        # ====================================================================

        # Some weak signals detected but not enough for high confidence
        if spam_score > 0 or newsletter_score > 0:
            return RuleLayerResult(
                matched_rules=matched_rules or ["no_clear_pattern"],
                importance=0.5,  # Neutral importance
                confidence=0.3,  # Low confidence - needs next layer
                category="newsletter",  # Default category (neutral fallback)
                reasoning="Weak patterns detected, needs deeper analysis",
                spam_signals=spam_signals,
                auto_reply_signals=auto_reply_signals,
                newsletter_signals=newsletter_signals,
            )

        # No clear patterns at all
        return RuleLayerResult(
            matched_rules=["no_pattern_match"],
            importance=0.5,  # Neutral
            confidence=0.2,  # Very low confidence - definitely needs next layer
            category="newsletter",  # Default fallback
            reasoning="No clear rule patterns matched",
            spam_signals=[],
            auto_reply_signals=[],
            newsletter_signals=[],
        )

    # ========================================================================
    # PATTERN CHECKING METHODS
    # ========================================================================

    def _check_spam_patterns(
        self, email: EmailToClassify, text: str
    ) -> Tuple[int, List[str]]:
        """
        Check for spam patterns.

        Returns:
            (spam_score, matched_patterns)
            Score >= 3 = high confidence spam
        """
        score = 0
        matches = []

        # Check spam keywords
        for keyword in self.SPAM_KEYWORDS:
            if keyword in text:
                score += 1
                matches.append(f"keyword:{keyword}")

        # Check subject patterns (regex)
        for pattern in self.spam_subject_patterns:
            if pattern.search(email.subject):
                score += 2  # Regex patterns are stronger signals
                matches.append(f"pattern:{pattern.pattern}")

        # Check for excessive caps in subject (> 50%)
        if email.subject:
            caps_ratio = sum(1 for c in email.subject if c.isupper()) / len(email.subject)
            if caps_ratio > 0.5 and len(email.subject) > 10:
                score += 1
                matches.append("excessive_caps")

        return score, matches

    def _check_auto_reply_patterns(
        self, email: EmailToClassify, text: str
    ) -> Tuple[int, List[str]]:
        """
        Check for auto-reply patterns.

        Returns:
            (auto_reply_score, matched_patterns)
            Score >= 2 = high confidence auto-reply
        """
        score = 0
        matches = []

        # Check auto-reply keywords
        for keyword in self.AUTO_REPLY_KEYWORDS:
            if keyword in text:
                score += 2  # Strong signal
                matches.append(f"keyword:{keyword}")

        # Check subject patterns
        for pattern in self.auto_reply_subjects:
            if pattern.search(email.subject):
                score += 3  # Very strong signal
                matches.append(f"subject_pattern")
                break  # Only count once

        return score, matches

    def _check_newsletter_patterns(
        self, email: EmailToClassify, text: str
    ) -> Tuple[int, List[str]]:
        """
        Check for newsletter patterns.

        Returns:
            (newsletter_score, matched_patterns)
            Score >= 2 = high confidence newsletter
        """
        score = 0
        matches = []

        # Check newsletter keywords
        for keyword in self.NEWSLETTER_KEYWORDS:
            if keyword in text:
                score += 1
                matches.append(f"keyword:{keyword}")
                if keyword in ["unsubscribe", "abbestellen"]:
                    score += 1  # Unsubscribe is very strong signal

        # Check sender patterns
        for pattern in self.newsletter_sender_patterns:
            if pattern.search(email.sender):
                score += 2
                matches.append(f"sender:{pattern.pattern}")
                break

        return score, matches

    def _check_system_notification_patterns(
        self, email: EmailToClassify, text: str
    ) -> Tuple[int, List[str]]:
        """
        Check for system notification patterns.

        Returns:
            (system_score, matched_patterns)
            Score >= 2 = high confidence system notification
        """
        score = 0
        matches = []

        # Check system keywords
        for keyword in self.SYSTEM_KEYWORDS:
            if keyword in text:
                score += 1
                matches.append(f"keyword:{keyword}")

        # Check sender patterns (strong signal for system emails)
        for pattern in self.system_sender_patterns:
            if pattern.search(email.sender):
                score += 2
                matches.append(f"sender:{pattern.pattern}")
                break

        return score, matches
