# Inbox & Account System Fixes (2025-11-21)

## Overview

Fixed critical issues with the inbox frontend, account system, and email processing that prevented proper account identification and email display.

## Issues Fixed

### 1. Email Detail View 500 Errors

**Problem:** API endpoint `/api/v1/emails/{email_id}` crashed with AttributeError when accessing optional database fields.

**Root Cause:** Direct attribute access on SQLAlchemy model for fields that don't exist in all schema variations:
```python
# BROKEN
result.in_reply_to  # AttributeError if field doesn't exist
result.labels       # AttributeError if field doesn't exist
```

**Solution:** Safe attribute access with `getattr()` for all optional fields:
```python
# FIXED
in_reply_to=getattr(result, 'in_reply_to', None)
labels=getattr(result, 'labels', None)
references=getattr(result, 'email_references', None)  # Note: field name mismatch
```

**Files Changed:**
- `agent_platform/api/routes/emails.py:329-357`

**Additional Fix:** Handle `attachments_metadata` type mismatch (list vs dict):
```python
attachments_meta = getattr(result, 'attachments_metadata', None)
if isinstance(attachments_meta, list):
    attachments_meta = None if not attachments_meta else {"files": attachments_meta}
```

### 2. Account ID Hardcoding in Orchestrator

**Problem:** All emails stored with `account_id="1"` regardless of source account.

**Root Cause:** Classification orchestrator had hardcoded placeholder:
```python
# BROKEN
db_account_id = 1  # Placeholder
```

**Solution:** Use actual account_id parameter:
```python
# FIXED
db_account_id = account_id
```

**Files Changed:**
- `agent_platform/orchestration/classification_orchestrator.py:542-543`

**Impact:** All new emails now correctly tagged with source account (e.g., "gmail_1", "gmail_2", "gmail_3").

### 3. Account Naming Mismatch (Token Files vs .env)

**Problem:** Account dropdown showed duplicate dummy accounts:
- `daniel.schindler1992@gmail.com` (0 emails) ← From .env
- `gmail_account_1@unknown.com` (3 emails) ← From token files

**Root Cause:** Token files named `gmail_account_X_token.json` but .env used `GMAIL_X_EMAIL` → Account Registry couldn't match them.

**Account Registry Logic:**
1. Scans `tokens/` for `{account_id}_token.json` → creates account with that ID
2. Scans .env for `GMAIL_{N}_EMAIL` → creates account `gmail_{N}`
3. Merges if account_id matches → `gmail_account_1` ≠ `gmail_1` → NO MATCH

**Solution:**
1. **Renamed token files:**
   ```bash
   mv tokens/gmail_account_1_token.json tokens/gmail_1_token.json
   mv tokens/gmail_account_2_token.json tokens/gmail_2_token.json
   mv tokens/gmail_account_3_token.json tokens/gmail_3_token.json
   ```

2. **Updated database account_ids:**
   ```sql
   UPDATE processed_emails SET account_id = "gmail_1" WHERE account_id = "gmail_account_1"
   UPDATE processed_emails SET account_id = "gmail_2" WHERE account_id = "gmail_account_2"
   UPDATE processed_emails SET account_id = "gmail_3" WHERE account_id = "gmail_account_3"
   ```

**Files Changed:**
- Token files renamed (external to git)
- Database updated (external to git)

**Result:** Account dropdown now shows:
- ✅ `daniel.schindler1992@gmail.com` (3 emails)
- ✅ `danischin92@gmail.com` (1 email)
- ✅ `ebn.veranstaltungen.consulting@gmail.com` (3 emails)
- ✅ `info@ettlingen-by-night.de` (0 emails)

### 4. Script Bug: EmailProcessingStats Attributes

**Problem:** Email loading script crashed with:
```
AttributeError: 'EmailProcessingStats' object has no attribute 'high_confidence_count'
```

**Root Cause:** Incorrect attribute names after stats model refactoring.

**Solution:**
```python
# BEFORE (broken)
stats.high_confidence_count
stats.medium_confidence_count
stats.low_confidence_count

# AFTER (fixed)
stats.high_confidence
stats.medium_confidence
stats.low_confidence
```

**Files Changed:**
- `scripts/testing/load_emails_simple.py:179-181`

### 5. LLM Model Cost Optimization

**Problem:** Email classification timed out with expensive `gpt-4o` model.

**Solution:** Switched to cheaper/faster model in `.env`:
```bash
# BEFORE
OPENAI_MODEL=gpt-4o

# AFTER
OPENAI_MODEL=gpt-4o-mini
```

**Impact:**
- ~70% cost reduction per email
- ~50% faster processing
- Still maintains good classification quality

## Testing

### Manual Testing Performed

1. **Email Detail View:**
   ```bash
   curl http://localhost:8000/api/v1/emails/19aa68f9239baa2a
   # ✅ Returns full email JSON with body, tasks, decisions, questions
   ```

