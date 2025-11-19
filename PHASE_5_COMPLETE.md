# Phase 5: Review System ✅ COMPLETE

## Was Implementiert Wurde

### 1. ReviewQueueManager (`review/queue_manager.py` - 380+ Zeilen)
- ✅ **Add to Queue** für medium-confidence Classifications (0.6-0.85)
- ✅ **Get Pending Items** mit Sorting nach Importance
- ✅ **Mark as Reviewed** (approved/rejected/modified)
- ✅ **Queue Statistics** für Monitoring
- ✅ **Cleanup** alter reviewed Items
- ✅ **Items for Digest** mit time-based filtering

### 2. DailyDigestGenerator (`review/digest_generator.py` - 450+ Zeilen)
- ✅ **HTML Email Generation** mit professionellem Design
- ✅ **Plain Text Version** für Email Clients ohne HTML
- ✅ **Summary Statistics** (totals, category breakdown)
- ✅ **Action Buttons** (Approve, Reject, Modify)
- ✅ **Empty Digest** für "All Caught Up" Nachrichten
- ✅ **Responsive Design** mit CSS styling

### 3. ReviewHandler (`review/review_handler.py` - 450+ Zeilen)
- ✅ **Approve Classification** mit Feedback Tracking
- ✅ **Reject Classification** mit optional corrected category
- ✅ **Modify Classification** für User-Korrekturen
- ✅ **Batch Processing** für multiple Reviews
- ✅ **Integration mit FeedbackTracker** für Learning
- ✅ **Review Statistics** (approval rate, accuracy by category)

### 4. Test Suite (`tests/test_review_system.py` - 550+ Zeilen)
- ✅ **7 Comprehensive Tests**
- ✅ **100% Test Success Rate**
- ✅ Alle Features getestet (Queue, Digest, Reviews)

## Review System Workflow

### 1. Email Classification → Review Queue

```python
from agent_platform.classification import UnifiedClassifier
from agent_platform.review import ReviewQueueManager

classifier = UnifiedClassifier()
queue_manager = ReviewQueueManager()

# Classify email
result = await classifier.classify(email)

# Add to review queue if medium confidence
if queue_manager.should_add_to_review_queue(result):
    queue_manager.add_to_queue(
        email_id=email.email_id,
        account_id=email.account_id,
        subject=email.subject,
        sender=email.sender,
        snippet=email.snippet,
        classification=result,
    )
```

**Confidence Thresholds:**
- ≥ 0.85: Auto-action (no review needed)
- 0.6 - 0.85: Review queue (daily digest)
- < 0.6: Low confidence (manual review)

### 2. Daily Digest Generation

```python
from agent_platform.review import DailyDigestGenerator

digest_generator = DailyDigestGenerator()

# Generate digest for last 24 hours
digest = digest_generator.generate_digest(
    account_id="gmail_1",
    hours_back=24,
    limit=20,  # Max items per digest
)

# Access digest content
html_email = digest['html']    # HTML version for email
text_email = digest['text']    # Plain text version
summary = digest['summary']    # Statistics
items = digest['items']        # ReviewQueueItems
```

**Digest Features:**
- Professional HTML design with CSS
- Summary statistics (total items, category breakdown)
- Email previews with subject, sender, snippet
- Classification suggestions with reasoning
- Confidence bars (visual)
- Action buttons (Approve/Reject/Modify)
- "All Caught Up" message when empty

### 3. User Review Actions

```python
from agent_platform.review import ReviewHandler

review_handler = ReviewHandler()

# Approve classification
result = review_handler.approve_classification(
    item_id=123,
    user_feedback="Good classification, I replied to this",
)

# Reject and correct
result = review_handler.reject_classification(
    item_id=124,
    corrected_category="newsletter",
    user_feedback="This is actually a newsletter, not spam",
)

# Modify classification
result = review_handler.modify_classification(
    item_id=125,
    corrected_category="action_required",
    user_feedback="This is more urgent than suggested",
)
```

**What Happens on Review:**
1. ✅ Review queue item updated (status: approved/rejected/modified)
2. ✅ Feedback event tracked in database
3. ✅ Sender/domain preferences updated (EMA learning)
4. ✅ Optional: Action applied to email (label, archive, etc.)

### 4. Integration with Feedback Tracking

Der ReviewHandler integriert automatisch mit dem FeedbackTracker:

```python
# User approves "wichtig" classification
review_handler.approve_classification(item_id=123)

# → Internally:
# 1. Infers action type from category ("wichtig" → "replied")
# 2. Tracks feedback event with inferred importance (0.85)
# 3. Updates sender preference:
#    - total_emails += 1
#    - total_replies += 1
#    - reply_rate recalculated
#    - average_importance updated via EMA
```

**Action Inference Logic:**

