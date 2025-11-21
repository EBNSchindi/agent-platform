"""
10-Category Rule-Based Classification Agent (Phase 8)

Extended rule-based classification with 10 fine-grained categories:
1. wichtig_todo - Action required, decisions, tasks, callbacks
2. termine - Calendar invitations, events, appointments
3. finanzen - Invoices, payments, financial matters
4. bestellungen - Orders, shipping, tracking
5. job_projekte - Business communication, projects, customers
6. vertraege - Contracts, authorities, formal/legal
7. persoenlich - Family, friends, personal messages
8. newsletter - Regular updates, content newsletters
9. werbung - Marketing, promotions, sales
10. spam - Spam, phishing, junk

Features:
- Primary category detection (1 per email)
- Secondary category detection (0-3 additional tags)
- Pattern-based confidence scoring
- Multi-category support for complex emails
"""

import re
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from agent_platform.classification.models import EmailCategory, CATEGORY_IMPORTANCE_MAP


# ============================================================================
# PATTERN DEFINITIONS (10 Categories)
# ============================================================================

# 1. WICHTIG & TODO (Action Required) - Confidence: 0.90
WICHTIG_TODO_PATTERNS = {
    'subject': [
        r'\?$',  # Question mark at end
        r'bitte um rückmeldung',
        r'action required',
        r'entscheidung',
        r'dringend',
        r'urgent',
        r'asap',
        r'rückruf',
        r'call.*back',
        r'antwort.*bis',
        r'response.*by',
        r'deadline',
        r'frist',
        r'zu erledigen',
        r'todo',
        r'aufgabe',
        r'task',
    ],
    'body': [
        r'bitte.*antworten',
        r'please.*respond',
        r'deine meinung',
        r'your opinion',
        r'brauch.*feedback',
        r'need.*feedback',
        r'kannst du.*\?',
        r'can you.*\?',
        r'could you.*\?',
        r'würdest du.*\?',
        r'entscheidung treffen',
        r'make.*decision',
        r'bitte bestätigen',
        r'please confirm',
        r'warten auf',
        r'waiting for',
    ],
}

# 2. TERMINE & EINLADUNGEN (Calendar/Events) - Confidence: 0.95
TERMINE_PATTERNS = {
    'subject': [
        r'einladung',
        r'invitation',
        r'termin',
        r'appointment',
        r'meeting',
        r'besprechung',
        r'calendar',
        r'kalender',
        r'\d{1,2}\.\d{1,2}\.\d{4}',  # Date (DD.MM.YYYY)
        r'\d{1,2}/\d{1,2}/\d{4}',    # Date (MM/DD/YYYY)
        r'veranstaltung',
        r'event',
        r'conference',
        r'konferenz',
        r'webinar',
        r'workshop',
    ],
    'body': [
        r'wann:.*\d{2}:\d{2}',  # Time (when: HH:MM)
        r'when:.*\d{1,2}:\d{2}',
        r'zum kalender hinzufügen',
        r'add to calendar',
        r'save the date',
        r'teilnehmen',
        r'attend',
        r'meeting link',
        r'zoom.*meeting',
        r'teams.*meeting',
        r'rsvp',
    ],
    'attachments': [r'\.ics$'],  # iCal calendar files
}

# 3. FINANZEN & RECHNUNGEN (Finance/Invoices) - Confidence: 0.92
FINANZEN_PATTERNS = {
    'subject': [
        r'rechnung',
        r'invoice',
        r'payment',
        r'zahlung',
        r'überweisung',
        r'transfer',
        r'mahnung',
        r'reminder.*payment',
        r'kontoauszug',
        r'bank statement',
        r'versicherung',
        r'insurance',
        r'beitrag',
        r'premium',
        r'steuer',
        r'tax',
    ],
    'body': [
        r'betrag.*€',
        r'amount.*€',
        r'rechnungsnummer',
        r'invoice.*number',
        r'fällig.*\d{2}\.\d{2}',
        r'due.*\d{1,2}/\d{1,2}',
        r'iban',
        r'bic',
        r'swift',
        r'zahlungseingang',
        r'payment received',
        r'offene.*rechnung',
        r'outstanding.*invoice',
    ],
    'attachments': [r'rechnung.*\.pdf', r'invoice.*\.pdf'],
    'sender': [r'billing@', r'finance@', r'rechnung@', r'invoices?@'],
}

