"""
Email Classifier Agent
Classifies emails as spam, important, normal, or auto-reply candidates.
Uses structured outputs (Pydantic) like Lab 3 patterns.
"""

from typing import List, Literal
from pydantic import BaseModel, Field
from agents import Agent
from datetime import datetime


# ============================================================================
# STRUCTURED OUTPUTS
# ============================================================================

class EmailClassification(BaseModel):
    """
    Structured output for email classification.
    Based on Pydantic patterns from 2_openai/3_lab3.ipynb
    """
    category: Literal["spam", "important", "normal", "auto_reply_candidate"] = Field(
        description="Email category based on content and sender"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for classification (0.0 to 1.0)"
    )
    suggested_label: str = Field(
        description="Suggested Gmail/Ionos label to apply"
    )
    should_reply: bool = Field(
        description="Whether this email should receive an automatic reply"
    )
    urgency: Literal["low", "medium", "high"] = Field(
        description="Urgency level for prioritization"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )


# ============================================================================
# CLASSIFIER AGENT
# ============================================================================

CLASSIFIER_INSTRUCTIONS = """You are an email classification expert. Your job is to analyze emails and categorize them accurately.

**Categories:**

1. **spam**:
   - Unsolicited commercial emails
   - Phishing attempts
   - Mass marketing from unknown senders
   - Suspicious links or requests
   - Generic subject lines like "You won!" or "Claim your prize"

2. **important**:
   - Emails from known contacts (check sender domain and name patterns)
   - Work-related communication
   - Financial/banking notifications
   - Appointments and meeting confirmations
   - Password resets from legitimate services
   - Legal or official documents

3. **normal**:
   - Newsletters from subscribed services
   - Social media notifications
   - Non-urgent updates
   - Automated service notifications
   - Promotional emails from known brands

4. **auto_reply_candidate**:
   - Simple questions that can be answered with standard responses
   - Meeting requests that need confirmation
   - Information requests about public information
   - Routine inquiries
   - Must NOT contain sensitive or complex topics

**Classification Guidelines:**

- **Confidence**: Be honest about certainty. Use lower scores when unsure.
- **Suggested Label**:
  - spam → "Spam"
  - important → "Important" or specific like "Work", "Finance"
  - normal → "Newsletters", "Notifications", "Social"
  - auto_reply_candidate → "Auto-Reply"

- **should_reply**:
  - True ONLY for auto_reply_candidate with high confidence
  - False for spam, newsletters, notifications
  - Consider for important emails that ask questions

- **Urgency**:
  - high: Time-sensitive, requires immediate attention
  - medium: Should be addressed soon
  - low: Can wait, informational

- **Reasoning**: Provide 1-2 sentence explanation

**Special Cases:**

- Banking emails from unknown senders → likely spam (phishing)
- Meeting invites from calendar systems → important
- Password resets YOU didn't request → important (security)
- Newsletter unsubscribe confirmations → normal
- "Out of office" replies → normal, should_reply=False

Analyze the email carefully and return classification in the exact JSON format specified."""


def create_classifier_agent() -> Agent:
    """
    Create classifier agent with structured output.

    Returns:
        Agent instance configured for email classification
    """
    agent = Agent(
        name="EmailClassifier",
        instructions=CLASSIFIER_INSTRUCTIONS,
        output_type=EmailClassification,  # Structured output
        model="gpt-4o-mini"  # Fast and cost-effective for classification
    )

    return agent


# ============================================================================
# BATCH CLASSIFICATION (for multiple emails)
# ============================================================================

async def classify_emails_batch(
    emails: List[dict],
    classifier_agent: Agent
) -> List[EmailClassification]:
    """
    Classify multiple emails in batch.

    Args:
        emails: List of email dictionaries (from fetch_unread_emails)
        classifier_agent: Classifier agent instance

    Returns:
        List of EmailClassification results
    """
    from agents import Runner
    import asyncio

    async def classify_single(email: dict) -> EmailClassification:
        """Classify a single email"""
        # Format email for classification
        email_text = f"""
**Subject:** {email.get('subject', 'No Subject')}
**From:** {email.get('sender', 'Unknown')}
**Date:** {email.get('date', '')}
**Preview:** {email.get('snippet', '')[:200]}

**Body (first 500 chars):**
{email.get('body', '')[:500]}
        """.strip()

        # Run classification
        result = await Runner.run(classifier_agent, email_text)
        return result.final_output

    # Classify all emails in parallel
    tasks = [classify_single(email) for email in emails]
    classifications = await asyncio.gather(*tasks)

    return classifications


# ============================================================================
# SPAM-SPECIFIC PATTERNS (Optional Enhancement)
# ============================================================================

SPAM_INDICATORS = [
    # Subject line patterns
    r"(?i)you.*won",
    r"(?i)claim.*prize",
    r"(?i)congratulations",
    r"(?i)act now",
    r"(?i)limited time",
    r"(?i)click here",
    r"(?i)urgent.*action",
    r"(?i)verify.*account",  # Unless from known sender
    r"(?i)bitcoin|cryptocurrency|forex",
    r"(?i)weight.*loss",
    r"(?i)make.*money.*fast",

    # Sender patterns
    r"noreply@",  # Context-dependent
    r"(?i)lottery",
    r"(?i)prize",
]


def quick_spam_check(subject: str, sender: str) -> float:
    """
    Quick regex-based spam score (0.0 to 1.0).
    Can be used as a fast pre-filter before AI classification.

    Args:
        subject: Email subject
        sender: Email sender

    Returns:
        Spam score (higher = more likely spam)
    """
    import re

    score = 0.0
    combined = f"{subject} {sender}"

    for pattern in SPAM_INDICATORS:
        if re.search(pattern, combined):
            score += 0.2

    return min(score, 1.0)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
Example usage:

from modules.email.agents.classifier import create_classifier_agent, classify_emails_batch
from modules.email.tools.gmail_tools import fetch_unread_emails_tool
from agents import Runner

# Create agent
classifier = create_classifier_agent()

# Fetch emails
emails = fetch_unread_emails_tool("gmail_1", max_results=10)

# Classify batch
classifications = await classify_emails_batch(emails, classifier)

# Process results
for email, classification in zip(emails, classifications):
    print(f"Email: {email['subject']}")
    print(f"Category: {classification.category}")
    print(f"Confidence: {classification.confidence:.2f}")
    print(f"Should reply: {classification.should_reply}")
    print(f"Reasoning: {classification.reasoning}")
    print("-" * 60)
"""
