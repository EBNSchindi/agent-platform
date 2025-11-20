-- Migration 004: Add Storage Level Strategy, Thread Handling, and Attachments
-- Date: 2025-11-20
-- Description: Extends ProcessedEmail with storage_level, thread fields, attachment fields,
--              user correction tracking, and Gmail action tracking. Creates new Attachments table.

-- ============================================================================
-- ALTER processed_emails TABLE - Add new columns
-- ============================================================================

-- Storage strategy (Datenhaltungs-Strategie)
ALTER TABLE processed_emails ADD COLUMN storage_level VARCHAR(20) NOT NULL DEFAULT 'full';
-- Values: 'full' (body+attachments+extraction), 'summary' (summary only), 'minimal' (metadata only)

-- Content storage (conditional based on storage_level)
ALTER TABLE processed_emails ADD COLUMN summary TEXT;  -- LLM-generated summary (2-3 sentences)
ALTER TABLE processed_emails ADD COLUMN body_text TEXT;  -- Full email body (text) - only for storage_level='full'
ALTER TABLE processed_emails ADD COLUMN body_html TEXT;  -- Full email body (HTML) - only for storage_level='full'

-- Thread handling
ALTER TABLE processed_emails ADD COLUMN thread_id VARCHAR(200);  -- Gmail thread ID
ALTER TABLE processed_emails ADD COLUMN thread_summary TEXT;  -- LLM-generated thread context summary
ALTER TABLE processed_emails ADD COLUMN thread_position INTEGER;  -- Position in thread (1=first, 2=second, etc.)
ALTER TABLE processed_emails ADD COLUMN is_thread_start BOOLEAN DEFAULT 0;  -- True if this is the first email in thread

-- Attachment metadata
ALTER TABLE processed_emails ADD COLUMN has_attachments BOOLEAN DEFAULT 0;  -- True if email has attachments
ALTER TABLE processed_emails ADD COLUMN attachment_count INTEGER DEFAULT 0;  -- Number of attachments
ALTER TABLE processed_emails ADD COLUMN attachments_metadata JSON;  -- List of attachment info: [{filename, size, mime_type, stored}]

-- User correction tracking (for feedback loop)
ALTER TABLE processed_emails ADD COLUMN user_corrected BOOLEAN DEFAULT 0;  -- True if user corrected classification
ALTER TABLE processed_emails ADD COLUMN user_corrected_at DATETIME;  -- When user made correction
ALTER TABLE processed_emails ADD COLUMN original_category VARCHAR(100);  -- Original category before user correction
ALTER TABLE processed_emails ADD COLUMN original_confidence FLOAT;  -- Original confidence before user correction

-- Gmail action tracking
ALTER TABLE processed_emails ADD COLUMN gmail_label_applied VARCHAR(200);  -- Label that was applied (e.g., "🔴 Wichtig")
ALTER TABLE processed_emails ADD COLUMN gmail_archived BOOLEAN DEFAULT 0;  -- True if email was archived
ALTER TABLE processed_emails ADD COLUMN gmail_marked_read BOOLEAN DEFAULT 0;  -- True if email was marked as read

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_processed_emails_storage_level ON processed_emails(storage_level);
CREATE INDEX IF NOT EXISTS idx_processed_emails_thread_id ON processed_emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_processed_emails_has_attachments ON processed_emails(has_attachments);
CREATE INDEX IF NOT EXISTS idx_processed_emails_user_corrected ON processed_emails(user_corrected);

-- ============================================================================
-- CREATE attachments TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attachment_id VARCHAR(36) UNIQUE NOT NULL,

    -- Email reference
    email_id VARCHAR(200) NOT NULL,  -- Gmail message ID or IMAP UID
    processed_email_id INTEGER,
    account_id VARCHAR(100) NOT NULL,  -- gmail_1, gmail_2, gmail_3, ionos

    -- Attachment metadata
    original_filename VARCHAR(500) NOT NULL,  -- Original filename from email
    file_size_bytes INTEGER NOT NULL,  -- File size in bytes
    mime_type VARCHAR(200) NOT NULL,  -- MIME type (e.g., application/pdf, image/jpeg)

    -- Storage
    stored_path VARCHAR(1000),  -- Local filesystem path (e.g., attachments/gmail_1/msg_123/file.pdf)
    storage_status VARCHAR(50) DEFAULT 'pending',  -- pending, downloaded, failed, skipped_too_large
    downloaded_at DATETIME,  -- When attachment was downloaded
    file_hash VARCHAR(64),  -- SHA-256 hash for deduplication

    -- Text extraction (Phase 2+ feature - not implemented yet)
    extracted_text TEXT,  -- Extracted text from PDF/DOCX/images (OCR)
    extraction_status VARCHAR(50),  -- pending, extracted, failed, not_supported

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSON,  -- Additional metadata (content analysis, virus scan results, etc.)

    -- Foreign keys
    FOREIGN KEY (processed_email_id) REFERENCES processed_emails(id) ON DELETE CASCADE
);

-- Create indexes for attachments table
CREATE INDEX IF NOT EXISTS idx_attachments_attachment_id ON attachments(attachment_id);
CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id);
CREATE INDEX IF NOT EXISTS idx_attachments_account_id ON attachments(account_id);
CREATE INDEX IF NOT EXISTS idx_attachments_processed_email_id ON attachments(processed_email_id);
CREATE INDEX IF NOT EXISTS idx_attachments_storage_status ON attachments(storage_status);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Migration 004 complete. The following features are now supported:
-- 1. Storage Level Strategy: ProcessedEmail.storage_level (full/summary/minimal)
-- 2. Email Content Storage: body_text, body_html, summary (conditional based on storage_level)
-- 3. Thread Handling: thread_id, thread_summary, thread_position, is_thread_start
-- 4. Attachment Tracking: has_attachments, attachment_count, attachments_metadata
-- 5. Attachment Storage: New attachments table with download tracking and file hash
-- 6. User Corrections: user_corrected, user_corrected_at, original_category/confidence
-- 7. Gmail Actions: gmail_label_applied, gmail_archived, gmail_marked_read