# 4. BESTELLUNGEN & VERSAND (Orders/Shipping) - Confidence: 0.90
BESTELLUNGEN_PATTERNS = {
    'subject': [
        r'bestellung',
        r'order',
        r'auftragsbestätigung',
        r'order confirmation',
        r'versand',
        r'shipping',
        r'shipped',
        r'tracking',
        r'sendungsverfolgung',
        r'lieferung',
        r'delivery',
        r'paket',
        r'package',
        r'ausgeliefert',
        r'delivered',
    ],
    'body': [
        r'bestellnummer',
        r'order.*\#?\d+',
        r'tracking.*nummer',
        r'tracking.*number',
        r'sendungsnummer',
        r'wird.*geliefert',
        r'will.*delivered',
        r'unterwegs',
        r'on.*way',
        r'voraussichtliche.*lieferung',
        r'estimated.*delivery',
        r'zustellung.*\d{2}\.\d{2}',
    ],
    'sender': [
        r'order@',
        r'shop@',
        r'noreply@.*shop',
        r'noreply@.*store',
        r'shipping@',
        r'versand@',
    ],
}

# 5. JOB & PROJEKTE (Business/Projects) - Confidence: 0.85
JOB_PROJEKTE_PATTERNS = {
    'subject': [
        r'projekt',
        r'project',
        r'kunde',
        r'client',
        r'customer',
        r'angebot',
        r'proposal',
        r'quotation',
        r'präsentation',
        r'presentation',
        r'status.*update',
        r'progress.*report',
        r'quarterly',
        r'quartal',
    ],
    'body': [
        r'deadline',
        r'meilenstein',
        r'milestone',
        r'sprint',
        r'feature',
        r'bug',
        r'ticket',
        r'review',
        r'pull request',
        r'merge request',
        r'deployment',
        r'release',
        r'rollout',
    ],
    'sender': [
        r'.*@(client|kunde|customer)',
        r'project@',
        r'team@',
    ],
}

# 6. VERTRÄGE, BEHÖRDEN & OFFIZIELLES (Contracts/Official) - Confidence: 0.95
VERTRAEGE_PATTERNS = {
    'subject': [
        r'vertrag',
        r'contract',
        r'vereinbarung',
        r'agreement',
        r'behörde',
        r'authority',
        r'amt',
        r'office',
        r'meldebescheinigung',
        r'certificate',
        r'steuerbescheid',
        r'tax.*assessment',
        r'stadtwerke',
        r'utilities',
        r'vermieter',
        r'landlord',
        r'mietvertrag',
        r'lease',
        r'rental.*agreement',
        r'gerichtlich',
        r'court',
        r'anwalt',
        r'lawyer',
        r'attorney',
    ],
    'body': [
        r'unterschrift',
        r'signature',
        r'rechtlich',
        r'legal',
        r'gesetzlich',
        r'statutory',
        r'aktenzeichen',
        r'case.*number',
        r'reference.*number',
        r'frist.*\d{2}\.\d{2}',
        r'deadline.*\d{1,2}/\d{1,2}',
        r'verbindlich',
        r'binding',
    ],
    'sender': [
        r'.*@(stadt|city|amt|office|behoerde|authority|gericht|court)',
        r'official@',
        r'legal@',
        r'rechtsabteilung@',
    ],
}

