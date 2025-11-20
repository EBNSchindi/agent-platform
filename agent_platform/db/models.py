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


# ============================================================================
# MEMORY-OBJECTS (Digital Twin - Derived from Events)
# ============================================================================

class Task(Base):
    """
    Task Memory-Object (derived from TASK_EXTRACTED events)

    Represents actionable items extracted from emails that require attention.
    These are persistent memory objects that can be tracked, updated, and completed.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))

    # Email reference
    account_id = Column(String(100), nullable=False, index=True)
    email_id = Column(String(200), nullable=False, index=True)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)

    # Email context
    email_subject = Column(Text, nullable=True)
    email_sender = Column(String(200), nullable=True)
    email_received_at = Column(DateTime, nullable=True)

    # Task details (from ExtractedTask model)
    description = Column(Text, nullable=False)  # What needs to be done
    context = Column(Text, nullable=True)  # Additional context from email
    deadline = Column(DateTime, nullable=True, index=True)  # When it needs to be done
    priority = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent

    # Ownership
    assignee = Column(String(200), nullable=True)  # Who should do it (if specified)
    requires_action_from_me = Column(Boolean, default=True)  # Does the user need to act?

    # Status tracking
    status = Column(String(50), default="pending", index=True)
    # Values: 'pending', 'in_progress', 'completed', 'cancelled', 'waiting'

    # Completion tracking
    completed_at = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)

    # Event references (Event-First principle)
    extraction_event_id = Column(String(36), ForeignKey("events.event_id"), nullable=True)
    # Additional events: STATUS_CHANGED, TASK_COMPLETED, etc.

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    processed_email = relationship("ProcessedEmail", backref="tasks")
    extraction_event = relationship("Event", foreign_keys=[extraction_event_id])

    def __repr__(self):
        return f"<Task(task_id='{self.task_id}', description='{self.description[:30]}...', status='{self.status}')>"

    def to_dict(self):
        """Convert task to dictionary for JSON serialization"""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'context': self.context,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'priority': self.priority,
            'status': self.status,
            'requires_action_from_me': self.requires_action_from_me,
            'assignee': self.assignee,
            'email_subject': self.email_subject,
            'email_sender': self.email_sender,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Decision(Base):
    """
    Decision Memory-Object (derived from DECISION_EXTRACTED events)

    Represents decisions that need to be made, extracted from emails.
    Tracks options, recommendations, and user choices.
    """
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    decision_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))

    # Email reference
    account_id = Column(String(100), nullable=False, index=True)
    email_id = Column(String(200), nullable=False, index=True)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)

    # Email context
    email_subject = Column(Text, nullable=True)
    email_sender = Column(String(200), nullable=True)
    email_received_at = Column(DateTime, nullable=True)

    # Decision details (from ExtractedDecision model)
    question = Column(Text, nullable=False)  # The decision to be made
    context = Column(Text, nullable=True)  # Additional context
    options = Column(JSON, nullable=False, default=[])  # List of available options
    recommendation = Column(Text, nullable=True)  # System/sender recommendation

    # Priority
    urgency = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent
    requires_my_input = Column(Boolean, default=True)  # Does the user need to decide?

    # Decision tracking
    status = Column(String(50), default="pending", index=True)
    # Values: 'pending', 'decided', 'delegated', 'cancelled'

    # User decision
    chosen_option = Column(String(500), nullable=True)
    decision_notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    # Event references
    extraction_event_id = Column(String(36), ForeignKey("events.event_id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    processed_email = relationship("ProcessedEmail", backref="decisions")
    extraction_event = relationship("Event", foreign_keys=[extraction_event_id])

    def __repr__(self):
        return f"<Decision(decision_id='{self.decision_id}', question='{self.question[:30]}...', status='{self.status}')>"

    def to_dict(self):
        """Convert decision to dictionary for JSON serialization"""
        return {
            'decision_id': self.decision_id,
            'question': self.question,
            'context': self.context,
            'options': self.options,
            'recommendation': self.recommendation,
            'urgency': self.urgency,
            'status': self.status,
            'requires_my_input': self.requires_my_input,
            'chosen_option': self.chosen_option,
            'decision_notes': self.decision_notes,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'email_subject': self.email_subject,
            'email_sender': self.email_sender,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Question(Base):
    """
    Question Memory-Object (derived from QUESTION_EXTRACTED events)

    Represents questions extracted from emails that need answers.
    Tracks response requirements and urgency.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    question_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))

    # Email reference
    account_id = Column(String(100), nullable=False, index=True)
    email_id = Column(String(200), nullable=False, index=True)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)

    # Email context
    email_subject = Column(Text, nullable=True)
    email_sender = Column(String(200), nullable=True)
    email_received_at = Column(DateTime, nullable=True)

    # Question details (from ExtractedQuestion model)
    question = Column(Text, nullable=False)  # The question being asked
    context = Column(Text, nullable=True)  # Additional context
    question_type = Column(String(50), nullable=False, default="information")
    # Types: 'yes_no', 'information', 'clarification', 'decision', 'opinion'

    # Response requirements
    requires_response = Column(Boolean, default=True)
    urgency = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent

    # Response tracking
    status = Column(String(50), default="pending", index=True)
    # Values: 'pending', 'answered', 'delegated', 'not_applicable'

    # User response
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    # Event references
    extraction_event_id = Column(String(36), ForeignKey("events.event_id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    processed_email = relationship("ProcessedEmail", backref="questions")
    extraction_event = relationship("Event", foreign_keys=[extraction_event_id])

    def __repr__(self):
        return f"<Question(question_id='{self.question_id}', question='{self.question[:30]}...', status='{self.status}')>"

    def to_dict(self):
        """Convert question to dictionary for JSON serialization"""
        return {
            'question_id': self.question_id,
            'question': self.question,
            'context': self.context,
            'question_type': self.question_type,
            'requires_response': self.requires_response,
            'urgency': self.urgency,
            'status': self.status,
            'answer': self.answer,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
            'email_subject': self.email_subject,
            'email_sender': self.email_sender,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class JournalEntry(Base):
    """
    Journal Entry Memory-Object

    Daily summary journal generated from events and memory-objects.
    Provides human-readable overview of the day's activities.
    """
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    journal_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))

    # Account and time period
    account_id = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # Date this journal covers
    period_type = Column(String(20), default="daily")  # daily, weekly, monthly

    # Journal content
    title = Column(String(500), nullable=False)
    content_markdown = Column(Text, nullable=False)  # Full journal in Markdown format
    summary = Column(Text, nullable=True)  # Brief summary

    # Statistics
    total_emails_processed = Column(Integer, default=0)
    total_tasks_created = Column(Integer, default=0)
    total_decisions_made = Column(Integer, default=0)
    total_questions_answered = Column(Integer, default=0)

    # Categories breakdown
    emails_by_category = Column(JSON, default={})  # {"wichtig": 5, "spam": 2, ...}

    # Key highlights
    top_senders = Column(JSON, default=[])  # List of top senders with counts
    important_items = Column(JSON, default=[])  # List of important tasks/decisions/questions

    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generation_event_id = Column(String(36), ForeignKey("events.event_id"), nullable=True)

    # Review status
    status = Column(String(50), default="generated", index=True)
    # Values: 'generated', 'reviewed', 'archived'

    reviewed_at = Column(DateTime, nullable=True)
    user_notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON, default={})

    # Relationships
    generation_event = relationship("Event", foreign_keys=[generation_event_id])

    def __repr__(self):
        return f"<JournalEntry(journal_id='{self.journal_id}', date='{self.date}', title='{self.title[:30]}...')>"

    def to_dict(self):
        """Convert journal entry to dictionary for JSON serialization"""
        return {
            'journal_id': self.journal_id,
            'account_id': self.account_id,
            'date': self.date.isoformat(),
            'period_type': self.period_type,
            'title': self.title,
            'content_markdown': self.content_markdown,
            'summary': self.summary,
            'total_emails_processed': self.total_emails_processed,
            'total_tasks_created': self.total_tasks_created,
            'total_decisions_made': self.total_decisions_made,
            'total_questions_answered': self.total_questions_answered,
            'emails_by_category': self.emails_by_category,
            'top_senders': self.top_senders,
            'important_items': self.important_items,
            'status': self.status,
            'generated_at': self.generated_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'user_notes': self.user_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
