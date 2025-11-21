# 10-Category Email Classification System

**Status:** Phase 6 COMPLETE ✅

Comprehensive email classification with fine-grained categories, sender profiling, and natural language preference management.

## Overview

The 10-Category System replaces the previous 6-category classification with:
- **10 Fine-Grained Categories:** Specific email types for better organization
- **Primary + Secondary Classification:** Multi-dimensional categorization (1 primary + 0-3 secondary)
- **Sender Profile Management:** Whitelist/Blacklist, trust levels, category preferences
- **NLP Intent Parser:** Natural language preference input ("Alle Werbemails von Zalando muten")
- **Multi-Provider Support:** Gmail (multi-label) and IONOS (single-folder)

## 10 Email Categories

### Category Definitions

```python
from agent_platform.classification.models import EmailCategory, CATEGORY_IMPORTANCE_MAP

# 10 Categories with German names and importance scores:
CATEGORIES = {
    'wichtig_todo': 0.95,     # Important & ToDo - Action items, decisions, tasks
    'termine': 0.90,          # Appointments & Events - Calendar, meetings
    'vertraege': 0.95,        # Contracts & Official - Legal documents, authorities
    'finanzen': 0.85,         # Finance & Invoices - Payments, bills, transactions
    'bestellungen': 0.70,     # Orders & Shipping - Order confirmations, tracking
    'job_projekte': 0.80,     # Job & Projects - Business communication, customers
    'persoenlich': 0.75,      # Personal Communication - Family, friends
    'newsletter': 0.40,       # Newsletter & Info - Updates, content
    'werbung': 0.20,          # Marketing & Promo - Advertising, sales
    'spam': 0.05,             # Spam - Phishing, junk
}
```

### Category Usage Examples

- **wichtig_todo:** "Bitte um Rückmeldung bis Freitag", "Entscheidung erforderlich"
- **termine:** "Meeting morgen 14 Uhr", "Kalendereinladung"
- **vertraege:** "Vertrag zur Unterschrift", "Amtlicher Bescheid"
- **finanzen:** "Rechnung #12345", "Kontoauszug", "Zahlungserinnerung"
- **bestellungen:** "Bestellung versandt", "Tracking-Nummer: ABC123"
- **job_projekte:** "Projekt Update Q4", "Kundengespräch Protokoll"
- **persoenlich:** "Grüße aus dem Urlaub", "Familienfeier Einladung"
- **newsletter:** "Monatlicher Newsletter", "Produktupdates"
- **werbung:** "50% RABATT heute!", "Sonderangebot"
- **spam:** "Sie haben gewonnen!!!", "Klicken Sie hier"

## Primary + Secondary Categories

Emails can have:
- **1 Primary Category** (highest scoring category)
- **0-3 Secondary Categories** (other relevant categories with score ≥ 3)

### Example

```python
Email: "Meeting zur Rechnung nächste Woche"

Result:
{
    'primary_category': 'wichtig_todo',      # Main focus: Action required
    'secondary_categories': ['termine', 'finanzen'],  # Also about meeting & invoice
    'primary_confidence': 0.85,
    'importance_score': 0.95
}
```

### Provider-Specific Handling

**Gmail (Multi-Label):**
- Primary + Secondary categories all applied as Gmail labels
- Example: `['Important/ToDo', 'Events/Appointments', 'Finance/Invoices']`

**IONOS (IMAP Single-Folder):**
- Only primary category applied (IMAP limitation)
- Secondary categories acknowledged but not applied
- Example: Moved to `Important/ToDo` folder, secondary ignored

## Sender Profile Management

### Trust Levels

```python
from agent_platform.senders import SenderProfileService

profile_service = SenderProfileService()

# Whitelist sender (trust_level='trusted', boost confidence +0.10)
await profile_service.whitelist_sender(
    sender_email='boss@company.com',
    account_id='gmail_1'
)

# Blacklist sender (trust_level='blocked', force to spam)
await profile_service.blacklist_sender(
    sender_email='spam@example.com',
    account_id='gmail_1'
)

# Set custom trust level
await profile_service.set_trust_level(
    sender_email='unknown@example.com',
    account_id='gmail_1',
    trust_level='suspicious'  # Options: trusted, neutral, suspicious, blocked
)
```

### Category Preferences

```python
# Mute specific categories from sender (importance → 0.10)
await profile_service.mute_categories(
    sender_email='newsletter@techcrunch.com',
    account_id='gmail_1',
    categories=['newsletter', 'werbung']
)

# Allow only specific categories
await profile_service.allow_only_categories(
    sender_email='work@company.com',
    account_id='gmail_1',
    categories=['wichtig_todo', 'job_projekte', 'termine']
)

# Set preferred primary category (override classification)
await profile_service.set_preferred_category(
    sender_email='client@company.com',
    account_id='gmail_1',
    category='job_projekte'
)
```

### Preference Application Priority

