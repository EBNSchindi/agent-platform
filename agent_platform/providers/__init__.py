"""
Provider-Specific Handlers (Phase 7)

Handles provider-specific email operations:
- Gmail: Multi-label support (primary + secondary categories as labels)
- IONOS: Single-folder support (primary category only as folder)
"""

from .gmail_handler import GmailHandler
from .ionos_handler import IonosHandler

__all__ = ['GmailHandler', 'IonosHandler']
