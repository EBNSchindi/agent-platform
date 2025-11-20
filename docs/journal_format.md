# Journal Format Specification

## Overview

Daily journals are generated from events and memory-objects to provide a human-readable summary of the day's email activities. Journals are stored in the database and can be exported to markdown files.

## File Structure

**Directory Layout:**
```
journals/
├── gmail_1/
│   ├── 2025-11-20.md
│   ├── 2025-11-21.md
│   └── 2025-11-22.md
├── gmail_2/
│   └── 2025-11-20.md
└── gmail_3/
    └── 2025-11-20.md
```

**Naming Convention:**
- Format: `{account_id}/{YYYY-MM-DD}.md`
- One journal per account per day
- Idempotent: generating twice returns same journal

## Markdown Structure

### Template

```markdown
# Daily Email Journal - {Day, Month DD, YYYY}

**Account:** {account_id}

## 📊 Daily Summary

- **Emails Processed:** {count}
- **Tasks Created:** {count}
- **Decisions Made:** {count}
- **Questions Answered:** {count}

### Email Breakdown by Category
- **{category}:** {count}
...

## 👥 Top Senders

- **{sender_email}:** {count} email(s)
...

## ⚠️ Important Items

### 📋 High Priority Tasks

- **[PRIORITY]** {task description} (Due: {deadline})
...

### 🤔 Urgent Decisions

- **[URGENCY]** {decision question}
...

### ❓ Urgent Questions

- **[URGENCY]** {question}
...

---

*Generated on {timestamp} UTC*
```

### Sections Explained

#### 1. Header
- **Title**: Date in human-readable format
- **Account**: Account ID for context

#### 2. Daily Summary
- **Emails Processed**: Total emails classified today
- **Tasks Created**: New tasks extracted from emails
- **Decisions Made**: Decisions that were resolved
- **Questions Answered**: Questions that were answered
- **Email Breakdown**: Count by category (wichtig, action_required, newsletter, etc.)

#### 3. Top Senders
- Lists senders with most emails today
- Aggregated across all email types
- Sorted by count descending
- Maximum 10 senders shown

#### 4. Important Items
- **High Priority Tasks**: Tasks with priority='high' or 'urgent'
- **Urgent Decisions**: Decisions with urgency='high' or 'urgent'
- **Urgent Questions**: Questions with urgency='high' or 'urgent'
- Only shown if items exist

## Example Journal

```markdown
# Daily Email Journal - Wednesday, November 20, 2025

**Account:** gmail_1

## 📊 Daily Summary

- **Emails Processed:** 47
- **Tasks Created:** 12
- **Decisions Made:** 3
- **Questions Answered:** 5

### Email Breakdown by Category
- **wichtig:** 15
- **action_required:** 8
- **nice_to_know:** 18
- **newsletter:** 5
- **spam:** 1

## 👥 Top Senders

- **boss@company.com:** 8 email(s)
- **team-lead@company.com:** 5 email(s)
- **project-manager@company.com:** 4 email(s)
- **notifications@github.com:** 3 email(s)
- **noreply@linkedin.com:** 3 email(s)

## ⚠️ Important Items

### 📋 High Priority Tasks

- **[HIGH]** Complete Q4 budget report (Due: 2025-11-22)
- **[URGENT]** Review contract changes before signing (Due: 2025-11-21)
- **[HIGH]** Prepare slides for client presentation (Due: 2025-11-23)

### 🤔 Urgent Decisions

- **[HIGH]** Approve or reject new hire candidate
- **[URGENT]** Choose vendor for cloud migration project

### ❓ Urgent Questions

- **[HIGH]** Can you attend Friday's strategy meeting?
- **[HIGH]** Do you approve the new marketing budget allocation?

---

*Generated on 2025-11-20 20:05:32 UTC*
```

## Database Schema

Journals are stored in the `journal_entries` table:

```python
class JournalEntry(Base):
    __tablename__ = "journal_entries"

    journal_id: int              # Primary key
    account_id: str              # Account identifier
    date: datetime               # Journal date (YYYY-MM-DD)
    title: str                   # Generated title
    content_markdown: str        # Full markdown content
    summary: JSON                # Statistics dict
    top_senders: JSON           # List of top senders
    important_items: JSON       # Important tasks/decisions/questions
    status: str                 # 'generated', 'reviewed'
    reviewed_at: datetime       # When user reviewed (optional)
    generation_event_id: int    # Link to JOURNAL_GENERATED event
    created_at: datetime
    updated_at: datetime
```

## Event Integration

Each journal generation creates a `JOURNAL_GENERATED` event:

```python
{
    "event_type": "JOURNAL_GENERATED",
    "account_id": "gmail_1",
    "email_id": None,  # Not tied to specific email
    "payload": {
        "journal_id": 123,
        "date": "2025-11-20",
        "emails_processed": 47,
        "tasks_created": 12,
        "decisions_made": 3,
        "questions_answered": 5
    },
    "processing_time_ms": 1234.5
}
```

## Usage

### Generate Journal Manually

```bash
# Generate for today (gmail_1)
python scripts/operations/run_journal_generator.py gmail_1

# Generate for specific date
python scripts/operations/run_journal_generator.py gmail_1 --date 2025-11-20

# Generate for all accounts
python scripts/operations/run_journal_generator.py --all

# Export to markdown file
python scripts/operations/run_journal_generator.py gmail_1 --export

# Specify output directory
python scripts/operations/run_journal_generator.py gmail_1 --export --output-dir ./my_journals
```

### Generate Programmatically

```python
from agent_platform.journal import JournalGenerator
from datetime import datetime

generator = JournalGenerator()

# Generate journal
journal = await generator.generate_daily_journal(
    account_id="gmail_1",
    date=datetime(2025, 11, 20)
)

# Export to file
filepath = generator.export_to_file(
    journal_entry=journal,
    account_id="gmail_1",
    output_dir="journals"
)

print(f"Journal exported to: {filepath}")
```

### Scheduled Generation

Journals are automatically generated daily at configured time (default: 8 PM):

```bash
# Run scheduler
python scripts/operations/run_scheduler.py

# Configuration (.env)
JOURNAL_GENERATION_HOUR=20  # 8 PM (24-hour format)
```

## Customization

### Filtering Important Items

Important items are filtered by:
- **Tasks**: priority in ['high', 'urgent']
- **Decisions**: urgency in ['high', 'urgent']
- **Questions**: urgency in ['high', 'urgent']

### Top Senders Limit

Maximum 10 senders shown, sorted by email count descending.

### Date Range

Journals aggregate data from:
- Start: 00:00:00 on the specified date
- End: 23:59:59 on the specified date

## Future Enhancements

Potential future features:
- **Weekly journals**: Aggregate across 7 days
- **Monthly journals**: Aggregate across 30 days
- **Custom templates**: User-configurable markdown templates
- **Email delivery**: Send journals via email
- **Analytics**: Trends, productivity metrics
- **Comparison**: Period-over-period analysis
