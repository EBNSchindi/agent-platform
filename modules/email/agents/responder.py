"""
Email Responder Agent
Generates draft email responses using specialized sub-agents.
Based on Agent-as-Tool pattern from 2_openai/2_lab2.ipynb
"""

from typing import Literal
from pydantic import BaseModel, Field
from agents import Agent


# ============================================================================
# STRUCTURED OUTPUTS
# ============================================================================

class EmailResponse(BaseModel):
    """Structured output for generated email response"""
    subject: str = Field(
        max_length=100,
        description="Reply subject line (typically Re: original subject)"
    )
    body: str = Field(
        description="Email body content (plain text or HTML)"
    )
    tone: Literal["professional", "friendly", "brief"] = Field(
        description="Tone used in the response"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the appropriateness of this response"
    )
    requires_review: bool = Field(
        description="Whether this draft requires human review before sending"
    )
    reasoning: str = Field(
        description="Brief explanation of response strategy"
    )


# ============================================================================
# SPECIALIZED SUB-AGENTS (Agent-as-Tool Pattern)
# ============================================================================

PROFESSIONAL_INSTRUCTIONS = """You are a professional email responder. Write business-appropriate email responses.

**Style:**
- Formal but warm tone
- Clear and concise
- Professional language
- Proper salutations (Dear X / Best regards)
- Focus on facts and actionable information
- Avoid emojis and casual language

**Structure:**
1. Greeting with name if available
2. Acknowledge their email/request
3. Provide clear answer or next steps
4. Closing with call-to-action if needed
5. Professional sign-off

**Length:** 100-200 words maximum

**Example:**
"Dear John,

Thank you for reaching out regarding [topic].

[Provide clear, factual response]

Please let me know if you need any additional information.

Best regards"

Return response in EmailResponse format with tone='professional'."""


FRIENDLY_INSTRUCTIONS = """You are a friendly email responder. Write warm, personable email responses.

**Style:**
- Conversational but respectful tone
- Show empathy and understanding
- Use contractions (I'm, you're, we'll)
- Warmer language
- Light, positive tone
- Can use occasional emoji if appropriate 😊

**Structure:**
1. Warm greeting (Hi! / Hey there!)
2. Personal acknowledgment
3. Helpful, friendly response
4. Encouraging closing
5. Friendly sign-off (Cheers / Thanks!)

**Length:** 80-150 words maximum

**Example:**
"Hi Sarah!

Thanks so much for getting in touch! I'd be happy to help with that.

[Friendly, helpful response]

Feel free to reach out if you have any other questions!

Cheers"

Return response in EmailResponse format with tone='friendly'."""


BRIEF_INSTRUCTIONS = """You are a concise email responder. Write short, to-the-point email responses.

**Style:**
- Direct and clear
- Minimal pleasantries
- Get straight to the answer
- No unnecessary words
- Professional but brief

**Structure:**
1. Quick greeting (Hi X,)
2. Direct answer/response
3. Short closing (Thanks / Regards)

**Length:** 30-80 words maximum

**Example:**
"Hi Alex,

[Direct answer in 1-2 sentences]

Let me know if you need anything else.

Thanks"

Return response in EmailResponse format with tone='brief'."""


def create_professional_agent() -> Agent:
    """Create professional tone responder agent"""
    return Agent(
        name="ProfessionalResponder",
        instructions=PROFESSIONAL_INSTRUCTIONS,
        output_type=EmailResponse,
        model="gpt-4o-mini"
    )


def create_friendly_agent() -> Agent:
    """Create friendly tone responder agent"""
    return Agent(
        name="FriendlyResponder",
        instructions=FRIENDLY_INSTRUCTIONS,
        output_type=EmailResponse,
        model="gpt-4o-mini"
    )


def create_brief_agent() -> Agent:
    """Create brief/concise tone responder agent"""
    return Agent(
        name="BriefResponder",
        instructions=BRIEF_INSTRUCTIONS,
        output_type=EmailResponse,
        model="gpt-4o-mini"
    )


# ============================================================================
# RESPONDER ORCHESTRATOR
# ============================================================================

