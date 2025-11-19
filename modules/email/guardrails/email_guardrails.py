"""
Email Guardrails
Input and output guardrails for safe email automation.
Based on patterns from 2_openai/3_lab3.ipynb and community contributions.
"""

from typing import List, Literal
from pydantic import BaseModel, Field
from agents import Agent, Runner, input_guardrail, output_guardrail, GuardrailFunctionOutput


# ============================================================================
# STRUCTURED OUTPUTS FOR GUARDRAILS
# ============================================================================

class PIICheck(BaseModel):
    """PII (Personally Identifiable Information) detection result"""
    contains_pii: bool = Field(description="Whether PII was detected")
    pii_types: List[str] = Field(
        default_factory=list,
        description="Types of PII found (email, phone, ssn, credit_card, address)"
    )
    safe: bool = Field(description="Whether content is safe to process")
    cleaned_content: str = Field(description="Content with PII redacted if needed")
    reasoning: str = Field(description="Explanation of PII findings")


class PhishingCheck(BaseModel):
    """Phishing attempt detection result"""
    is_phishing: bool = Field(description="Whether email appears to be phishing")
    risk_level: Literal["low", "medium", "high"] = Field(description="Phishing risk level")
    indicators: List[str] = Field(
        default_factory=list,
        description="Phishing indicators found"
    )
    safe: bool = Field(description="Whether email is safe to process")
    reasoning: str = Field(description="Explanation of phishing assessment")


class ComplianceCheck(BaseModel):
    """Compliance check for email responses"""
    approved: bool = Field(description="Whether response meets compliance standards")
    risk_level: Literal["low", "medium", "high"] = Field(description="Compliance risk level")
    violations: List[str] = Field(
        default_factory=list,
        description="Compliance violations found"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions to fix violations"
    )
    reasoning: str = Field(description="Explanation of compliance assessment")


# ============================================================================
# GUARDRAIL AGENTS
# ============================================================================

PII_DETECTION_INSTRUCTIONS = """You are a PII (Personally Identifiable Information) detection expert.

**Your job:** Detect and flag sensitive personal information in email content.

**PII Types to Detect:**

1. **Email addresses** (except generic ones like support@, info@)
2. **Phone numbers** (any format: +49 123 456789, (555) 123-4567, etc.)
3. **Physical addresses** (street addresses, postal codes)
4. **SSN / Tax IDs** (patterns like XXX-XX-XXXX, German tax IDs)
5. **Credit card numbers** (16-digit patterns)
6. **Passport numbers**
7. **Bank account numbers** (IBAN, etc.)
8. **Personal health information**
9. **Login credentials** (passwords, API keys)

**Assessment:**

- **safe=True** if:
  - No PII detected
  - Only generic contact info (company emails, public phone numbers)
  - Names without additional identifying info

- **safe=False** if:
  - Personal email addresses
  - Personal phone numbers
  - Home addresses
  - Financial information
  - Health information
  - Credentials

**Output:**
- contains_pii: True/False
- pii_types: List of detected PII types
- safe: True/False for processing
- cleaned_content: Original content with PII redacted as [REDACTED]
- reasoning: Brief explanation

**Examples:**

Input: "Contact me at john.doe@gmail.com or call 555-123-4567"
Output:
- contains_pii: True
- pii_types: ["email", "phone"]
- safe: False
- cleaned_content: "Contact me at [REDACTED EMAIL] or call [REDACTED PHONE]"

Input: "Visit our website or email support@company.com"
Output:
- contains_pii: False
- pii_types: []
- safe: True
- cleaned_content: (same as input)
"""


PHISHING_DETECTION_INSTRUCTIONS = """You are a phishing detection expert for email security.

**Your job:** Identify phishing attempts and suspicious emails.

**Phishing Indicators:**

1. **Urgency tactics:**
   - "Urgent action required"
   - "Account will be suspended"
   - "Limited time offer"
   - "Verify immediately"

2. **Suspicious requests:**
   - Asking for passwords or credentials
   - Requesting personal/financial information
   - Unexpected password reset links
   - Unusual payment requests

3. **Sender mismatch:**
   - Claims to be from bank but uses generic email
   - Impersonating known services (PayPal, Amazon, etc.)
   - Slight misspellings in domain names

4. **Suspicious links:**
   - Shortened URLs (bit.ly, tinyurl)
   - URLs that don't match claimed sender
   - IP addresses instead of domains

5. **Poor quality:**
   - Grammar/spelling errors
   - Generic greetings ("Dear customer")
   - Mismatched branding

6. **Too good to be true:**
   - Lottery wins
   - Unexpected refunds
   - Free money/prizes

**Risk Levels:**

- **Low:** Legitimate email, no indicators
- **Medium:** 1-2 minor indicators, could be legitimate or phishing
- **High:** Multiple indicators, likely phishing

**Assessment:**
- is_phishing: True if likely phishing
- risk_level: low/medium/high
- indicators: List of detected indicators
- safe: False if medium/high risk
- reasoning: Explanation

Mark safe=False for medium or high risk to prevent auto-processing."""