| Category | Approved Action | Rejected Action |
|----------|----------------|-----------------|
| **wichtig** | replied (0.85) | archived (0.40) |
| **action_required** | replied (0.85) | archived (0.40) |
| **nice_to_know** | archived (0.40) | archived (0.40) |
| **newsletter** | archived (0.40) | deleted (0.05) |
| **spam** | deleted (0.05) | archived (0.40) |

## Test-Ergebnisse (7/7 = 100%)

**Test 1: Add to Queue**
```
✅ Item added with correct attributes
✅ Status: pending
✅ Successfully retrieved from queue
```

**Test 2: Get Pending Items**
```
✅ 3 items added with different importance
✅ Items correctly ordered by importance (DESC)
✅ High importance first, low importance last
```

**Test 3: Daily Digest Generation**
```
✅ HTML digest generated (11,000+ characters)
✅ Contains all required elements:
   - Title ("Email Review Digest")
   - All categories (wichtig, action_required, newsletter)
   - Approve/Reject buttons
   - Summary statistics
```

**Test 4: Approve Classification**
```
✅ Status updated to "approved"
✅ User approved = True
✅ Feedback event created (action: replied)
✅ Sender preference updated (importance: 0.85)
```

**Test 5: Reject Classification**
```
✅ Status updated to "modified" (because corrected_category provided)
✅ User approved = False
✅ Corrected category saved
✅ Feedback event created (action: archived)
✅ Sender preference updated (importance: 0.40)
```

**Test 6: Modify Classification**
```
✅ Status set to "modified"
✅ Corrected category saved
✅ Feedback event created (action: replied for action_required)
✅ Inferred importance: 0.85
```

**Test 7: Queue Statistics**
```
✅ Correct counts:
   - Total: 5
   - Approved: 3
   - Modified: 2
   - Rejected: 0
✅ Review statistics:
   - Approval rate: 80%
   - Modification rate: 40%
```

## Usage Examples

### Basic Usage - Add to Review Queue

```python
from agent_platform.review import ReviewQueueManager
from agent_platform.classification import ClassificationResult

queue_manager = ReviewQueueManager()

# Classification result from unified classifier
classification = ClassificationResult(
    category="wichtig",
    importance=0.75,
    confidence=0.72,  # Medium confidence → review queue
    reasoning="Email from boss about project deadline",
    layer_used="llm",
    processing_time_ms=150.0,
)

# Add to queue
item = queue_manager.add_to_queue(
    email_id="msg_123",
    account_id="gmail_1",
    subject="Project Deadline Update",
    sender="boss@company.com",
    snippet="We need to discuss the project timeline...",
    classification=classification,
)

print(f"Added to queue: {item.id}")
print(f"Status: {item.status}")  # "pending"
```

### Generate Daily Digest Email

```python
from agent_platform.review import DailyDigestGenerator

digest_generator = DailyDigestGenerator()

# Generate digest for all accounts
digest = digest_generator.generate_digest(
    hours_back=24,    # Last 24 hours
    limit=20,         # Max 20 items
)

# Send email with digest
if digest['summary']['total_items'] > 0:
    send_email(
        to="user@example.com",
        subject=f"Daily Review Digest ({digest['summary']['total_items']} items)",
        html=digest['html'],
        text=digest['text'],
    )
else:
    print("No items to review - all caught up!")
```

### Process User Review

```python
from agent_platform.review import ReviewHandler

review_handler = ReviewHandler()

# User clicks "Approve" button in digest email
result = review_handler.approve_classification(
    item_id=123,
    user_feedback="Correct classification",
)

print(f"Status: {result['item'].status}")  # "approved"
print(f"Feedback tracked: {result['feedback_event'].action_type}")  # "replied"

# User clicks "Reject" and corrects
result = review_handler.reject_classification(
    item_id=124,
    corrected_category="newsletter",
    user_feedback="This is a newsletter, not spam",
)

print(f"Corrected: {result['item'].user_corrected_category}")  # "newsletter"
```

### Batch Review Processing

```python
from agent_platform.review import ReviewHandler

review_handler = ReviewHandler()

# Process multiple reviews at once
reviews = [
    {"item_id": 123, "action": "approve"},
    {"item_id": 124, "action": "reject", "corrected_category": "spam"},
    {"item_id": 125, "action": "modify", "corrected_category": "action_required"},
]

result = review_handler.process_batch_reviews(reviews)

print(f"Total: {result['total']}")
print(f"Successful: {result['successful']}")
print(f"Failed: {result['failed']}")
```

### Queue Statistics

```python
from agent_platform.review import ReviewQueueManager

queue_manager = ReviewQueueManager()

# Get statistics
stats = queue_manager.get_queue_statistics(account_id="gmail_1")

print(f"Total items: {stats['total_items']}")
print(f"Pending: {stats['pending']}")
print(f"Approved: {stats['approved']}")
print(f"Rejected: {stats['rejected']}")
print(f"Modified: {stats['modified']}")

# By category
for category, count in stats['by_category'].items():
    print(f"{category}: {count}")

# Average age
print(f"Avg age: {stats['avg_age_hours']:.1f} hours")

# Pretty print
queue_manager.print_queue_summary(account_id="gmail_1")
```

