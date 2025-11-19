"""
Database Models
SQLAlchemy models for storing agent runs, steps, and module information.
"""

from datetime import datetime
from typing import Optional
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
    metadata = Column(JSON, default={})

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
    metadata = Column(JSON, default={})

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
    metadata = Column(JSON, default={})

    # Relationships
    run = relationship("Run", back_populates="steps")

    def __repr__(self):
        return f"<Step(run_id={self.run_id}, index={self.index}, role='{self.role}')>"


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
    metadata = Column(JSON, default={})

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

    # Classification results
    category = Column(String(100), nullable=True)  # spam, important, normal, auto_reply_candidate
    confidence = Column(Float, nullable=True)
    suggested_label = Column(String(200), nullable=True)
    should_reply = Column(Boolean, default=False)
    urgency = Column(String(50), nullable=True)  # low, medium, high

    # Response tracking
    draft_generated = Column(Boolean, default=False)
    draft_id = Column(String(200), nullable=True)  # Gmail draft ID
    replied = Column(Boolean, default=False)
    replied_at = Column(DateTime, nullable=True)

    metadata = Column(JSON, default={})

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
