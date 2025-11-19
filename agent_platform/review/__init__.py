"""
Review System Module

Manages medium-confidence email classifications through a review queue
and daily digest system. Integrates with feedback tracking to learn from
user approvals/rejections.

Main Components:
- ReviewQueueManager: Manages items in the review queue
- DailyDigestGenerator: Generates email summaries for review
- ReviewHandler: Handles user approval/rejection and feedback
"""

from agent_platform.review.queue_manager import ReviewQueueManager
from agent_platform.review.digest_generator import DailyDigestGenerator
from agent_platform.review.review_handler import ReviewHandler

__all__ = [
    'ReviewQueueManager',
    'DailyDigestGenerator',
    'ReviewHandler',
]