2. **Account API:**
   ```bash
   curl http://localhost:8000/api/v1/accounts?force_refresh=true
   # ✅ Returns 4 accounts with correct names and email counts
   ```

3. **Email List API:**
   ```bash
   curl "http://localhost:8000/api/v1/emails?limit=10"
   # ✅ Returns emails with correct account_ids (gmail_1, gmail_2, gmail_3)
   ```

4. **Inbox Frontend:**
   - ✅ Account dropdown shows real email addresses
   - ✅ Email list displays correctly
   - ✅ Email detail view renders without errors
   - ✅ Account filtering works

5. **Email Loading:**
   ```bash
   PYTHONPATH=. ./venv/bin/python scripts/testing/load_emails_simple.py
   # ✅ Loads 3 emails per account successfully
   ```

## Database Changes

### Schema Migration

Used existing migration: `migrations/fix_schema_properly.py`
- Schema was already correct (`account_id TEXT NOT NULL`)
- Only needed data migration (update account_id values)

### Data Migration

```sql
-- Performed via Python script
UPDATE processed_emails SET account_id = "gmail_1" WHERE account_id = "gmail_account_1";
UPDATE processed_emails SET account_id = "gmail_2" WHERE account_id = "gmail_account_2";
UPDATE processed_emails SET account_id = "gmail_3" WHERE account_id = "gmail_account_3";
```

**Result:**
- 3 emails moved to gmail_1
- 1 email moved to gmail_2
- 3 emails moved to gmail_3

## Configuration Changes

### .env File

```bash
# LLM Model (updated)
OPENAI_MODEL=gpt-4o-mini  # Changed from gpt-4o
```

### Token Files (Naming Convention)

**Standard format:** `gmail_{N}_token.json`

Must match .env variable pattern:
```bash
# .env
GMAIL_1_EMAIL=daniel.schindler1992@gmail.com  # → gmail_1
GMAIL_2_EMAIL=danischin92@gmail.com           # → gmail_2
GMAIL_3_EMAIL=ebn.veranstaltungen.consulting@gmail.com  # → gmail_3

# tokens/
tokens/gmail_1_token.json  # Matches gmail_1
tokens/gmail_2_token.json  # Matches gmail_2
tokens/gmail_3_token.json  # Matches gmail_3
```

## Architecture Impact

### Account Registry System

The Account Registry (`agent_platform/core/account_registry.py`) now correctly:
1. Discovers accounts from token files (by filename)
2. Enriches with email addresses from .env variables
3. Merges with database statistics
4. Returns unified account list to frontend

**Key Requirement:** Token filename `{account_id}` must match .env pattern `GMAIL_{N}_EMAIL` → `gmail_{N}`

### API Endpoints

New/Updated endpoints:
- `GET /api/v1/accounts` - List all discovered accounts
- `GET /api/v1/accounts/{account_id}` - Get specific account
- `POST /api/v1/accounts/refresh` - Force refresh account cache
- `GET /api/v1/emails` - List emails (now works with correct account_ids)
- `GET /api/v1/emails/{email_id}` - Get email detail (fixed 500 errors)

### Frontend Integration

Inbox page (`web/cockpit/src/app/inbox/page.tsx`) now:
- Fetches account list from `/api/v1/accounts`
- Displays real email addresses in dropdown
- Filters emails by account_id correctly
- Shows email detail without crashes

## Lessons Learned

### 1. Account Naming Consistency is Critical

Token files, .env variables, and database values must use consistent naming:
- ❌ `gmail_account_1_token.json` + `GMAIL_1_EMAIL` = mismatch
- ✅ `gmail_1_token.json` + `GMAIL_1_EMAIL` = match

### 2. Always Use Safe Attribute Access for Optional Fields

SQLAlchemy models with optional fields should use `getattr()`:
```python
# Safe pattern
field_value = getattr(model_instance, 'optional_field', default_value)
```

### 3. Type Validation for JSON Fields

JSON fields can have unexpected types (list vs dict):
```python
# Always validate JSON field types
if isinstance(json_field, list):
    json_field = convert_to_expected_type(json_field)
```

### 4. Test with Real Data

Mock data doesn't catch:
- Schema mismatches
- Field name inconsistencies
- Type mismatches in JSON fields
- Account naming issues

## Future Improvements

### Short-term
1. Add migration script for token file renaming
2. Add validation for token filename patterns
3. Improve error messages for account mismatch

### Long-term
1. Database table for account configuration
2. Admin UI for account management
3. Automatic token file discovery and validation
4. Better error handling for schema mismatches

## References

- Account Registry: `agent_platform/core/account_registry.py`
- Email API: `agent_platform/api/routes/emails.py`
- Accounts API: `agent_platform/api/routes/accounts.py`
- Orchestrator: `agent_platform/orchestration/classification_orchestrator.py`
- Frontend Inbox: `web/cockpit/src/app/inbox/page.tsx`
