"""
LLM Prompts for Email Extraction

Contains system prompts and instructions for extracting structured
information from emails.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert email analyzer specialized in extracting structured information from emails.

Your task is to analyze email content and extract:
1. **Tasks** - Action items that need to be done
2. **Decisions** - Choices or decisions that need to be made
3. **Questions** - Questions that need answers
4. **Summary** - A brief 1-2 sentence overview

## Guidelines for Tasks:
- Focus on concrete actions that need to be taken
- Identify deadlines if mentioned (even implicit ones like "this week")
- Determine if the task is for the email recipient or someone else
- Assess priority based on urgency words (urgent, ASAP, important, etc.)
- Examples:
  * "Please send me the report by Friday" → Task with deadline
  * "Can you review the document?" → Task without deadline
  * "Don't forget to call John" → Task, likely high priority

## Guidelines for Decisions:
- Look for choices that need to be made
- Extract mentioned options if available
- Identify recommendations if stated
- Determine if the recipient needs to make the decision
- Examples:
  * "Should we go with Option A or Option B?" → Decision with options
  * "I recommend choosing the blue design" → Decision with recommendation
  * "We need to decide on the meeting date" → Decision without options

## Guidelines for Questions:
- Extract all questions that require answers
- Determine if the recipient is expected to answer
- Classify the type of question (factual, opinion, scheduling, etc.)
- Assess urgency based on context
- Examples:
  * "When can we meet?" → Scheduling question, requires response
  * "What's your opinion?" → Opinion question, requires response
  * "Did you know that...?" → Rhetorical question, may not require response

## Guidelines for Summary:
- Keep it brief (1-2 sentences)
- Focus on the main point or request
- Use clear, actionable language
- Examples:
  * "Meeting invitation for project kickoff on Friday"
  * "Request to review budget proposal by end of week"
  * "Question about availability for upcoming conference"

## Priority/Urgency Assessment:
- **High**: Contains words like urgent, ASAP, critical, important, deadline today/tomorrow
- **Medium**: Contains deadline this week, "when you can", "please prioritize"
- **Low**: No deadline, "no rush", "whenever you have time"

## Sentiment Assessment:
- **Positive**: Friendly, enthusiastic, appreciative tone
- **Neutral**: Factual, professional, informative tone
- **Negative**: Complaints, concerns, disappointment
- **Urgent**: Time-sensitive, demanding immediate attention

## Important Notes:
- Be conservative: Don't extract items if you're not confident
- Empty lists are okay if no tasks/decisions/questions found
- Focus on items relevant to the email recipient
- Consider context when determining urgency and priority
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Analyze the following email and extract structured information:

**Subject:** {subject}

**From:** {sender}

**Email Body:**
{body}

**Additional Context:**
- Received: {received_at}
- Has attachments: {has_attachments}
- Is reply: {is_reply}

Please extract all tasks, decisions, questions, and provide a brief summary of this email.
"""


def build_extraction_prompt(
    subject: str,
    sender: str,
    body: str,
    received_at: str,
    has_attachments: bool,
    is_reply: bool,
) -> str:
    """
    Build the complete extraction prompt.

    Args:
        subject: Email subject line
        sender: Email sender address
        body: Email body content
        received_at: When email was received (ISO format or human-readable)
        has_attachments: Whether email has attachments
        is_reply: Whether email is a reply

    Returns:
        Complete formatted prompt
    """
    return EXTRACTION_USER_PROMPT_TEMPLATE.format(
        subject=subject,
        sender=sender,
        body=body,
        received_at=received_at,
        has_attachments="Yes" if has_attachments else "No",
        is_reply="Yes" if is_reply else "No",
    )


# Example extractions for few-shot learning (if needed)
EXAMPLE_EXTRACTIONS = [
    {
        "email": {
            "subject": "Project Update & Next Steps",
            "sender": "john@company.com",
            "body": """Hi there,

I wanted to give you a quick update on the project. We've completed Phase 1 and are ready to move forward.

Can you please review the attached document by Friday? We need to decide whether to go with Option A (faster but more expensive) or Option B (slower but cheaper). I'd recommend Option A given our timeline.

Also, when do you have time for a quick call next week to discuss the budget?

Thanks!
John"""
        },
        "extraction": {
            "summary": "Project update requesting document review by Friday and decision on implementation approach, plus scheduling a budget discussion call.",
            "main_topic": "Project progress and next steps",
            "sentiment": "neutral",
            "has_action_items": True,
            "tasks": [
                {
                    "description": "Review the attached document",
                    "deadline": "Friday",
                    "priority": "high",
                    "requires_action_from_me": True,
                    "context": "Needed for Phase 2 planning",
                    "assignee": None
                }
            ],
            "decisions": [
                {
                    "question": "Should we go with Option A or Option B for implementation?",
                    "options": ["Option A (faster but more expensive)", "Option B (slower but cheaper)"],
                    "recommendation": "Option A given our timeline",
                    "urgency": "high",
                    "requires_my_input": True,
                    "context": "Decision needed after reviewing the document"
                }
            ],
            "questions": [
                {
                    "question": "When do you have time for a quick call next week to discuss the budget?",
                    "context": "Budget discussion for Phase 2",
                    "requires_response": True,
                    "urgency": "medium",
                    "question_type": "scheduling"
                }
            ]
        }
    }
]
