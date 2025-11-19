"""
Feedback Tracking Module

Learns from user actions on emails to improve future classifications.
Tracks actions like replies, archives, deletes, stars, and folder moves
to build and update sender/domain preferences over time.

The system uses exponential moving average for adaptive learning,
giving more weight to recent actions while still considering historical patterns.
"""

from agent_platform.feedback.tracker import FeedbackTracker, ActionType
from agent_platform.feedback.checker import FeedbackChecker

__all__ = [
    'FeedbackTracker',
    'ActionType',
    'FeedbackChecker',
]
