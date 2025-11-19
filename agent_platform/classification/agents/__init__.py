"""
Classification Agents using OpenAI Agents SDK

This module contains SDK-based agents that wrap the existing classification logic
following the Preservation Principle:
- EXTRACT existing logic (100% preserved)
- WRAP as Agent tools
- ORCHESTRATE with Runner.run()

Agents:
- rule_agent: Pattern matching (spam, newsletter, auto-reply detection)
- history_agent: User behavior learning (reply rate, archive rate, EMA)
- llm_agent: Deep semantic analysis (Ollama-first + OpenAI fallback)
- orchestrator_agent: Early stopping orchestration (0.85 confidence threshold)
"""

from agent_platform.classification.agents.rule_agent import create_rule_agent
from agent_platform.classification.agents.history_agent import create_history_agent
from agent_platform.classification.agents.llm_agent import create_llm_agent
from agent_platform.classification.agents.orchestrator_agent import (
    create_orchestrator_agent,
    AgentBasedClassifier,
)

__all__ = [
    "create_rule_agent",
    "create_history_agent",
    "create_llm_agent",
    "create_orchestrator_agent",
    "AgentBasedClassifier",
]
