"""
Pydantic models for thread handling
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ThreadEmail(BaseModel):
    """Single email in a thread"""
    email_id: str = Field(..., description="Gmail message ID")
    subject: str = Field(..., description="Email subject")
    sender: str = Field(..., description="Sender email address")
    received_at: datetime = Field(..., description="When email was received")
    summary: Optional[str] = Field(None, description="Brief summary (1-2 sentences)")
    position: int = Field(..., description="Position in thread (1=first, 2=second, etc.)")
    is_thread_start: bool = Field(..., description="True if this is the first email in thread")


class ThreadSummary(BaseModel):
    """Summary of an email thread"""
    thread_id: str = Field(..., description="Gmail thread ID")
    account_id: str = Field(..., description="Account ID")
    email_count: int = Field(..., description="Number of emails in thread")
    participants: List[str] = Field(..., description="List of email addresses involved")
    subject: str = Field(..., description="Thread subject")
    started_at: datetime = Field(..., description="When thread started")
    last_email_at: datetime = Field(..., description="When last email was received")
    summary: str = Field(..., description="LLM-generated thread summary")
    key_points: List[str] = Field(default_factory=list, description="Key points from thread")
    emails: List[ThreadEmail] = Field(..., description="Emails in thread")


class ThreadSummarizationPrompt(BaseModel):
    """Prompt for LLM thread summarization"""
    thread_id: str
    emails: List[dict]  # List of email dicts with subject, sender, body, date

    def format_for_llm(self) -> str:
        """Format thread emails for LLM prompt"""
        parts = [
            "Thread of emails to summarize:",
            "",
        ]

        for i, email in enumerate(self.emails, 1):
            parts.append(f"Email {i}:")
            parts.append(f"From: {email.get('sender', 'Unknown')}")
            parts.append(f"Subject: {email.get('subject', 'No subject')}")
            parts.append(f"Date: {email.get('received_at', 'Unknown')}")
            parts.append(f"Content: {email.get('body_text', '')[:500]}")  # First 500 chars
            parts.append("")

        parts.append("---")
        parts.append("Provide a 2-3 sentence summary of this email thread, focusing on:")
        parts.append("1. The main topic or question")
        parts.append("2. Key decisions or outcomes")
        parts.append("3. Current status or next steps")

        return "\n".join(parts)
