"""
Pydantic Models for Email Extraction

Defines structured outputs for extracting tasks, decisions, questions,
and summaries from emails.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# EXTRACTED ENTITIES
# ============================================================================

class ExtractedTask(BaseModel):
    """
    A task or action item extracted from an email.

    Examples:
    - "Please send me the report by Friday"
    - "Can you review the document?"
    - "Don't forget to call John"
    """
    description: str = Field(
        ...,
        description="Clear description of the task/action to be taken",
        min_length=3,
        max_length=500
    )

    deadline: Optional[datetime] = Field(
        None,
        description="Deadline for the task (if mentioned)"
    )

    priority: Literal["low", "medium", "high"] = Field(
        ...,
        description="Priority level based on urgency and importance"
    )

    requires_action_from_me: bool = Field(
        ...,
        description="Whether this task requires action from the email recipient (me)"
    )

    context: Optional[str] = Field(
        None,
        description="Additional context or details about the task",
        max_length=200
    )

    assignee: Optional[str] = Field(
        None,
        description="Who is responsible for this task (if specified)",
        max_length=100
    )


class ExtractedDecision(BaseModel):
    """
    A decision point or choice extracted from an email.

    Examples:
    - "Should we go with Option A or Option B?"
    - "We need to decide on the meeting date"
    - "I recommend choosing the blue design"
    """
    question: str = Field(
        ...,
        description="The decision to be made (as a question)",
        min_length=5,
        max_length=300
    )

    options: List[str] = Field(
        default_factory=list,
        description="Possible options or choices (if mentioned)",
        max_items=10
    )

    recommendation: Optional[str] = Field(
        None,
        description="Recommended choice (if stated in email)",
        max_length=200
    )

    urgency: Literal["low", "medium", "high"] = Field(
        ...,
        description="How urgent is this decision"
    )

    requires_my_input: bool = Field(
        ...,
        description="Whether this decision requires input from the email recipient (me)"
    )

    context: Optional[str] = Field(
        None,
        description="Additional context about the decision",
        max_length=200
    )


class ExtractedQuestion(BaseModel):
    """
    A question that requires an answer, extracted from an email.

    Examples:
    - "When can we schedule the meeting?"
    - "What's your opinion on this?"
    - "Do you have time next week?"
    """
    question: str = Field(
        ...,
        description="The question being asked",
        min_length=5,
        max_length=300
    )

    context: Optional[str] = Field(
        None,
        description="Context or background for the question",
        max_length=200
    )

    requires_response: bool = Field(
        ...,
        description="Whether this question requires a response from the email recipient (me)"
    )

    urgency: Literal["low", "medium", "high"] = Field(
        ...,
        description="How urgent is answering this question"
    )

    question_type: Literal["factual", "opinion", "scheduling", "confirmation", "other"] = Field(
        ...,
        description="Type of question being asked"
    )


# ============================================================================
# COMPLETE EXTRACTION RESULT
# ============================================================================

class EmailExtraction(BaseModel):
    """
    Complete extraction result for an email.

    Contains all extracted tasks, decisions, questions, and a summary.
    """
    # Summary
    summary: str = Field(
        ...,
        description="Brief 1-2 sentence summary of the email content",
        min_length=10,
        max_length=500
    )

    # Extracted entities
    tasks: List[ExtractedTask] = Field(
        default_factory=list,
        description="List of tasks/action items found in the email"
    )

    decisions: List[ExtractedDecision] = Field(
        default_factory=list,
        description="List of decisions/choices mentioned in the email"
    )

    questions: List[ExtractedQuestion] = Field(
        default_factory=list,
        description="List of questions that need answers"
    )

    # Metadata
    has_action_items: bool = Field(
        ...,
        description="Whether the email contains any action items (tasks, decisions, or questions requiring response)"
    )

    main_topic: str = Field(
        ...,
        description="Main topic or theme of the email",
        min_length=3,
        max_length=100
    )

    sentiment: Literal["positive", "neutral", "negative", "urgent"] = Field(
        ...,
        description="Overall sentiment/tone of the email"
    )

    # Counts (for quick overview)
    @property
    def task_count(self) -> int:
        """Number of tasks extracted."""
        return len(self.tasks)

    @property
    def decision_count(self) -> int:
        """Number of decisions extracted."""
        return len(self.decisions)

    @property
    def question_count(self) -> int:
        """Number of questions extracted."""
        return len(self.questions)

    @property
    def total_items(self) -> int:
        """Total number of extracted items."""
        return self.task_count + self.decision_count + self.question_count

    def to_summary_dict(self) -> dict:
        """
        Create a concise summary dictionary.

        Returns:
            Dictionary with summary information
        """
        return {
            'summary': self.summary,
            'main_topic': self.main_topic,
            'sentiment': self.sentiment,
            'has_action_items': self.has_action_items,
            'counts': {
                'tasks': self.task_count,
                'decisions': self.decision_count,
                'questions': self.question_count,
                'total': self.total_items,
            },
        }
