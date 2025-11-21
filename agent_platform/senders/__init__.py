"""
Sender Profile Management (Phase 5)

Services for managing sender profiles with:
- Whitelist/Blacklist
- Trust levels (trusted, neutral, suspicious, blocked)
- Category preferences (allowed/muted categories)
- Preference application during classification
- NLP intent parsing (Agent SDK)
- Intent execution
"""

from .profile_service import SenderProfileService
from .nlp_intent_agent import (
    create_nlp_intent_agent,
    parse_nlp_intent,
    ParsedIntent,
    IntentParserResult
)
from .intent_executor import IntentExecutor, IntentExecutionResult

__all__ = [
    'SenderProfileService',
    'create_nlp_intent_agent',
    'parse_nlp_intent',
    'ParsedIntent',
    'IntentParserResult',
    'IntentExecutor',
    'IntentExecutionResult'
]