ORCHESTRATOR_INSTRUCTIONS = """You are an email response orchestrator. Your job is to select the appropriate tone and generate a response.

**Your Tools:**
- professional_responder: For business emails, formal requests, unknown senders
- friendly_responder: For casual emails, known contacts, personal topics
- brief_responder: For quick acknowledgments, simple questions, time-sensitive replies

**Decision Process:**

1. **Analyze the incoming email:**
   - Who is the sender? (business contact, friend, unknown)
   - What's the topic? (work-related, personal, routine)
   - What's the urgency?
   - What tone did they use?

2. **Select appropriate tone:**
   - Professional: Business emails, formal requests, first-time contacts
   - Friendly: Known contacts, personal emails, casual topics
   - Brief: Quick updates, confirmations, simple yes/no questions

3. **Generate response:**
   - Use the selected agent tool
   - Provide context about the sender and their email
   - Return the generated response

4. **Quality check:**
   - Does it answer their question?
   - Is the tone appropriate?
   - Is the length appropriate?
   - Set requires_review=True if:
     * Contains commitments or promises
     * Involves sensitive topics
     * Confidence < 0.8
     * Multiple interpretations possible

**Important:**
- Match the sender's tone when appropriate
- Keep responses concise
- Always be helpful and clear
- Set higher confidence_score only when you're certain the response is appropriate"""


def create_responder_orchestrator() -> Agent:
    """
    Create responder orchestrator that uses specialized agents as tools.
    Based on Agent-as-Tool pattern from Lab 2.

    Returns:
        Orchestrator agent with sub-agents as tools
    """
    # Create specialized agents
    professional = create_professional_agent()
    friendly = create_friendly_agent()
    brief = create_brief_agent()

    # Convert agents to tools
    professional_tool = professional.as_tool(
        tool_name="professional_responder",
        tool_description="Generate professional, business-appropriate email response"
    )

    friendly_tool = friendly.as_tool(
        tool_name="friendly_responder",
        tool_description="Generate friendly, warm email response"
    )

    brief_tool = brief.as_tool(
        tool_name="brief_responder",
        tool_description="Generate brief, concise email response"
    )

    # Create orchestrator with tools
    orchestrator = Agent(
        name="EmailResponseOrchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        tools=[professional_tool, friendly_tool, brief_tool],
        output_type=EmailResponse,
        model="gpt-4o-mini"
    )

    return orchestrator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_email_for_response(email: dict, classification: dict = None) -> str:
    """
    Format email data for response generation.

    Args:
        email: Email dictionary from fetch tools
        classification: Optional classification results

    Returns:
        Formatted string for agent input
    """
    context = f"""
**Original Email:**
**From:** {email.get('sender', 'Unknown')}
**Subject:** {email.get('subject', 'No Subject')}
**Date:** {email.get('date', '')}

**Body:**
{email.get('body', '')[:1000]}  # First 1000 chars
    """.strip()

    if classification:
        context += f"""

**Classification:**
- Category: {classification.get('category', 'unknown')}
- Urgency: {classification.get('urgency', 'medium')}
- Reasoning: {classification.get('reasoning', '')}
        """

    context += """

**Your task:**
Analyze this email and generate an appropriate response. Choose the right tone based on the sender and content.
    """

    return context


async def generate_response(
    email: dict,
    classification: dict = None,
    preferred_tone: str = None
) -> EmailResponse:
    """
    Generate email response using orchestrator.

    Args:
        email: Email dictionary
        classification: Optional classification results
        preferred_tone: Optional preferred tone (professional/friendly/brief)

    Returns:
        EmailResponse with generated draft
    """
    from agents import Runner

    orchestrator = create_responder_orchestrator()

    # Format input
    input_text = format_email_for_response(email, classification)

    if preferred_tone:
        input_text += f"\n\n**Preferred tone:** {preferred_tone}"

    # Generate response
    result = await Runner.run(orchestrator, input_text)

    return result.final_output


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
Example usage:

from modules.email.agents.responder import generate_response
from modules.email.tools.gmail_tools import fetch_unread_emails_tool

# Fetch email
emails = fetch_unread_emails_tool("gmail_1", max_results=1)
email = emails[0]

# Generate response
response = await generate_response(
    email=email,
    classification={"category": "normal", "urgency": "medium"},
    preferred_tone="professional"  # Optional
)

print(f"Subject: {response.subject}")
print(f"Tone: {response.tone}")
print(f"Confidence: {response.confidence_score:.2f}")
print(f"Requires Review: {response.requires_review}")
print(f"\nBody:\n{response.body}")
"""
