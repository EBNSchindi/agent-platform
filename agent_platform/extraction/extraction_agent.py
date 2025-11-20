"""
Email Extraction Agent

Extracts structured information (tasks, decisions, questions, summary) from emails
using LLM with Structured Outputs.

Architecture:
- Ollama-first (local, free, fast)
- OpenAI fallback (cloud, paid, reliable)
- Event-logging integration
"""

import time
from typing import Optional
from datetime import datetime

from agent_platform.extraction.models import EmailExtraction
from agent_platform.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from agent_platform.classification.models import EmailToClassify
from agent_platform.llm.providers import get_llm_provider
from agent_platform.events import log_event, EventType
from agent_platform.monitoring import SystemLogger


class ExtractionAgent:
    """
    Extracts structured information from emails.

    Uses UnifiedLLMProvider (Ollama-first + OpenAI fallback).
    Returns EmailExtraction with tasks, decisions, questions, and summary.
    """

    def __init__(self):
        """Initialize extraction agent."""
        # Get unified LLM provider (Ollama-first + OpenAI fallback)
        self.llm_provider = get_llm_provider()

        # Logger
        self.logger = SystemLogger.get_logger("extraction")

    async def extract(
        self,
        email: EmailToClassify,
        force_openai: bool = False,
    ) -> EmailExtraction:
        """
        Extract structured information from email.

        Args:
            email: Email to analyze
            force_openai: If True, skip Ollama and use OpenAI directly

        Returns:
            EmailExtraction with tasks, decisions, questions, and summary

        Example:
            agent = ExtractionAgent()
            result = await agent.extract(email)

            print(f"Summary: {result.summary}")
            print(f"Found {result.task_count} tasks")

            for task in result.tasks:
                print(f"  - {task.description}")
        """
        start_time = time.time()

        # Build prompt
        prompt = build_extraction_prompt(
            subject=email.subject,
            sender=email.sender,
            body=email.body,
            received_at=email.received_at.isoformat() if email.received_at else "Unknown",
            has_attachments=email.has_attachments,
            is_reply=email.is_reply,
        )

        # Build messages
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        # Call LLM with structured output (Ollama-first + OpenAI fallback)
        self.logger.info(f"🤖 Extracting information from email...")

        response, llm_provider = await self.llm_provider.complete(
            messages=messages,
            response_format=EmailExtraction,
            force_provider="openai" if force_openai else None,
        )

        # Extract parsed result from response
        extraction_result = response.choices[0].message.parsed

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Log extraction results
        self.logger.info(
            f"📊 Extraction complete: {extraction_result.task_count} tasks, "
            f"{extraction_result.decision_count} decisions, "
            f"{extraction_result.question_count} questions "
            f"(provider={llm_provider}, time={processing_time_ms:.0f}ms)"
        )

        # Log events to Event-Log system
        self._log_extraction_events(
            email=email,
            extraction=extraction_result,
            llm_provider=llm_provider,
            processing_time_ms=processing_time_ms,
        )

        return extraction_result

    def _log_extraction_events(
        self,
        email: EmailToClassify,
        extraction: EmailExtraction,
        llm_provider: str,
        processing_time_ms: float,
    ) -> None:
        """
        Log extraction events to Event-Log system.

        Logs:
        - EMAIL_ANALYZED event (overall extraction)
        - TASK_EXTRACTED events (one per task)
        - DECISION_EXTRACTED events (one per decision)
        - QUESTION_EXTRACTED events (one per question)

        Args:
            email: Original email
            extraction: Extraction result
            llm_provider: LLM provider used
            processing_time_ms: Processing time in milliseconds
        """
        try:
            # Log overall EMAIL_ANALYZED event
            log_event(
                event_type=EventType.EMAIL_ANALYZED,
                account_id=email.account_id,
                email_id=email.email_id,
                payload={
                    'summary': extraction.summary,
                    'main_topic': extraction.main_topic,
                    'sentiment': extraction.sentiment,
                    'has_action_items': extraction.has_action_items,
                    'task_count': extraction.task_count,
                    'decision_count': extraction.decision_count,
                    'question_count': extraction.question_count,
                },
                extra_metadata={
                    'llm_provider': llm_provider,
                },
                processing_time_ms=processing_time_ms,
            )

            # Log TASK_EXTRACTED events
            for idx, task in enumerate(extraction.tasks):
                log_event(
                    event_type=EventType.TASK_EXTRACTED,
                    account_id=email.account_id,
                    email_id=email.email_id,
                    payload={
                        'task_index': idx,
                        'description': task.description,
                        'deadline': task.deadline.isoformat() if task.deadline else None,
                        'priority': task.priority,
                        'requires_action_from_me': task.requires_action_from_me,
                        'context': task.context,
                        'assignee': task.assignee,
                    },
                    extra_metadata={
                        'llm_provider': llm_provider,
                    },
                )

            # Log DECISION_EXTRACTED events
            for idx, decision in enumerate(extraction.decisions):
                log_event(
                    event_type=EventType.DECISION_EXTRACTED,
                    account_id=email.account_id,
                    email_id=email.email_id,
                    payload={
                        'decision_index': idx,
                        'question': decision.question,
                        'options': decision.options,
                        'recommendation': decision.recommendation,
                        'urgency': decision.urgency,
                        'requires_my_input': decision.requires_my_input,
                        'context': decision.context,
                    },
                    extra_metadata={
                        'llm_provider': llm_provider,
                    },
                )

            # Log QUESTION_EXTRACTED events
            for idx, question in enumerate(extraction.questions):
                log_event(
                    event_type=EventType.QUESTION_EXTRACTED,
                    account_id=email.account_id,
                    email_id=email.email_id,
                    payload={
                        'question_index': idx,
                        'question': question.question,
                        'context': question.context,
                        'requires_response': question.requires_response,
                        'urgency': question.urgency,
                        'question_type': question.question_type,
                    },
                    extra_metadata={
                        'llm_provider': llm_provider,
                    },
                )

        except Exception as e:
            self.logger.warning(f"Failed to log extraction events: {e}")
