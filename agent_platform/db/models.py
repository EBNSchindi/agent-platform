"""
Database Models
SQLAlchemy models for storing agent runs, steps, and module information.
"""

from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Module(Base):
    """Registered module information"""
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    agents = relationship("Agent", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Module(name='{self.name}', version='{self.version}', active={self.active})>"


class Agent(Base):
    """Registered agent information"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    agent_id = Column(String(200), unique=True, nullable=False, index=True)  # module_name.agent_name
    name = Column(String(100), nullable=False)
    agent_type = Column(String(100), nullable=False)  # classifier, responder, backup, etc.
    description = Column(Text)
    capabilities = Column(JSON, default=[])  # List of capabilities
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    module = relationship("Module", back_populates="agents")
    runs = relationship("Run", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent(agent_id='{self.agent_id}', type='{self.agent_type}')>"


class Run(Base):
    """Agent execution run"""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    run_id = Column(String(100), unique=True, nullable=False, index=True)  # UUID or timestamp-based
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, error
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    user_prompt = Column(Text)
    final_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    context = Column(JSON, default={})  # Additional context/metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="runs")
    steps = relationship("Step", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Run(run_id='{self.run_id}', status='{self.status}')>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration in seconds"""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class Step(Base):
    """Individual step within an agent run"""
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    index = Column(Integer, nullable=False)  # Step order
    role = Column(String(50), nullable=False)  # system, user, assistant, tool
    content = Column(Text, nullable=False)
    tool_name = Column(String(100), nullable=True)  # If this is a tool call
    tool_arguments = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    run = relationship("Run", back_populates="steps")

    def __repr__(self):
        return f"<Step(run_id={self.run_id}, index={self.index}, role='{self.role}')>"


# ============================================================================
# EVENT-LOG SYSTEM (Digital Twin Foundation)
# ============================================================================

class Event(Base):
    """
    Event-Log for Digital Twin System

    All actions in the system are logged as immutable events.
    This provides:
    - Complete audit trail
    - Learning foundation
    - Feedback tracking
    - Historical analysis

    Events are APPEND-ONLY (never updated/deleted).
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False, index=True)  # EMAIL_RECEIVED, EMAIL_CLASSIFIED, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Context
    account_id = Column(String(100), nullable=True, index=True)  # gmail_1, gmail_2, etc.
    email_id = Column(String(200), nullable=True, index=True)  # Email message ID (if applicable)
    user_id = Column(String(100), nullable=True)  # For multi-user support (future)

    # Event data
    payload = Column(JSON, nullable=False, default={})  # Event-specific data
    extra_metadata = Column(JSON, nullable=True, default={})  # Additional context (renamed from 'metadata')

    # Performance tracking
    processing_time_ms = Column(Float, nullable=True)  # Time taken for this event

    def __repr__(self):
        return f"<Event(event_id='{self.event_id}', type='{self.event_type}', timestamp='{self.timestamp}')>"

    def to_dict(self):
        """Convert event to dictionary for JSON serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'account_id': self.account_id,
            'email_id': self.email_id,
            'user_id': self.user_id,
            'payload': self.payload,
            'extra_metadata': self.extra_metadata,
            'processing_time_ms': self.processing_time_ms,
        }


# Email-specific tables (optional - for detailed email tracking)

class EmailAccount(Base):
    """Email account configuration"""
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), unique=True, nullable=False, index=True)  # gmail_1, gmail_2, ionos
    account_type = Column(String(50), nullable=False)  # gmail, ionos
    email_address = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=True)
    mode = Column(String(50), default="draft")  # draft, auto_reply, manual
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    processed_emails = relationship("ProcessedEmail", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EmailAccount(account_id='{self.account_id}', email='{self.email_address}')>"


class ProcessedEmail(Base):
    """Record of processed emails"""
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("email_accounts.id"), nullable=False)
    email_id = Column(String(200), nullable=False)  # Gmail message ID or IMAP UID
    message_id = Column(String(500), nullable=True)  # Email Message-ID header
    subject = Column(Text, nullable=True)
    sender = Column(String(200), nullable=True)
    received_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

    # Classification results (Legacy - basic classifier)
    category = Column(String(100), nullable=True)  # spam, important, normal, auto_reply_candidate
    confidence = Column(Float, nullable=True)
    suggested_label = Column(String(200), nullable=True)
    should_reply = Column(Boolean, default=False)
    urgency = Column(String(50), nullable=True)  # low, medium, high

    # NEW: Importance classification results
    importance_score = Column(Float, nullable=True)  # 0.0-1.0 importance score
    classification_confidence = Column(Float, nullable=True)  # 0.0-1.0 confidence
    llm_provider_used = Column(String(50), nullable=True)  # ollama, openai_fallback, rules_only
    rule_layer_hint = Column(String(500), nullable=True)  # What rules detected
    history_layer_hint = Column(String(500), nullable=True)  # Historical context used

    # Response tracking
    draft_generated = Column(Boolean, default=False)
    draft_id = Column(String(200), nullable=True)  # Gmail draft ID
    replied = Column(Boolean, default=False)
    replied_at = Column(DateTime, nullable=True)

    extra_metadata = Column(JSON, default={})

    # Relationships
    account = relationship("EmailAccount", back_populates="processed_emails")

    def __repr__(self):
        return f"<ProcessedEmail(email_id='{self.email_id}', category='{self.category}')>"

    class Config:
        # Composite unique constraint
        __table_args__ = (
            # Prevent processing same email twice in same account
            # Index(['account_id', 'email_id'], unique=True),
        )