COMPLIANCE_CHECK_INSTRUCTIONS = """You are a compliance checker for email responses.

**Your job:** Ensure email responses meet professional and legal standards.

**Compliance Rules:**

1. **No unsubstantiated claims:**
   - "Guaranteed results"
   - "Best in market" without proof
   - ROI percentages without data
   - Time savings claims without backing

2. **No hyperbole:**
   - "Revolutionary"
   - "#1" or "Best"
   - "Never"/"Always" (absolutes)
   - Excessive superlatives

3. **No pressure tactics:**
   - "Act now or lose out"
   - "Limited time only" (if not true)
   - Artificial urgency

4. **Required elements (if applicable):**
   - Unsubscribe link for marketing emails
   - Company contact information
   - Clear sender identification

5. **Professional tone:**
   - No inappropriate language
   - No all caps (SHOUTING)
   - Proper grammar and spelling

6. **No commitments without authority:**
   - Don't promise features not yet available
   - Don't commit to dates/prices without approval
   - Don't make legal commitments

**Risk Levels:**

- **Low:** No violations, safe to send
- **Medium:** Minor issues, fixable with small edits
- **High:** Major violations, requires human review

**Assessment:**
- approved: True only if risk_level='low'
- risk_level: low/medium/high
- violations: List of specific violations
- suggestions: How to fix violations
- reasoning: Explanation

Only approve (approved=True) if risk level is LOW."""


def create_pii_detection_agent() -> Agent:
    """Create PII detection guardrail agent"""
    return Agent(
        name="PIIDetector",
        instructions=PII_DETECTION_INSTRUCTIONS,
        output_type=PIICheck,
        model="gpt-4o-mini"
    )


def create_phishing_detection_agent() -> Agent:
    """Create phishing detection guardrail agent"""
    return Agent(
        name="PhishingDetector",
        instructions=PHISHING_DETECTION_INSTRUCTIONS,
        output_type=PhishingCheck,
        model="gpt-4o-mini"
    )


def create_compliance_agent() -> Agent:
    """Create compliance check guardrail agent"""
    return Agent(
        name="ComplianceChecker",
        instructions=COMPLIANCE_CHECK_INSTRUCTIONS,
        output_type=ComplianceCheck,
        model="gpt-4o-mini"
    )


# ============================================================================
# INPUT GUARDRAILS (for incoming emails)
# ============================================================================

@input_guardrail
async def check_pii_in_email(ctx, agent, message):
    """
    Input guardrail: Check for PII in incoming email before processing.

    Prevents processing emails with sensitive personal information
    to avoid accidentally including it in responses or logs.
    """
    pii_agent = create_pii_detection_agent()

    result = await Runner.run(pii_agent, message, context=ctx.context)
    pii_check = result.final_output

    # Store PII check results in context
    output_info = {
        'pii_detected': pii_check.contains_pii,
        'pii_types': pii_check.pii_types,
        'reasoning': pii_check.reasoning
    }

    # Trigger tripwire if sensitive PII detected
    # This will stop processing and require human review
    tripwire = not pii_check.safe

    if tripwire:
        print(f"⚠️  INPUT GUARDRAIL: PII detected - {pii_check.pii_types}")
        print(f"   {pii_check.reasoning}")

    return GuardrailFunctionOutput(
        output_info=output_info,
        tripwire_triggered=tripwire
    )


