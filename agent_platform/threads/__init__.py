"""
Thread Management System
Handles email thread tracking and summarization.
"""

from agent_platform.threads.thread_service import ThreadService
from agent_platform.threads.models import ThreadSummary, ThreadEmail

__all__ = [
    'ThreadService',
    'ThreadSummary',
    'ThreadEmail',
]
