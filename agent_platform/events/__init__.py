"""
Event-Log System for Digital Twin Platform

This module provides event logging functionality for tracking all actions
in the system. Events are immutable and form the foundation for:
- Audit trail
- Learning & feedback
- Historical analysis
- Twin growth tracking
"""

from agent_platform.events.event_types import EventType
from agent_platform.events.event_service import EventService, log_event, get_events

__all__ = [
    'EventType',
    'EventService',
    'log_event',
    'get_events',
]