# ============================================================================
# IMPORTANCE CLASSIFICATION & LEARNING TABLES
# ============================================================================

class SenderPreference(Base):
    """User preferences learned from actions on emails from specific senders"""
    __tablename__ = "sender_preferences"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)  # gmail_1, gmail_2, etc.

    # Sender identification
    sender_email = Column(String(200), nullable=False, index=True)
    sender_domain = Column(String(200), nullable=False, index=True)
    sender_name = Column(String(200), nullable=True)

    # Learned preferences (updated based on user actions)
    preferred_category = Column(String(100), nullable=True)  # Most common category
    average_importance = Column(Float, default=0.5)  # 0.0-1.0

    # Statistics
    total_emails_received = Column(Integer, default=0)
    total_replies = Column(Integer, default=0)
    total_archived = Column(Integer, default=0)
    total_deleted = Column(Integer, default=0)
    total_moved_to_folder = Column(Integer, default=0)

    # Behavioral patterns
    avg_time_to_reply_hours = Column(Float, nullable=True)  # How quickly user replies
    reply_rate = Column(Float, default=0.0)  # % of emails replied to
    archive_rate = Column(Float, default=0.0)  # % archived
    delete_rate = Column(Float, default=0.0)  # % deleted

    # Metadata
    last_email_received = Column(DateTime, nullable=True)
    last_user_action = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    feedback_events = relationship("FeedbackEvent", back_populates="sender_preference")

    def __repr__(self):
        return f"<SenderPreference(sender='{self.sender_email}', importance={self.average_importance:.2f})>"


class DomainPreference(Base):
    """User preferences at domain level (e.g., all emails from @company.com)"""
    __tablename__ = "domain_preferences"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)

    # Domain identification
    domain = Column(String(200), nullable=False, index=True)  # e.g., "company.com"

    # Learned preferences
    preferred_category = Column(String(100), nullable=True)
    average_importance = Column(Float, default=0.5)

    # Statistics
    total_emails_received = Column(Integer, default=0)
    reply_rate = Column(Float, default=0.0)
    archive_rate = Column(Float, default=0.0)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DomainPreference(domain='{self.domain}', importance={self.average_importance:.2f})>"


class FeedbackEvent(Base):
    """Individual user actions on emails (feedback for learning)"""
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)

    # Email reference
    email_id = Column(String(200), nullable=False, index=True)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)
    sender_preference_id = Column(Integer, ForeignKey("sender_preferences.id"), nullable=True)

    # Email context
    sender_email = Column(String(200), nullable=False, index=True)
    sender_domain = Column(String(200), nullable=False, index=True)
    subject = Column(Text, nullable=True)

    # Original classification
    original_category = Column(String(100), nullable=True)
    original_importance = Column(Float, nullable=True)
    original_confidence = Column(Float, nullable=True)

    # User action
    action_type = Column(String(50), nullable=False, index=True)
    # Possible values: 'replied', 'archived', 'deleted', 'moved_folder',
    #                  'changed_label', 'manual_category_change', 'marked_important'

    action_details = Column(JSON, default={})  # e.g., {"folder": "Work", "time_to_action_hours": 2.5}

    # Inferred feedback
    inferred_category = Column(String(100), nullable=True)  # What we learn from the action
    inferred_importance = Column(Float, nullable=True)  # 0.0-1.0

    # Timestamps
    email_received_at = Column(DateTime, nullable=True)
    action_taken_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    processed_email = relationship("ProcessedEmail", backref="feedback_events")
    sender_preference = relationship("SenderPreference", back_populates="feedback_events")

    def __repr__(self):
        return f"<FeedbackEvent(action='{self.action_type}', sender='{self.sender_email}')>"


class ReviewQueueItem(Base):
    """Emails pending user review (medium confidence classifications)"""
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)

    # Email reference
    email_id = Column(String(200), nullable=False)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)

    # Email data
    subject = Column(Text, nullable=True)
    sender = Column(String(200), nullable=True)
    snippet = Column(Text, nullable=True)

    # Classification
    suggested_category = Column(String(100), nullable=False)
    importance_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=True)

    # Review status
    status = Column(String(50), default="pending", index=True)
    # Values: 'pending', 'approved', 'rejected', 'modified'

    # User response
    user_approved = Column(Boolean, nullable=True)
    user_corrected_category = Column(String(100), nullable=True)
    user_feedback = Column(Text, nullable=True)

    # Timestamps
    added_to_queue_at = Column(DateTime, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, default={})

    # Relationships
    processed_email = relationship("ProcessedEmail", backref="review_queue_items")

    def __repr__(self):
        return f"<ReviewQueueItem(subject='{self.subject[:30] if self.subject else ''}...', status='{self.status}')>"


class SubjectPattern(Base):
    """Learned patterns from email subjects (optional - for advanced learning)"""
    __tablename__ = "subject_patterns"

    id = Column(Integer, primary_key=True)
    account_id = Column(String(100), nullable=False, index=True)

    # Pattern
    pattern = Column(String(500), nullable=False, index=True)  # e.g., "Invoice #", "Meeting:", "RE:"
    pattern_type = Column(String(50), nullable=False)  # 'prefix', 'contains', 'regex'

    # Learned association
    preferred_category = Column(String(100), nullable=True)
    average_importance = Column(Float, default=0.5)

    # Statistics
    occurrence_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SubjectPattern(pattern='{self.pattern}', category='{self.preferred_category}')>"