# 7. PERSÖNLICHE KOMMUNIKATION (Personal) - Confidence: 0.80
PERSOENLICH_PATTERNS = {
    'subject': [
        r'hallo.*!',
        r'hey',
        r'hi\s+[A-Z]',  # "Hi John"
        r'liebe.*grüße',
        r'best.*regards',
        r'alles.*gute',
        r'happy.*birthday',
        r'geburtstag',
        r'birthday',
        r'gratulation',
        r'congratulations',
        r'familie',
        r'family',
    ],
    'body': [
        r'liebe.*grüße',
        r'herzliche.*grüße',
        r'best.*wishes',
        r'freund',
        r'friend',
        r'treffen.*wir.*uns',
        r'lets.*meet',
        r'coffee',
        r'kaffee',
        r'dinner',
        r'abendessen',
    ],
    'sender': [
        # Freemail providers (often personal)
        r'@gmail\.com',
        r'@gmx\.',
        r'@web\.de',
        r'@yahoo\.',
        r'@outlook\.',
        r'@hotmail\.',
    ],
}

# 8. NEWSLETTER & INFOS (Newsletters) - Confidence: 0.85
NEWSLETTER_PATTERNS = {
    'subject': [
        r'newsletter',
        r'rundbrief',
        r'weekly.*update',
        r'wöchentlicher.*bericht',
        r'monthly.*digest',
        r'monatlicher.*überblick',
        r'this week in',
        r'diese woche',
        r'roundup',
        r'zusammenfassung',
        r'neue.*artikel',
        r'new.*articles',
        r'blog.*update',
    ],
    'body': [
        r'unsubscribe',
        r'abbestellen',
        r'abmelden',
        r'manage.*preferences',
        r'einstellungen.*verwalten',
        r'view.*in.*browser',
        r'im.*browser.*ansehen',
        r'dieser.*newsletter',
        r'this.*newsletter',
    ],
    'headers': {
        'List-Unsubscribe': True,
        'Precedence': 'bulk',
    },
    'sender': [
        r'newsletter@',
        r'info@',
        r'news@',
        r'updates?@',
    ],
}

# 9. WERBUNG & PROMO (Marketing/Sales) - Confidence: 0.88
WERBUNG_PATTERNS = {
    'subject': [
        r'rabatt',
        r'discount',
        r'sale',
        r'angebot',
        r'offer',
        r'deal',
        r'\d+%.*off',
        r'\d+%.*rabatt',
        r'aktion',
        r'promotion',
        r'sonderpreis',
        r'special.*price',
        r'limited.*time',
        r'nur.*heute',
        r'only.*today',
        r'black.*friday',
        r'cyber.*monday',
        r'summer.*sale',
        r'winter.*sale',
    ],
    'body': [
        r'jetzt.*kaufen',
        r'buy.*now',
        r'shop.*now',
        r'jetzt.*bestellen',
        r'order.*now',
        r'nur.*noch.*\d+',  # "nur noch 5 Stück"
        r'only.*\d+.*left',
        r'sparen',
        r'save',
        r'günstig',
        r'cheap',
        r'exklusiv',
        r'exclusive',
    ],
    'headers': {
        'List-Unsubscribe': True,
    },
    'sender': [
        r'marketing@',
        r'promo@',
        r'sales@',
        r'angebote@',
        r'deals@',
    ],
}

# 10. SPAM / PHISHING (Spam) - Confidence: 0.95
SPAM_PATTERNS = {
    'subject': [
        r'gewinnspiel',
        r'gewonnen',
        r'you.*won',
        r'congratulations.*won',
        r'viagra',
        r'casino',
        r'lottery',
        r'free.*money',
        r'gratis.*geld',
        r'!!!+',
        r'\$+\$+\$+',
        r'RE:\s*RE:\s*RE:',  # Multiple RE:
        r'[A-Z]{10,}',  # Excessive caps
        r'nigerian.*prince',
        r'inheritance',
        r'erbe',
    ],
    'body': [
        r'click.*here.*urgent',
        r'verify.*account.*immediately',
        r'konto.*bestätigen.*sofort',
        r'suspended.*account',
        r'konto.*gesperrt',
        r'password.*expired',
        r'passwort.*abgelaufen',
        r'bitcoin',
        r'cryptocurrency',
        r'kryptowährung',
        r'get.*rich.*quick',
        r'schnell.*reich',
        r'million.*dollar',
        r'million.*euro',
    ],
    'sender': [
        r'.*@suspicious\.tld',
    ],
}