@input_guardrail
async def check_phishing(ctx, agent, message):
    """
    Input guardrail: Check for phishing attempts.

    Prevents auto-processing phishing emails to avoid:
    - Accidentally engaging with attackers
    - Sending auto-replies to malicious addresses
    - Logging credentials if they appear in phishing emails
    """
    phishing_agent = create_phishing_detection_agent()

    result = await Runner.run(phishing_agent, message, context=ctx.context)
    phishing_check = result.final_output

    output_info = {
        'is_phishing': phishing_check.is_phishing,
        'risk_level': phishing_check.risk_level,
        'indicators': phishing_check.indicators,
        'reasoning': phishing_check.reasoning
    }

    # Trigger for medium or high risk
    tripwire = not phishing_check.safe

    if tripwire:
        print(f"⚠️  INPUT GUARDRAIL: Phishing risk detected - {phishing_check.risk_level.upper()}")
        print(f"   Indicators: {', '.join(phishing_check.indicators)}")
        print(f"   {phishing_check.reasoning}")

    return GuardrailFunctionOutput(
        output_info=output_info,
        tripwire_triggered=tripwire
    )


# ============================================================================
# OUTPUT GUARDRAILS (for generated responses)
# ============================================================================

@output_guardrail
async def check_response_compliance(ctx, agent, output):
    """
    Output guardrail: Check generated response for compliance.

    Ensures responses:
    - Don't make unsubstantiated claims
    - Don't use prohibited language
    - Meet professional standards
    - Don't commit to things without authority
    """
    compliance_agent = create_compliance_agent()

    # Extract response text from output
    if hasattr(output, 'body'):
        response_text = f"Subject: {output.subject}\n\nBody:\n{output.body}"
    else:
        response_text = str(output)

    result = await Runner.run(compliance_agent, response_text, context=ctx.context)
    compliance_check = result.final_output

    output_info = {
        'approved': compliance_check.approved,
        'risk_level': compliance_check.risk_level,
        'violations': compliance_check.violations,
        'suggestions': compliance_check.suggestions,
        'reasoning': compliance_check.reasoning
    }

    # Trigger if not approved (medium or high risk)
    tripwire = not compliance_check.approved

    if tripwire:
        print(f"⚠️  OUTPUT GUARDRAIL: Compliance issues detected - {compliance_check.risk_level.upper()}")
        if compliance_check.violations:
            print(f"   Violations: {', '.join(compliance_check.violations[:3])}")  # First 3
        if compliance_check.suggestions:
            print(f"   Suggestions: {compliance_check.suggestions[0]}")  # First suggestion
        print(f"   {compliance_check.reasoning}")

    return GuardrailFunctionOutput(
        output_info=output_info,
        tripwire_triggered=tripwire
    )


# ============================================================================
# STANDALONE GUARDRAIL FUNCTIONS (for manual use)
# ============================================================================

async def check_email_safety(email_content: str) -> dict:
    """
    Check email for PII and phishing (standalone function).

    Returns dict with:
    - pii_check: PIICheck results
    - phishing_check: PhishingCheck results
    - safe: Overall safety assessment
    """
    pii_agent = create_pii_detection_agent()
    phishing_agent = create_phishing_detection_agent()

    # Run both checks in parallel
    import asyncio
    pii_result, phishing_result = await asyncio.gather(
        Runner.run(pii_agent, email_content),
        Runner.run(phishing_agent, email_content)
    )

    pii_check = pii_result.final_output
    phishing_check = phishing_result.final_output

    overall_safe = pii_check.safe and phishing_check.safe

    return {
        'pii_check': pii_check,
        'phishing_check': phishing_check,
        'safe': overall_safe
    }


async def check_response_safety(response_text: str) -> ComplianceCheck:
    """
    Check response for compliance (standalone function).

    Returns ComplianceCheck results.
    """
    compliance_agent = create_compliance_agent()
    result = await Runner.run(compliance_agent, response_text)
    return result.final_output


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example 1: Apply guardrails to an agent

from agents import Agent
from modules.email.guardrails.email_guardrails import (
    check_pii_in_email,
    check_phishing,
    check_response_compliance
)

protected_agent = Agent(
    name="ProtectedResponder",
    instructions="Generate email responses",
    input_guardrails=[check_pii_in_email, check_phishing],
    output_guardrails=[check_response_compliance],
    model="gpt-4o-mini"
)

# If guardrails trigger, agent execution will be blocked


Example 2: Manual safety check

from modules.email.guardrails.email_guardrails import check_email_safety

email_content = "Urgent! Your account will be suspended. Click here to verify: http://suspicious-link.com"

safety_result = await check_email_safety(email_content)

if not safety_result['safe']:
    print("⚠️ Email flagged as unsafe!")
    print(f"PII: {safety_result['pii_check'].contains_pii}")
    print(f"Phishing: {safety_result['phishing_check'].is_phishing}")
"""
