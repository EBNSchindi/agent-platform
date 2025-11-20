"""
Email Extraction Module

Extracts structured information from emails:
- Tasks (actions to be taken)
- Decisions (choices to be made)
- Questions (information needed)
- Summary (brief overview)

Usage:
    from agent_platform.extraction import ExtractionAgent, EmailExtraction

    agent = ExtractionAgent()
    result = await agent.extract(email)

    for task in result.tasks:
        print(f"Task: {task.description}")
"""

from agent_platform.extraction.models import (
    ExtractedTask,
    ExtractedDecision,
    ExtractedQuestion,
    EmailExtraction,
)
from agent_platform.extraction.extraction_agent import ExtractionAgent

__all__ = [
    "ExtractedTask",
    "ExtractedDecision",
    "ExtractedQuestion",
    "EmailExtraction",
    "ExtractionAgent",
]
