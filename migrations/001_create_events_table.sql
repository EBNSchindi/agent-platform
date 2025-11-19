-- Migration: Create Events Table
-- Date: 2025-11-20
-- Description: Event-Log System for Digital Twin Platform

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(36) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    timestamp DATETIME NOT NULL,
    account_id VARCHAR(100),
    email_id VARCHAR(200),
    user_id VARCHAR(100),
    payload JSON NOT NULL DEFAULT '{}',
    extra_metadata JSON DEFAULT '{}',
    processing_time_ms REAL
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_account_id ON events(account_id);
CREATE INDEX IF NOT EXISTS idx_events_email_id ON events(email_id);

-- Comments
-- This table stores all events in the Digital Twin system
-- Events are APPEND-ONLY (never updated or deleted)
-- Provides complete audit trail and learning foundation