1. **Blacklist Check** (Highest Priority)
   - If blacklisted or trust_level='blocked' → Force spam, confidence=0.99, importance=0.0

2. **Whitelist Boost**
   - If whitelisted or trust_level='trusted' → Confidence +0.10

3. **Trust Level Adjustment**
   - suspicious → Confidence -0.10
   - neutral → No change

4. **Category Muting**
   - If primary_category in muted_categories → importance=0.10, confidence -0.20

5. **Category Filtering**
   - If allowed_categories set → Remove non-allowed from secondary categories

6. **Preferred Category Override**
   - If preferred_primary_category set → Override primary_category

## NLP Intent Parser

Parse natural language preferences into structured actions.

### Supported Intents

```python
from agent_platform.senders import parse_nlp_intent, IntentExecutor

# Intent Types:
# - whitelist_sender
# - blacklist_sender
# - set_trust_level
# - mute_categories
# - allow_only_categories
# - remove_from_whitelist
# - remove_from_blacklist
# - unknown
```

### Usage Example

```python
# Step 1: Parse natural language
text = "Alle Werbemails von zalando.de ignorieren"

result = await parse_nlp_intent(
    text=text,
    account_id='gmail_1'
)

# Result:
# {
#     'parsed_intent': {
#         'intent_type': 'mute_categories',
#         'sender_domain': 'zalando.de',
#         'categories': ['werbung'],
#         'confidence': 0.92,
#         'reasoning': 'User wants to mute marketing emails from zalando.de',
#         'key_signals': ['Werbemails', 'ignorieren', 'zalando.de']
#     },
#     'suggested_actions': [
#         'Mute category "werbung" for sender zalando.de',
#         'Create UserPreferenceRule for future emails'
#     ],
#     'requires_confirmation': False  # High-risk actions require confirmation
# }

# Step 2: Execute intent
executor = IntentExecutor()
exec_result = await executor.execute(
    intent=result.parsed_intent,
    account_id='gmail_1',
    source_channel='gui_chat',
    confirmed=True
)

# Result:
# {
#     'success': True,
#     'message': 'Successfully muted category "werbung" for zalando.de'
# }
```

### NLP Examples (German)

```python
# Whitelist
"Alle Emails von boss@company.com sind wichtig"
→ whitelist_sender, trust_level='trusted'

# Blacklist
"Blockiere alle Mails von spam@example.com"
→ blacklist_sender, trust_level='blocked'

# Mute Categories
"Newsletter von techcrunch.com muten"
→ mute_categories, categories=['newsletter']

# Domain-Based
"Alle Werbemails von zalando.de in Werbung verschieben"
→ mute_categories or allow_only_categories, sender_domain='zalando.de'

# Allow Only
"Von work@company.com nur wichtige Emails und Termine erlauben"
→ allow_only_categories, categories=['wichtig_todo', 'termine']
```

## Rule-Based Classification

Pattern-based classification with ~180 rules across 10 categories.

### Implementation

```python
from agent_platform.classification.agents.rule_agent_10cat import classify_with_10_categories

result = classify_with_10_categories(
    email_id='msg_123',
    subject='Bitte um Rückmeldung bis Freitag',
    body='Können Sie mir die Zahlen bis Freitag schicken?',
    sender='boss@company.com',
    has_attachments=False
)

# Result:
# {
#     'primary_category': 'wichtig_todo',
#     'secondary_categories': [],
#     'primary_confidence': 0.85,
#     'importance_score': 0.95,
#     'reasoning': 'Matched action-required patterns: "bitte um rückmeldung", deadline "bis Freitag"',
#     'all_scores': {
#         'wichtig_todo': {'score': 8, 'confidence': 0.85},
#         'termine': {'score': 1, 'confidence': 0.20},
#         ...
#     }
# }
```

### Pattern Examples

**wichtig_todo Patterns:**
- Subject: `\?$`, `bitte um rückmeldung`, `action required`, `dringend`, `urgent`, `asap`
- Body: `bitte.*antworten`, `kannst du.*\?`, `deadline`, `frist`

**termine Patterns:**
- Subject: `meeting`, `termin`, `calendar`, `einladung`, `invitation`, `veranstaltung`
- Body: `um \d{1,2}(:\d{2})? uhr`, `kalender`, `treffen`

**finanzen Patterns:**
- Subject: `rechnung`, `invoice`, `payment`, `zahlung`, `kontoauszug`, `überweisung`
- Body: `betrag`, `€`, `fällig`, `due date`, `zahlungserinnerung`

## Multi-Provider Support

### Gmail Handler (Multi-Label)

```python
from agent_platform.providers import GmailHandler

gmail_handler = GmailHandler()

# Applies primary + secondary categories as labels
result = await gmail_handler.apply_classification(
    email_record=email,
    account_id='gmail_1',
    primary_category='wichtig_todo',
    secondary_categories=['termine', 'finanzen'],
    importance_score=0.90,
    confidence=0.92
)

# Result:
# {
#     'success': True,
#     'labels_applied': ['Important/ToDo', 'Events/Appointments', 'Finance/Invoices'],
#     'archived': False  # High importance not archived
# }
```

