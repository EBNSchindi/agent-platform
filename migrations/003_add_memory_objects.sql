-- Migration 003: Add Memory-Objects Tables (Tasks, Decisions, Questions, Journal Entries)
-- Date: 2025-11-20
-- Description: Adds Memory-Object tables derived from extraction events for Digital Twin

-- ============================================================================
-- TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) UNIQUE NOT NULL,

    -- Email reference
    account_id VARCHAR(100) NOT NULL,
    email_id VARCHAR(200) NOT NULL,
    processed_email_id INTEGER,

    -- Email context
    email_subject TEXT,
    email_sender VARCHAR(200),
    email_received_at DATETIME,

    -- Task details
    description TEXT NOT NULL,
    context TEXT,
    deadline DATETIME,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- Ownership
    assignee VARCHAR(200),
    requires_action_from_me BOOLEAN DEFAULT 1,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Completion tracking
    completed_at DATETIME,
    completion_notes TEXT,

    -- Event references
    extraction_event_id VARCHAR(36),

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSON,

    -- Foreign keys
    FOREIGN KEY (processed_email_id) REFERENCES processed_emails(id),
    FOREIGN KEY (extraction_event_id) REFERENCES events(event_id)
);

-- Indexes for tasks
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_account_id ON tasks(account_id);
CREATE INDEX IF NOT EXISTS idx_tasks_email_id ON tasks(email_id);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);


-- ============================================================================
-- DECISIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id VARCHAR(36) UNIQUE NOT NULL,

    -- Email reference
    account_id VARCHAR(100) NOT NULL,
    email_id VARCHAR(200) NOT NULL,
    processed_email_id INTEGER,

    -- Email context
    email_subject TEXT,
    email_sender VARCHAR(200),
    email_received_at DATETIME,

    -- Decision details
    question TEXT NOT NULL,
    context TEXT,
    options JSON NOT NULL,
    recommendation TEXT,

    -- Priority
    urgency VARCHAR(20) NOT NULL DEFAULT 'medium',
    requires_my_input BOOLEAN DEFAULT 1,

    -- Decision tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- User decision
    chosen_option VARCHAR(500),
    decision_notes TEXT,
    decided_at DATETIME,

    -- Event references
    extraction_event_id VARCHAR(36),

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSON,

    -- Foreign keys
    FOREIGN KEY (processed_email_id) REFERENCES processed_emails(id),
    FOREIGN KEY (extraction_event_id) REFERENCES events(event_id)
);

-- Indexes for decisions
CREATE INDEX IF NOT EXISTS idx_decisions_decision_id ON decisions(decision_id);
CREATE INDEX IF NOT EXISTS idx_decisions_account_id ON decisions(account_id);
CREATE INDEX IF NOT EXISTS idx_decisions_email_id ON decisions(email_id);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);


-- ============================================================================
-- QUESTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id VARCHAR(36) UNIQUE NOT NULL,

    -- Email reference
    account_id VARCHAR(100) NOT NULL,
    email_id VARCHAR(200) NOT NULL,
    processed_email_id INTEGER,

    -- Email context
    email_subject TEXT,
    email_sender VARCHAR(200),
    email_received_at DATETIME,

    -- Question details
    question TEXT NOT NULL,
    context TEXT,
    question_type VARCHAR(50) NOT NULL DEFAULT 'information',

    -- Response requirements
    requires_response BOOLEAN DEFAULT 1,
    urgency VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- Response tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- User response
    answer TEXT,
    answered_at DATETIME,

    -- Event references
    extraction_event_id VARCHAR(36),

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSON,

    -- Foreign keys
    FOREIGN KEY (processed_email_id) REFERENCES processed_emails(id),
    FOREIGN KEY (extraction_event_id) REFERENCES events(event_id)
);

-- Indexes for questions
CREATE INDEX IF NOT EXISTS idx_questions_question_id ON questions(question_id);
CREATE INDEX IF NOT EXISTS idx_questions_account_id ON questions(account_id);
CREATE INDEX IF NOT EXISTS idx_questions_email_id ON questions(email_id);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at);


-- ============================================================================
-- JOURNAL ENTRIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id VARCHAR(36) UNIQUE NOT NULL,

    -- Account and time period
    account_id VARCHAR(100) NOT NULL,
    date DATETIME NOT NULL,
    period_type VARCHAR(20) DEFAULT 'daily',

    -- Journal content
    title VARCHAR(500) NOT NULL,
    content_markdown TEXT NOT NULL,
    summary TEXT,

    -- Statistics
    total_emails_processed INTEGER DEFAULT 0,
    total_tasks_created INTEGER DEFAULT 0,
    total_decisions_made INTEGER DEFAULT 0,
    total_questions_answered INTEGER DEFAULT 0,

    -- Categories breakdown
    emails_by_category JSON,

    -- Key highlights
    top_senders JSON,
    important_items JSON,

    -- Generation metadata
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generation_event_id VARCHAR(36),

    -- Review status
    status VARCHAR(50) NOT NULL DEFAULT 'generated',
    reviewed_at DATETIME,
    user_notes TEXT,

    -- Metadata
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSON,

    -- Foreign keys
    FOREIGN KEY (generation_event_id) REFERENCES events(event_id)
);

-- Indexes for journal entries
CREATE INDEX IF NOT EXISTS idx_journal_entries_journal_id ON journal_entries(journal_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_account_id ON journal_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_status ON journal_entries(status);