### Review Statistics & Accuracy

```python
from agent_platform.review import ReviewHandler

review_handler = ReviewHandler()

# Get review statistics (last 30 days)
stats = review_handler.get_review_statistics(account_id="gmail_1")

print(f"Total reviewed: {stats['total_reviewed']}")
print(f"Approval rate: {stats['approval_rate']:.0%}")
print(f"Modification rate: {stats['modification_rate']:.0%}")

# Accuracy by category
for category, category_stats in stats['accuracy_by_category'].items():
    print(f"{category}:")
    print(f"  Accuracy: {category_stats['accuracy']:.0%}")
    print(f"  Correct: {category_stats['correct']}/{category_stats['total']}")

# Pretty print
review_handler.print_review_summary(account_id="gmail_1")
```

## Integration mit Scheduler (Future)

Der Review System sollte täglich laufen:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agent_platform.review import DailyDigestGenerator

scheduler = AsyncIOScheduler()

def send_daily_digest():
    """Send daily digest email to user."""
    digest_generator = DailyDigestGenerator()

    # Generate digest for last 24 hours
    digest = digest_generator.generate_digest(hours_back=24, limit=20)

    if digest['summary']['total_items'] > 0:
        # Send email to user
        send_email(
            to="user@example.com",
            subject=f"Daily Review Digest ({digest['summary']['total_items']} items)",
            html=digest['html'],
            text=digest['text'],
        )
        print(f"Sent digest with {digest['summary']['total_items']} items")
    else:
        print("No items to review - skipping digest")

# Run every day at 9 AM
scheduler.add_job(
    send_daily_digest,
    trigger='cron',
    hour=9,
    minute=0,
    id='daily_review_digest'
)

scheduler.start()
```

## Email Action Application (Future)

Das `_apply_action_to_email()` in ReviewHandler ist aktuell ein Placeholder.
Zukünftige Integration mit Email Tools:

```python
def _apply_action_to_email(
    self,
    item: ReviewQueueItem,
    corrected_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply action to the actual email (label, archive, etc.)."""
    category = corrected_category or item.suggested_category

    # Map category to Gmail label
    label_map = {
        "wichtig": "Important",
        "action_required": "Action Required",
        "newsletter": "Newsletters",
        "spam": "Spam",
        "nice_to_know": "Low Priority",
        "system_notifications": "System",
    }

    label = label_map.get(category, "Uncategorized")

    # Apply label via Gmail API
    if item.account_id.startswith("gmail_"):
        from modules.email.tools.gmail_tools import apply_label
        apply_label(item.account_id, item.email_id, label)

        return {
            "applied": True,
            "action": "label_applied",
            "label": label,
            "email_id": item.email_id,
        }

    # For IMAP accounts (Ionos)
    else:
        from modules.email.tools.ionos_tools import move_to_folder
        folder = label_map.get(category, "INBOX")
        move_to_folder(item.account_id, item.email_id, folder)

        return {
            "applied": True,
            "action": "moved_to_folder",
            "folder": folder,
            "email_id": item.email_id,
        }
```

## Datei-Übersicht

**Neu erstellt:**
1. `agent_platform/review/__init__.py`
2. `agent_platform/review/queue_manager.py` (380+ Zeilen)
3. `agent_platform/review/digest_generator.py` (450+ Zeilen)
4. `agent_platform/review/review_handler.py` (450+ Zeilen)
5. `tests/test_review_system.py` (550+ Zeilen)
6. `PHASE_5_COMPLETE.md` (diese Datei)

**Gesamt: ~1,900+ neue Zeilen**

## Status

✅ **Phase 5: COMPLETE**
- ✅ ReviewQueueManager (add, retrieve, update, statistics)
- ✅ DailyDigestGenerator (HTML + text emails)
- ✅ ReviewHandler (approve/reject/modify + feedback integration)
- ✅ Integration mit FeedbackTracker für Learning
- ✅ Comprehensive Test Suite (7/7 = 100%)
- ✅ Queue & Review Statistics
- 🔄 Email Action Application (placeholder - future integration)

**Kern-System komplett! (Phases 1-5)**
- Phase 1: ✅ Foundation + Ollama Integration
- Phase 2: ✅ Rule + History Layers
- Phase 3: ✅ LLM Layer + Unified Classifier
- Phase 4: ✅ Feedback Tracking System
- Phase 5: ✅ Review System (Daily Digest)

**Noch zu tun:**
- Phase 6: Orchestrator Integration
- Phase 7: Testing & Tuning

---

**Next**: Phase 6 - Orchestrator Integration (Email Processing Pipeline)