# ============================================================================
# PATTERN MATCHING FUNCTIONS
# ============================================================================

def check_category_patterns(
    category_name: str,
    patterns: Dict[str, Any],
    subject: str,
    body: str,
    sender: str,
    has_attachments: bool = False
) -> Dict[str, Any]:
    """
    Check if email matches patterns for a specific category.

    Args:
        category_name: Name of category (for logging)
        patterns: Pattern dictionary with subject/body/sender/attachments/headers keys
        subject: Email subject
        body: Email body
        sender: Sender email
        has_attachments: Whether email has attachments

    Returns:
        Dict with:
        - matches: bool (True if threshold met)
        - score: int (total match score)
        - matched_patterns: List[str] (what matched)
        - confidence: float (0.0-1.0)
    """
    text = f"{subject} {body}".lower()
    score = 0
    matched_patterns = []

    # Check subject patterns
    if 'subject' in patterns:
        for pattern_str in patterns['subject']:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(subject):
                score += 2  # Subject matches are strong signals
                matched_patterns.append(f"subject:{pattern_str}")

    # Check body patterns
    if 'body' in patterns:
        for pattern_str in patterns['body']:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(body):
                score += 1  # Body matches are moderate signals
                matched_patterns.append(f"body:{pattern_str}")

    # Check sender patterns
    if 'sender' in patterns:
        for pattern_str in patterns['sender']:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(sender):
                score += 2  # Sender matches are strong signals
                matched_patterns.append(f"sender:{pattern_str}")

    # Check attachment patterns
    if has_attachments and 'attachments' in patterns:
        # Note: This would need actual attachment filenames to work properly
        score += 1
        matched_patterns.append("has_attachments")

    # Determine if threshold met (score >= 3 for high confidence)
    threshold_met = score >= 3

    # Calculate confidence based on score
    # Score 0-2: Low confidence (0.2-0.6)
    # Score 3-4: Medium confidence (0.7-0.85)
    # Score 5+: High confidence (0.85-0.95)
    if score >= 5:
        confidence = 0.90
    elif score >= 4:
        confidence = 0.85
    elif score >= 3:
        confidence = 0.75
    elif score >= 2:
        confidence = 0.60
    elif score >= 1:
        confidence = 0.40
    else:
        confidence = 0.20

    return {
        'matches': threshold_met,
        'score': score,
        'matched_patterns': matched_patterns,
        'confidence': confidence,
    }