**Category → Label Mapping:**
```python
CATEGORY_TO_LABEL_MAP = {
    'wichtig_todo': 'Important/ToDo',
    'termine': 'Events/Appointments',
    'finanzen': 'Finance/Invoices',
    'bestellungen': 'Orders/Shipping',
    'job_projekte': 'Work/Projects',
    'vertraege': 'Contracts/Official',
    'persoenlich': 'Personal',
    'newsletter': 'Newsletter',
    'werbung': 'Marketing/Promo',
    'spam': 'SPAM',
}
```

### IONOS Handler (Single-Folder)

```python
from agent_platform.providers import IonosHandler

ionos_handler = IonosHandler()

# Only applies primary category (IMAP limitation)
result = await ionos_handler.apply_classification(
    email_record=email,
    account_id='ionos_1',
    primary_category='wichtig_todo',
    secondary_categories=['termine', 'finanzen'],  # Ignored
    importance_score=0.90,
    confidence=0.92
)

# Result:
# {
#     'success': True,
#     'folder_applied': 'Important/ToDo',
#     'secondary_ignored': ['termine', 'finanzen'],  # Acknowledged but not applied
#     'moved': True
# }
```

**Category → Folder Mapping:**
Same as Gmail (CATEGORY_TO_FOLDER_MAP), but only primary applied.

## Database Schema

### Enhanced Tables

**ProcessedEmail:**
```python
primary_category = Column(String(100), nullable=True, index=True)
secondary_categories = Column(JSON, default=list)
category_confidence = Column(Float, nullable=True)
gmail_labels_applied = Column(JSON, default=list)
ionos_folder_applied = Column(String(200), nullable=True)
```

**SenderPreference (Enhanced):**
```python
trust_level = Column(String(50), default='neutral', index=True)  # trusted, neutral, suspicious, blocked
is_whitelisted = Column(Boolean, default=False, index=True)
is_blacklisted = Column(Boolean, default=False, index=True)
allowed_categories = Column(JSON, default=list)
muted_categories = Column(JSON, default=list)
preferred_primary_category = Column(String(100), nullable=True)
```

**UserPreferenceRule (New):**
```python
class UserPreferenceRule(Base):
    __tablename__ = "user_preference_rules"
    id = Column(Integer, primary_key=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    account_id = Column(String(100), nullable=False, index=True)
    applies_to = Column(String(50), nullable=False, index=True)  # 'sender_email', 'sender_domain', etc.
    pattern = Column(String(500), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # 'whitelist', 'blacklist', 'mute_categories', etc.
    created_via = Column(String(50), nullable=False, default='manual')  # 'manual', 'nlp_intent', 'learning'
    source_text = Column(Text, nullable=True)  # Original NLP text if created via NLP
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**NLPIntent (New):**
```python
class NLPIntent(Base):
    __tablename__ = "nlp_intents"
    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)
    source_text = Column(Text, nullable=False)
    source_channel = Column(String(50), nullable=False, default='gui_chat')  # 'gui_chat', 'voice_note', etc.
    parsed_intent = Column(JSON, nullable=False)
    intent_type = Column(String(100), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'completed', 'failed'
    user_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## API Endpoints

**NLP Intent API:**
```
POST /api/nlp/parse
POST /api/nlp/execute
GET  /api/nlp/rules?account_id=gmail_1
```

**Frontend API Routes:**
```
POST /api/preferences/parse
POST /api/preferences/execute
GET  /api/preferences/rules?account_id=gmail_1
```

## Testing

**Test Coverage:**
- `tests/classification/test_10_category_system.py` - 16 tests for rule classification
- `tests/senders/test_sender_profile_service.py` - 15 tests for profile management
- `tests/senders/test_nlp_intent_parser.py` - 20 tests for NLP parsing & execution
- `tests/providers/test_gmail_handler.py` - 10 tests for Gmail multi-label
- `tests/providers/test_ionos_handler.py` - 10 tests for IONOS single-folder
- `tests/integration/test_10_category_integration.py` - 12 integration tests

**Total:** ~83 new tests for 10-category system

## Migration from 6 to 10 Categories

```bash
# Run migration script
PYTHONPATH=. python migrations/add_10_category_system.py
```

**Category Mapping:**
```python
OLD_TO_NEW_CATEGORY_MAP = {
    "wichtig": "wichtig_todo",
    "action_required": "wichtig_todo",
    "nice_to_know": "newsletter",
    "newsletter": "newsletter",
    "system_notifications": "newsletter",
    "spam": "spam",
}
```

## Next Steps

**Phase 7: Advanced Features**
- Voice note integration (Plaud AI)
- ML-based classification (complement to rules + LLM)
- Advanced sender learning from user behavior
- Cross-category insights and recommendations