def classify_with_10_categories(
    email_id: str,
    subject: str,
    body: str,
    sender: str,
    has_attachments: bool = False
) -> Dict[str, Any]:
    """
    Classify email into 10 categories with primary + secondary detection.

    Returns:
        Dict with:
        - primary_category: str (main category)
        - secondary_categories: List[str] (0-3 additional categories)
        - primary_confidence: float (0.0-1.0)
        - importance_score: float (0.0-1.0, from CATEGORY_IMPORTANCE_MAP)
        - reasoning: str
        - all_scores: Dict[str, Dict] (scores for all categories)
    """

    # All pattern groups mapped to categories
    all_patterns = {
        'spam': SPAM_PATTERNS,
        'wichtig_todo': WICHTIG_TODO_PATTERNS,
        'termine': TERMINE_PATTERNS,
        'finanzen': FINANZEN_PATTERNS,
        'bestellungen': BESTELLUNGEN_PATTERNS,
        'job_projekte': JOB_PROJEKTE_PATTERNS,
        'vertraege': VERTRAEGE_PATTERNS,
        'persoenlich': PERSOENLICH_PATTERNS,
        'newsletter': NEWSLETTER_PATTERNS,
        'werbung': WERBUNG_PATTERNS,
    }

    # Check all categories
    category_scores = {}
    for category, patterns in all_patterns.items():
        result = check_category_patterns(
            category_name=category,
            patterns=patterns,
            subject=subject,
            body=body,
            sender=sender,
            has_attachments=has_attachments
        )
        category_scores[category] = result

    # Find primary category (highest score with threshold met)
    valid_categories = {
        cat: result
        for cat, result in category_scores.items()
        if result['matches']  # Only categories that met threshold
    }

    if not valid_categories:
        # No category met threshold - default to newsletter (neutral)
        return {
            'primary_category': 'newsletter',
            'secondary_categories': [],
            'primary_confidence': 0.30,
            'importance_score': CATEGORY_IMPORTANCE_MAP.get('newsletter', 0.40),
            'reasoning': "No clear patterns matched, defaulting to newsletter",
            'all_scores': category_scores,
        }

    # Sort by score descending
    sorted_categories = sorted(
        valid_categories.items(),
        key=lambda x: (x[1]['score'], x[1]['confidence']),
        reverse=True
    )

    # Primary = highest scoring category
    primary_cat, primary_result = sorted_categories[0]

    # Secondary = other categories with score >= 3 (max 3 additional)
    secondary_cats = [
        cat
        for cat, result in sorted_categories[1:4]  # Max 3 secondary
        if result['score'] >= 3
    ]

    # Get importance from primary category
    importance = CATEGORY_IMPORTANCE_MAP.get(primary_cat, 0.50)

    # Build reasoning
    primary_patterns = ', '.join(primary_result['matched_patterns'][:3])
    reasoning_parts = [f"Primary: {primary_cat} ({primary_patterns})"]
    if secondary_cats:
        reasoning_parts.append(f"Secondary: {', '.join(secondary_cats)}")
    reasoning = '; '.join(reasoning_parts)

    return {
        'primary_category': primary_cat,
        'secondary_categories': secondary_cats,
        'primary_confidence': primary_result['confidence'],
        'importance_score': importance,
        'reasoning': reasoning,
        'all_scores': category_scores,
    }


# ============================================================================
# TEST FUNCTION
# ============================================================================

if __name__ == "__main__":
    # Test with sample emails
    test_emails = [
        {
            'id': '1',
            'subject': 'Rechnung für Ihre Bestellung #12345',
            'body': 'Vielen Dank für Ihre Bestellung. Betrag: 49,99€. Rechnungsnummer: INV-2025-001.',
            'sender': 'billing@shop.de',
            'has_attachments': True,
        },
        {
            'id': '2',
            'subject': 'Bitte um Rückmeldung bis Freitag - Dringend',
            'body': 'Kannst du mir bitte bis Freitag Feedback geben? Ich brauch deine Entscheidung für das Projekt.',
            'sender': 'colleague@company.com',
            'has_attachments': False,
        },
        {
            'id': '3',
            'subject': '50% Rabatt - Nur heute! Limited Time Offer!!!',
            'body': 'Jetzt kaufen und sparen! Exklusives Angebot nur für Sie. Shop now!',
            'sender': 'marketing@onlineshop.com',
            'has_attachments': False,
        },
    ]

    print("=" * 80)
    print("10-CATEGORY RULE-BASED CLASSIFIER TEST")
    print("=" * 80)

    for email in test_emails:
        print(f"\n📧 Email {email['id']}: {email['subject'][:50]}...")
        print("-" * 80)

        result = classify_with_10_categories(
            email_id=email['id'],
            subject=email['subject'],
            body=email['body'],
            sender=email['sender'],
            has_attachments=email.get('has_attachments', False)
        )

        print(f"Primary: {result['primary_category']} (confidence: {result['primary_confidence']:.2f})")
        print(f"Importance: {result['importance_score']:.2f}")
        if result['secondary_categories']:
            print(f"Secondary: {', '.join(result['secondary_categories'])}")
        print(f"Reasoning: {result['reasoning']}")
