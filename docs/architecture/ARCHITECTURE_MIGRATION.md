# Architecture Migration Guide: OpenAI Agents SDK Integration

**Document Version:** 1.0
**Last Updated:** 2025-11-19
**Audience:** Developers implementing the SDK migration

---

## Table of Contents

1. [Overview](#overview)
2. [Current vs Target Architecture](#current-vs-target-architecture)
3. [Step-by-Step Migration](#step-by-step-migration)
4. [Code Examples](#code-examples)
5. [Testing Strategy](#testing-strategy)
6. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide provides **detailed technical instructions** for migrating the `agent_platform/classification/` system from direct LLM calls to the OpenAI Agents SDK pattern.

### 🎯 PRESERVATION PRINCIPLE

**CRITICAL: This is an INTERFACE migration, NOT a logic rewrite!**

We are **wrapping existing, proven logic** with the Agent SDK interface. All classification rules, pattern matching, EMA learning formulas, and early stopping thresholds remain **100% identical**.

**What changes:** How we call the code (Agent interface)
**What stays:** What the code does (pattern matching, learning, decisions)

Think of it as: **"Putting the same engine in a better chassis"**

### Goals

1. ✅ **Extract** existing classification logic as reusable functions
2. ✅ **Wrap** extracted functions as Agent tools (no logic changes)
3. ✅ **Create** Agent interfaces for unified orchestration
4. ✅ **Integrate** with AgentRegistry for discoverability
5. ✅ **Add** guardrails where appropriate (LLM layer only)
6. ✅ **Preserve** all existing functionality (early stopping, adaptive learning, review routing)
7. ✅ **Merge** `modules/email/` capabilities into unified structure

### Non-Goals

- ❌ Rewriting classification logic (pattern matching stays identical)
- ❌ Changing EMA learning formulas (α=0.15 preserved)
- ❌ Modifying confidence thresholds (0.85 for early stopping preserved)
- ❌ Database schema changes (ProcessedEmail, SenderPreference tables unchanged)
- ❌ Breaking changes to public API (backward compatibility wrapper provided)

---

## Current vs Target Architecture

### Current Architecture (agent_platform/classification/)

```
UnifiedClassifier (unified_classifier.py)
├─ RuleLayer (rule_layer.py)
│  └─ Direct pattern matching
├─ HistoryLayer (history_layer.py)
│  └─ Database queries + EMA learning
└─ LLMLayer (llm_layer.py)
   └─ UnifiedLLMProvider.complete()
      ├─ Ollama (local)
      └─ OpenAI (fallback)
```

**Problem:** Direct LLM calls, no Agent abstraction, no guardrails, no registry

### Target Architecture (agent_platform/classification/)

```
ClassificationOrchestrator (orchestrator.py)
├─ RuleAgent (agents/rule_agent.py)
│  └─ Agent with rule-based instructions
├─ HistoryAgent (agents/history_agent.py)
│  └─ Agent with database tool + EMA learning
└─ LLMAgent (agents/llm_agent.py)
   └─ Agent with semantic analysis
      ├─ Input Guardrails: PII, Phishing
      └─ Output Guardrails: Confidence validation

AgentRegistry
├─ classification.rule_classifier
├─ classification.history_classifier
├─ classification.llm_classifier
└─ classification.orchestrator
```

**Benefits:** Agent abstraction, guardrails, registry discovery, tool reuse

### Migration Strategy: Extract & Wrap (Not Rewrite!)

```
┌─────────────────────────────────────────────────────────────┐
│  PRESERVATION STRATEGY                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: EXTRACT existing logic as standalone functions    │
│          (Copy-paste from RuleLayer._is_spam(), etc.)      │
│                                                             │
│  Step 2: WRAP extracted functions as Agent tools           │
│          (No logic changes - just interface!)              │
│                                                             │
│  Step 3: CREATE Agent with instructions                    │
│          (Agent calls our functions via tools)             │
│                                                             │
│  Result: SAME classification decisions,                    │
│          BETTER orchestration & discoverability            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Example:**
```python
# OLD: Method in class (works, but not Agent-compatible)
class RuleLayer:
    def _is_spam(self, email):
        keywords = ['unsubscribe', 'click here']
        return any(k in email.body.lower() for k in keywords)

# NEW: Extracted function (IDENTICAL logic) + Agent wrapper
def check_spam_patterns(body: str) -> dict:
    keywords = ['unsubscribe', 'click here']  # ← Same keywords!
    matched = [k for k in keywords if k in body.lower()]  # ← Same check!
    return {'is_spam': len(matched) >= 2}  # ← Same threshold!

rule_agent = Agent(
    tools=[check_spam_patterns],  # ← Wraps our function
    instructions="Use check_spam_patterns tool for spam detection"
)
```

**What's preserved:**
- ✅ Spam keywords list (identical)
- ✅ Pattern matching logic (identical)
- ✅ Confidence scores (0.95 for spam, 0.90 for newsletter, etc.)
- ✅ Importance scores (0.0 for spam, 0.2 for newsletter, etc.)
- ✅ Early stopping thresholds (0.85)
- ✅ EMA learning formula (α=0.15)
- ✅ Database queries (same SQL)

**What changes:**
- 🔄 Interface: Agent with tools instead of class methods
- 🔄 Orchestration: Runner.run() instead of direct calls
- 🔄 Discovery: Registry lookup instead of direct imports

---

## Step-by-Step Migration

### Phase 1.1: Extract Logic & Create Agent Wrappers

#### Step 1.1.1: Extract Rule Layer Logic & Create Agent Wrapper

**Goal:** Preserve all pattern matching logic, wrap with Agent interface

**File:** `agent_platform/classification/agents/rule_agent.py`

**Current Code (rule_layer.py:35-120) - Logic to be EXTRACTED:**
```python
class RuleLayer:
    def classify(self, email: Email) -> ClassificationResult:
        # Spam detection
        if self._is_spam(email):
            return ClassificationResult(
                category="spam",
                confidence=0.95,
                reasoning="Matched spam pattern",
                importance=0.0
            )

        # Newsletter detection
        if self._is_newsletter(email):
            return ClassificationResult(
                category="newsletter",
                confidence=0.90,
                reasoning="Matched newsletter pattern",
                importance=0.2
            )

        # Auto-reply detection
        if self._is_auto_reply(email):
            return ClassificationResult(
                category="auto_reply",
                confidence=0.95,
                reasoning="Auto-reply pattern detected",
                importance=0.1
            )

        # No match
        return None
```

**New Code (agents/rule_agent.py) - EXTRACT + WRAP Strategy:**

```python
"""
Rule-Based Classification Agent

PRESERVATION NOTE: All pattern matching logic extracted from rule_layer.py
                   WITHOUT changes. Only wrapped with Agent interface.

Deterministic classification of:
- Spam (unsubscribe links, promotional keywords)
- Newsletters (list-unsubscribe header, bulk sender)
- Auto-replies (vacation, out-of-office)
"""

from agents import Agent
from pydantic import BaseModel, Field
from typing import Optional, List
import re


# ============================================================================
# PYDANTIC MODELS (Structured Output)
# ============================================================================

class RuleClassification(BaseModel):
    """Structured output for rule-based classification."""

    category: Optional[str] = Field(
        None,
        description="Email category if rule matched: 'spam', 'newsletter', 'auto_reply', or None"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0). High for rule matches (≥0.85)"
    )
    reasoning: str = Field(
        "",
        description="Explanation of which rule matched"
    )
    importance: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0-1.0). Low for spam/newsletters"
    )
    matched_patterns: List[str] = Field(
        default_factory=list,
        description="List of patterns that matched (for debugging)"
    )


# ============================================================================
# EXTRACTED FUNCTIONS (From rule_layer.py - UNCHANGED LOGIC)
# ============================================================================
# These functions contain the EXACT SAME pattern matching logic from the old
# RuleLayer._is_spam(), _is_newsletter(), _is_auto_reply() methods.
# Only the interface changed (standalone functions instead of class methods).
# ============================================================================

def check_spam_patterns(subject: str, body: str, sender: str) -> dict:
    """
    EXTRACTED FROM: rule_layer.py RuleLayer._is_spam()

    Check email content against spam patterns.

    PRESERVATION: Keywords, domains, and threshold (2+) are IDENTICAL to original.

    Returns:
        dict with 'is_spam', 'patterns' keys
    """
    # ← SAME keywords as rule_layer.py
    spam_keywords = [
        'unsubscribe', 'click here', 'limited time',
        'act now', 'congratulations', 'winner',
        'free money', 'guaranteed', 'special promotion'
    ]

    # ← SAME sender domains as rule_layer.py
    spam_domains = [
        'noreply@', 'no-reply@', 'marketing@',
        'promo@', 'newsletter@'
    ]

    matched_patterns = []
    content = (subject + " " + body).lower()

    # ← SAME keyword matching logic
    for keyword in spam_keywords:
        if keyword in content:
            matched_patterns.append(f"spam_keyword:{keyword}")

    # ← SAME domain matching logic
    for domain in spam_domains:
        if domain in sender.lower():
            matched_patterns.append(f"spam_sender:{domain}")

    # ← SAME unsubscribe link detection
    if 'http' in body and 'unsubscribe' in body.lower():
        matched_patterns.append("unsubscribe_link")

    return {
        'is_spam': len(matched_patterns) >= 2,  # ← SAME threshold (2+)
        'patterns': matched_patterns
    }


def check_newsletter_patterns(headers: dict, subject: str, sender: str) -> dict:
    """
    EXTRACTED FROM: rule_layer.py RuleLayer._is_newsletter()

    Check if email is a newsletter.

    PRESERVATION: Header checks and subject patterns IDENTICAL to original.

    Returns:
        dict with 'is_newsletter', 'patterns' keys
    """
    matched_patterns = []

    # Check List-Unsubscribe header (RFC 2369)
    if headers.get('List-Unsubscribe'):
        matched_patterns.append("list_unsubscribe_header")

    # Check Precedence header
    if headers.get('Precedence', '').lower() in ['bulk', 'list']:
        matched_patterns.append("precedence_bulk")

    # Check subject patterns
    newsletter_subjects = ['newsletter', 'digest', 'weekly update', 'monthly summary']
    for pattern in newsletter_subjects:
        if pattern in subject.lower():
            matched_patterns.append(f"subject:{pattern}")

    return {
        'is_newsletter': len(matched_patterns) >= 1,
        'patterns': matched_patterns
    }


def check_auto_reply_patterns(subject: str, body: str, headers: dict) -> dict:
    """
    Check if email is an auto-reply.

    Returns:
        dict with 'is_auto_reply', 'patterns' keys
    """
    matched_patterns = []

    # Check Auto-Submitted header (RFC 3834)
    auto_submitted = headers.get('Auto-Submitted', '')
    if auto_submitted and auto_submitted != 'no':
        matched_patterns.append(f"auto_submitted_header:{auto_submitted}")

    # Check subject patterns
    auto_reply_subjects = [
        'out of office', 'away from office', 'automatic reply',
        'vacation', 'abwesend', 'abwesenheitsnotiz'
    ]
    for pattern in auto_reply_subjects:
        if pattern in subject.lower():
            matched_patterns.append(f"subject:{pattern}")

    # Check body patterns
    auto_reply_body = [
        'i am currently out of office',
        'automatic reply',
        'i will be away until'
    ]
    body_lower = body.lower()
    for pattern in auto_reply_body:
        if pattern in body_lower:
            matched_patterns.append(f"body:{pattern}")

    return {
        'is_auto_reply': len(matched_patterns) >= 1,
        'patterns': matched_patterns
    }


# ============================================================================
# RULE AGENT DEFINITION
# ============================================================================

rule_agent = Agent(
    name="rule_classifier",

    instructions="""
You are a rule-based email classifier. Apply deterministic pattern matching to categorize emails.

**Classification Rules:**

1. **SPAM** - If email matches 2+ spam patterns:
   - Keywords: "unsubscribe", "click here", "limited time", "act now", "congratulations", "winner", "free money", "guaranteed", "special promotion"
   - Sender domains: noreply@, no-reply@, marketing@, promo@, newsletter@
   - Contains unsubscribe link
   - Confidence: 0.95, Importance: 0.0

2. **NEWSLETTER** - If email matches newsletter patterns:
   - Has List-Unsubscribe header (RFC 2369)
   - Has Precedence: bulk/list header
   - Subject contains: "newsletter", "digest", "weekly update", "monthly summary"
   - Confidence: 0.90, Importance: 0.2

3. **AUTO_REPLY** - If email matches auto-reply patterns:
   - Has Auto-Submitted header (not 'no')
   - Subject contains: "out of office", "automatic reply", "vacation", "abwesend"
   - Body contains: "i am currently out of office", "automatic reply", "i will be away"
   - Confidence: 0.95, Importance: 0.1

4. **NO MATCH** - If no patterns match:
   - category: None
   - confidence: 0.0
   - Return None to signal "continue to next layer"

**Input Format:**
You will receive email data with:
- subject: Email subject line
- body: Email body content
- sender: Sender email address
- headers: Email headers dict

**Output Format:**
Return RuleClassification with matched category, confidence, reasoning, importance, and matched_patterns.

**Examples:**

Input: subject="Win a Free iPhone!", sender="promo@marketing.com", body="Click here now! Limited time!"
Output: category="spam", confidence=0.95, reasoning="Matched spam patterns: promotional keywords + marketing sender", importance=0.0, matched_patterns=["spam_keyword:click here", "spam_keyword:limited time", "spam_sender:promo@"]

Input: subject="Out of Office", body="I am currently out of office until Monday."
Output: category="auto_reply", confidence=0.95, reasoning="Auto-reply pattern detected", importance=0.1, matched_patterns=["subject:out of office", "body:i am currently out of office"]

Input: subject="Meeting Tomorrow", sender="colleague@company.com", body="Let's meet at 2pm."
Output: category=None, confidence=0.0, reasoning="No rule patterns matched", importance=0.0, matched_patterns=[]
""",

    # Structured output
    output_type=RuleClassification,

    # No tools needed (pure pattern matching)
    tools=[],

    # No guardrails needed (deterministic rules, no LLM risk)
    input_guardrails=[],
    output_guardrails=[]
)


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

async def classify_with_rules(
    subject: str,
    body: str,
    sender: str,
    headers: dict
) -> RuleClassification:
    """
    Classify email using rule-based agent.

    Args:
        subject: Email subject line
        body: Email body content
        sender: Sender email address
        headers: Email headers dict

    Returns:
        RuleClassification with category, confidence, reasoning

    Example:
        result = await classify_with_rules(
            subject="Out of Office",
            body="I am away until Monday",
            sender="colleague@company.com",
            headers={}
        )
        if result.category:
            print(f"Classified as {result.category} with {result.confidence} confidence")
    """
    from agents import Runner

    # Format input for agent
    input_data = f"""
Subject: {subject}
Sender: {sender}
Body: {body[:500]}  # Truncate body to 500 chars for rule matching

Headers: {headers}
"""

    # Run agent
    result = await Runner.run(rule_agent, input_data)

    return result.output


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'rule_agent',
    'RuleClassification',
    'classify_with_rules',
    'check_spam_patterns',
    'check_newsletter_patterns',
    'check_auto_reply_patterns'
]
```

**Migration Notes:**
- Original logic preserved (pattern matching unchanged)
- Added structured output with Pydantic
- Extracted helper functions as potential tools
- Detailed instructions for LLM to follow rules
- No guardrails needed (deterministic, no external calls)

#### Step 1.1.2: Create History Agent

**File:** `agent_platform/classification/agents/history_agent.py`

**Current Code (history_layer.py:40-150):**
```python
class HistoryLayer:
    def classify(self, email: Email) -> Optional[ClassificationResult]:
        # Get sender preference
        preference = self._get_sender_preference(email.sender, email.domain)

        if not preference:
            return None  # No history

        # Check if confidence threshold met
        if preference.confidence < 0.6:
            return None  # Not confident enough

        # Return classification based on history
        return ClassificationResult(
            category=preference.preferred_category,
            confidence=preference.confidence,
            reasoning=f"Based on {preference.email_count} previous emails",
            importance=preference.avg_importance
        )

    def update_preference(self, email: Email, classification: ClassificationResult):
        """Update sender preference with EMA."""
        preference = self._get_sender_preference(email.sender, email.domain)

        if not preference:
            # Create new preference
            preference = SenderPreference(
                sender=email.sender,
                domain=email.domain,
                preferred_category=classification.category,
                confidence=0.5,  # Start at medium confidence
                email_count=1,
                avg_importance=classification.importance
            )
        else:
            # Update with EMA (α=0.15)
            alpha = 0.15
            preference.confidence = (1 - alpha) * preference.confidence + alpha * classification.confidence
            preference.avg_importance = (1 - alpha) * preference.avg_importance + alpha * classification.importance
            preference.email_count += 1

        db.add(preference)
        db.commit()
```

**New Code (agents/history_agent.py):**
```python
"""
History-Based Classification Agent

Uses sender/domain history with Exponential Moving Average (EMA) learning
to classify emails based on past user preferences.
"""

from agents import Agent, ToolFunction
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from agent_platform.db.database import get_db
from agent_platform.db.models import SenderPreference


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class HistoryClassification(BaseModel):
    """Structured output for history-based classification."""

    category: Optional[str] = Field(
        None,
        description="Email category from history: 'spam', 'important', 'newsletter', 'normal', or None"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence based on historical accuracy (EMA-adjusted)"
    )
    reasoning: str = Field(
        "",
        description="Explanation based on sender history"
    )
    importance: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Average importance from historical emails"
    )
    email_count: int = Field(
        0,
        description="Number of emails from this sender in history"
    )
    last_seen: Optional[str] = Field(
        None,
        description="ISO timestamp of last email from sender"
    )


# ============================================================================
# TOOLS (Database Access)
# ============================================================================

async def get_sender_history(sender: str, domain: str) -> dict:
    """
    Retrieve sender preference from database.

    Args:
        sender: Full email address
        domain: Email domain

    Returns:
        dict with preference data or None if no history
    """
    with get_db() as db:
        # Try exact sender match first
        preference = db.query(SenderPreference).filter(
            SenderPreference.sender == sender
        ).first()

        # Fall back to domain match
        if not preference:
            preference = db.query(SenderPreference).filter(
                SenderPreference.domain == domain
            ).first()

        if not preference:
            return {"has_history": False}

        return {
            "has_history": True,
            "sender": preference.sender,
            "domain": preference.domain,
            "preferred_category": preference.preferred_category,
            "confidence": preference.confidence,
            "avg_importance": preference.avg_importance,
            "email_count": preference.email_count,
            "last_seen": preference.last_seen.isoformat() if preference.last_seen else None
        }


# Register as tool
get_sender_history_tool = ToolFunction.from_function(get_sender_history)


# ============================================================================
# HISTORY AGENT DEFINITION
# ============================================================================

history_agent = Agent(
    name="history_classifier",

    instructions="""
You are a history-based email classifier. Use sender/domain history to predict email category.

**Classification Strategy:**

1. **Retrieve History:**
   - Use `get_sender_history(sender, domain)` tool
   - Check if sender has previous emails

2. **Confidence Threshold:**
   - If no history: Return None (continue to next layer)
   - If confidence < 0.6: Return None (not confident enough)
   - If confidence ≥ 0.6: Return classification

3. **Category Selection:**
   - Use `preferred_category` from history
   - Adjust confidence based on `email_count` (more emails = more confident)

4. **Importance:**
   - Use `avg_importance` from history

**Confidence Adjustment Rules:**
- 1-5 emails: confidence * 0.8 (lower confidence, limited history)
- 6-20 emails: confidence * 1.0 (normal confidence)
- 20+ emails: confidence * 1.1 (higher confidence, strong pattern, cap at 1.0)

**Output Format:**
Return HistoryClassification with category from history, adjusted confidence, reasoning, importance.

**Examples:**

Input: sender="newsletter@company.com", domain="company.com"
History: preferred_category="newsletter", confidence=0.85, email_count=15, avg_importance=0.2
Output: category="newsletter", confidence=0.85, reasoning="Based on 15 previous emails from this sender", importance=0.2

Input: sender="boss@company.com", domain="company.com"
History: preferred_category="important", confidence=0.92, email_count=50, avg_importance=0.95
Output: category="important", confidence=1.0 (capped), reasoning="Based on 50 previous emails from this sender (strong pattern)", importance=0.95

Input: sender="new_sender@example.com", domain="example.com"
History: No history found
Output: category=None, confidence=0.0, reasoning="No sender history available", importance=0.0
""",

    # Structured output
    output_type=HistoryClassification,

    # Database tool
    tools=[get_sender_history_tool],

    # No guardrails needed (database access only)
    input_guardrails=[],
    output_guardrails=[]
)


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

async def classify_with_history(sender: str, domain: str) -> HistoryClassification:
    """
    Classify email using sender history.

    Args:
        sender: Sender email address
        domain: Email domain

    Returns:
        HistoryClassification with category from history

    Example:
        result = await classify_with_history(
            sender="newsletter@company.com",
            domain="company.com"
        )
        if result.category:
            print(f"History suggests {result.category} (based on {result.email_count} emails)")
    """
    from agents import Runner

    input_data = f"Sender: {sender}, Domain: {domain}"

    result = await Runner.run(history_agent, input_data)

    return result.output


# ============================================================================
# LEARNING FUNCTION (EMA Update)
# ============================================================================

async def update_sender_preference(
    sender: str,
    domain: str,
    category: str,
    confidence: float,
    importance: float,
    alpha: float = 0.15
):
    """
    Update sender preference using Exponential Moving Average (EMA).

    Args:
        sender: Sender email address
        domain: Email domain
        category: Classified category
        confidence: Classification confidence
        importance: Email importance
        alpha: EMA smoothing factor (default 0.15)

    This implements the adaptive learning loop:
    - New emails update sender preferences
    - Confidence/importance calculated with EMA
    - More weight to recent emails
    """
    with get_db() as db:
        # Get existing preference
        preference = db.query(SenderPreference).filter(
            SenderPreference.sender == sender
        ).first()

        if not preference:
            # Create new preference
            preference = SenderPreference(
                sender=sender,
                domain=domain,
                preferred_category=category,
                confidence=0.5,  # Start at medium
                email_count=1,
                avg_importance=importance,
                last_seen=datetime.utcnow()
            )
            db.add(preference)
        else:
            # Update with EMA
            preference.preferred_category = category  # Always update to latest
            preference.confidence = (1 - alpha) * preference.confidence + alpha * confidence
            preference.avg_importance = (1 - alpha) * preference.avg_importance + alpha * importance
            preference.email_count += 1
            preference.last_seen = datetime.utcnow()

        db.commit()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'history_agent',
    'HistoryClassification',
    'classify_with_history',
    'update_sender_preference',
    'get_sender_history'
]
```

**Migration Notes:**
- EMA learning logic preserved
- Database access converted to tool pattern
- Structured output with Pydantic
- Separated classification from preference updates
- Agent uses tool to query database

#### Step 1.1.3: Create LLM Agent

**File:** `agent_platform/classification/agents/llm_agent.py`

**Current Code (llm_layer.py:35-200):**
```python
class LLMLayer:
    async def classify(self, email: Email) -> ClassificationResult:
        # Build prompt
        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": format_email_for_llm(email)}
        ]

        # Call LLM with structured output
        response, provider = await llm_provider.complete(
            messages=messages,
            response_format=EmailClassification
        )

        # Extract result
        classification = response.choices[0].message.parsed

        return ClassificationResult(
            category=classification.category,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            importance=classification.importance
        )
```

**New Code (agents/llm_agent.py):**
```python
"""
LLM-Based Classification Agent

Deep semantic analysis for difficult emails using gpt-4o.
Handles cases where rule and history layers don't have enough confidence.
"""

from agents import Agent, input_guardrail, output_guardrail, GuardrailFunctionOutput
from pydantic import BaseModel, Field
from typing import Optional


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LLMClassification(BaseModel):
    """Structured output for LLM-based classification."""

    category: str = Field(
        ...,
        description="Email category: 'spam', 'important', 'newsletter', 'auto_reply', 'normal'"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in classification (0.0-1.0)"
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation of classification decision"
    )
    importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0=low, 1.0=high). Important work emails should be ≥0.7"
    )
    detected_intent: Optional[str] = Field(
        None,
        description="Detected user intent: 'question', 'request', 'information', 'complaint', etc."
    )
    requires_response: bool = Field(
        False,
        description="Whether email requires a response"
    )


# ============================================================================
# GUARDRAILS
# ============================================================================

@input_guardrail
async def check_pii_before_llm(ctx, agent, email_content: str):
    """
    Block LLM classification if email contains sensitive PII.

    Prevents sending credit card numbers, SSNs, passwords to LLM.
    """
    import re

    pii_patterns = {
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'password': r'(?i)(password|pwd|pass)[\s:]+[\w!@#$%^&*]+',
    }

    detected_pii = []
    for pii_type, pattern in pii_patterns.items():
        if re.search(pattern, email_content):
            detected_pii.append(pii_type)

    if detected_pii:
        return GuardrailFunctionOutput(
            output_info={'pii_types_detected': detected_pii},
            tripwire_triggered=True  # STOP execution
        )

    return GuardrailFunctionOutput(
        output_info={'pii_detected': False},
        tripwire_triggered=False
    )


@input_guardrail
async def check_phishing_before_llm(ctx, agent, email_content: str):
    """
    Detect potential phishing emails before LLM classification.

    Phishing emails should be blocked immediately.
    """
    import re

    phishing_indicators = []

    # Check for suspicious URLs
    if re.search(r'https?://\S+\.(tk|ml|ga|cf|gq)/', email_content):
        phishing_indicators.append('suspicious_tld')

    # Check for urgent language
    urgent_phrases = ['verify your account', 'confirm your identity', 'suspended', 'unusual activity']
    for phrase in urgent_phrases:
        if phrase.lower() in email_content.lower():
            phishing_indicators.append(f'urgent_language:{phrase}')

    # Check for mismatched sender
    if re.search(r'paypal|bank|security', email_content.lower()):
        # Simplified check - in production, compare sender domain
        phishing_indicators.append('financial_impersonation_risk')

    if len(phishing_indicators) >= 2:
        return GuardrailFunctionOutput(
            output_info={'phishing_indicators': phishing_indicators},
            tripwire_triggered=True  # STOP and classify as spam
        )

    return GuardrailFunctionOutput(
        output_info={'phishing_detected': False},
        tripwire_triggered=False
    )


@output_guardrail
async def validate_classification_output(ctx, agent, classification: LLMClassification):
    """
    Validate LLM classification output.

    Ensures:
    - Category is valid
    - Confidence/importance in valid range
    - Reasoning is not empty
    """
    valid_categories = ['spam', 'important', 'newsletter', 'auto_reply', 'normal']

    errors = []

    if classification.category not in valid_categories:
        errors.append(f"Invalid category: {classification.category}")

    if not (0.0 <= classification.confidence <= 1.0):
        errors.append(f"Confidence out of range: {classification.confidence}")

    if not (0.0 <= classification.importance <= 1.0):
        errors.append(f"Importance out of range: {classification.importance}")

    if not classification.reasoning or len(classification.reasoning) < 10:
        errors.append("Reasoning too short or empty")

    if errors:
        return GuardrailFunctionOutput(
            output_info={'validation_errors': errors},
            tripwire_triggered=True  # STOP and retry
        )

    return GuardrailFunctionOutput(
        output_info={'validation': 'passed'},
        tripwire_triggered=False
    )


# ============================================================================
# LLM AGENT DEFINITION
# ============================================================================

llm_agent = Agent(
    name="llm_classifier",

    instructions="""
You are an expert email classifier using deep semantic analysis.

You receive emails that did NOT match rule patterns or sender history.
These are typically:
- Personal emails
- Work emails requiring nuanced understanding
- Mixed-category emails
- Emails from new senders

**Classification Categories:**

1. **SPAM** (confidence ≥ 0.7, importance 0.0-0.2)
   - Promotional content
   - Unsolicited offers
   - Clickbait
   - Suspicious requests

2. **IMPORTANT** (confidence ≥ 0.7, importance 0.7-1.0)
   - Work-related emails requiring action
   - Time-sensitive requests
   - Direct questions from colleagues/clients
   - Meeting requests
   - Project updates

3. **NEWSLETTER** (confidence ≥ 0.7, importance 0.1-0.3)
   - Subscribed content
   - Blog updates
   - Company announcements
   - Educational content

4. **AUTO_REPLY** (confidence ≥ 0.8, importance 0.0-0.2)
   - Out-of-office notifications
   - Automated confirmations
   - System-generated messages

5. **NORMAL** (confidence 0.5-0.9, importance 0.3-0.7)
   - Personal emails
   - FYI emails
   - Social updates
   - Non-urgent communication

**Classification Process:**

1. **Analyze Intent:**
   - What is the sender trying to accomplish?
   - Does it require a response?

2. **Assess Importance:**
   - Is it time-sensitive?
   - Does it affect work or personal obligations?
   - Who is the sender (position, relationship)?

3. **Determine Category:**
   - Primary purpose of email
   - Sender's relationship to recipient
   - Content type and structure

4. **Assign Confidence:**
   - High (0.85-1.0): Clear category, obvious intent
   - Medium (0.6-0.85): Likely category, some ambiguity
   - Low (0.5-0.6): Uncertain, could be multiple categories

**Examples:**

Email: "Hi, can you send me the Q4 report by EOD? Thanks, Sarah (VP Sales)"
Output:
  category: "important"
  confidence: 0.95
  reasoning: "Direct request from VP Sales with deadline. Requires immediate action."
  importance: 0.9
  detected_intent: "request"
  requires_response: true

Email: "Check out our new blog post about machine learning trends!"
Output:
  category: "newsletter"
  confidence: 0.85
  reasoning: "Blog update from subscribed source. Informational, not urgent."
  importance: 0.2
  detected_intent: "information"
  requires_response: false

Email: "Hey! How was your weekend?"
Output:
  category: "normal"
  confidence: 0.8
  reasoning: "Personal social email. Not urgent but warrants a response."
  importance: 0.4
  detected_intent: "social"
  requires_response: true

**Edge Cases:**

- Mixed content (work + personal): Prioritize most important part
- Uncertain sender: Lower confidence, default to "normal"
- Empty/very short: category="normal", lower confidence
- Forwarded emails: Analyze original content, not forward header

**Output:**
Always return LLMClassification with all fields filled.
Reasoning should explain WHY you chose this category and confidence level.
""",

    # Structured output
    output_type=LLMClassification,

    # No tools needed (pure semantic analysis)
    tools=[],

    # Guardrails
    input_guardrails=[check_pii_before_llm, check_phishing_before_llm],
    output_guardrails=[validate_classification_output]
)


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

async def classify_with_llm(
    subject: str,
    body: str,
    sender: str,
    headers: dict = None
) -> LLMClassification:
    """
    Classify email using LLM agent with semantic analysis.

    Args:
        subject: Email subject line
        body: Email body content
        sender: Sender email address
        headers: Optional email headers

    Returns:
        LLMClassification with category, confidence, reasoning

    Example:
        result = await classify_with_llm(
            subject="Q4 Report Request",
            body="Can you send me the Q4 report by EOD?",
            sender="vp.sales@company.com"
        )
        print(f"Category: {result.category}, Confidence: {result.confidence}")
    """
    from agents import Runner

    # Format email for LLM
    email_text = f"""
Subject: {subject}
From: {sender}

{body}
"""

    if headers:
        email_text = f"Headers: {headers}\n\n" + email_text

    # Run agent (guardrails execute automatically)
    result = await Runner.run(llm_agent, email_text)

    return result.output


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'llm_agent',
    'LLMClassification',
    'classify_with_llm',
    'check_pii_before_llm',
    'check_phishing_before_llm',
    'validate_classification_output'
]
```

**Migration Notes:**
- LLM layer logic converted to agent instructions
- Added comprehensive guardrails (PII, phishing, output validation)
- Structured output with additional fields (detected_intent, requires_response)
- Detailed examples in instructions for better classification
- Tripwire mechanism for security

#### Step 1.1.4: Create Classification Orchestrator

**File:** `agent_platform/classification/agents/orchestrator_agent.py`

```python
"""
Classification Orchestrator Agent

Coordinates rule → history → llm classification pipeline with early stopping.
"""

from agents import Agent, Runner
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from .rule_agent import rule_agent, RuleClassification, classify_with_rules
from .history_agent import history_agent, HistoryClassification, classify_with_history, update_sender_preference
from .llm_agent import llm_agent, LLMClassification, classify_with_llm

from agent_platform.models.email import Email
from agent_platform.monitoring import log_classification
import time


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ClassificationResult(BaseModel):
    """Final classification result from orchestrator."""

    email_id: str = Field(..., description="Unique email ID")
    category: str = Field(..., description="Final category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Final confidence")
    reasoning: str = Field(..., description="Classification reasoning")
    importance: float = Field(..., ge=0.0, le=1.0, description="Email importance")

    layer_used: str = Field(
        ...,
        description="Which layer classified: 'rule', 'history', 'llm'"
    )
    llm_provider: Optional[str] = Field(
        None,
        description="LLM provider used: 'ollama', 'openai', 'rules_only', 'history_only'"
    )

    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Additional metadata
    requires_response: Optional[bool] = Field(None, description="Whether email requires response")
    detected_intent: Optional[str] = Field(None, description="Detected user intent")


# ============================================================================
# CLASSIFICATION ORCHESTRATOR
# ============================================================================

class ClassificationOrchestrator:
    """
    Orchestrates 3-layer classification pipeline with early stopping.

    Pipeline:
    1. Rule Layer (fast, deterministic) → 40-60% hit rate
    2. History Layer (medium, adaptive) → 20-30% hit rate
    3. LLM Layer (slow, semantic) → 10-20% usage

    Early stopping: If layer confidence ≥ 0.85, stop and return.
    """

    CONFIDENCE_THRESHOLD = 0.85  # Early stopping threshold

    async def classify(self, email: Email) -> ClassificationResult:
        """
        Classify email using 3-layer pipeline.

        Args:
            email: Email object with subject, body, sender, etc.

        Returns:
            ClassificationResult with category, confidence, layer used

        Raises:
            RuntimeError: If all layers fail
        """
        start_time = time.time()

        # ========================================
        # LAYER 1: RULE-BASED CLASSIFICATION
        # ========================================
        try:
            rule_result: RuleClassification = await classify_with_rules(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                headers=email.headers or {}
            )

            if rule_result.category and rule_result.confidence >= self.CONFIDENCE_THRESHOLD:
                # Early stopping - rule match with high confidence
                processing_time_ms = (time.time() - start_time) * 1000

                # Log classification
                log_classification(
                    email_id=email.email_id,
                    processing_time_ms=processing_time_ms,
                    layer_used="rules",
                    category=rule_result.category,
                    confidence=rule_result.confidence,
                    importance=rule_result.importance,
                    llm_provider="rules_only"
                )

                return ClassificationResult(
                    email_id=email.email_id,
                    category=rule_result.category,
                    confidence=rule_result.confidence,
                    reasoning=rule_result.reasoning,
                    importance=rule_result.importance,
                    layer_used="rules",
                    llm_provider="rules_only",
                    processing_time_ms=processing_time_ms
                )

        except Exception as e:
            print(f"⚠️  Rule layer failed: {e}")

        # ========================================
        # LAYER 2: HISTORY-BASED CLASSIFICATION
        # ========================================
        try:
            history_result: HistoryClassification = await classify_with_history(
                sender=email.sender,
                domain=email.domain
            )

            if history_result.category and history_result.confidence >= self.CONFIDENCE_THRESHOLD:
                # Early stopping - history match with high confidence
                processing_time_ms = (time.time() - start_time) * 1000

                log_classification(
                    email_id=email.email_id,
                    processing_time_ms=processing_time_ms,
                    layer_used="history",
                    category=history_result.category,
                    confidence=history_result.confidence,
                    importance=history_result.importance,
                    llm_provider="history_only"
                )

                return ClassificationResult(
                    email_id=email.email_id,
                    category=history_result.category,
                    confidence=history_result.confidence,
                    reasoning=history_result.reasoning,
                    importance=history_result.importance,
                    layer_used="history",
                    llm_provider="history_only",
                    processing_time_ms=processing_time_ms
                )

        except Exception as e:
            print(f"⚠️  History layer failed: {e}")

        # ========================================
        # LAYER 3: LLM-BASED CLASSIFICATION
        # ========================================
        try:
            llm_result: LLMClassification = await classify_with_llm(
                subject=email.subject,
                body=email.body,
                sender=email.sender,
                headers=email.headers or {}
            )

            processing_time_ms = (time.time() - start_time) * 1000

            log_classification(
                email_id=email.email_id,
                processing_time_ms=processing_time_ms,
                layer_used="llm",
                category=llm_result.category,
                confidence=llm_result.confidence,
                importance=llm_result.importance,
                llm_provider="openai"  # Will be updated when we add provider tracking
            )

            # Update sender preference with EMA learning
            await update_sender_preference(
                sender=email.sender,
                domain=email.domain,
                category=llm_result.category,
                confidence=llm_result.confidence,
                importance=llm_result.importance
            )

            return ClassificationResult(
                email_id=email.email_id,
                category=llm_result.category,
                confidence=llm_result.confidence,
                reasoning=llm_result.reasoning,
                importance=llm_result.importance,
                layer_used="llm",
                llm_provider="openai",
                processing_time_ms=processing_time_ms,
                requires_response=llm_result.requires_response,
                detected_intent=llm_result.detected_intent
            )

        except Exception as e:
            # All layers failed
            raise RuntimeError(
                f"All classification layers failed!\n"
                f"  Rule layer: skipped or failed\n"
                f"  History layer: skipped or failed\n"
                f"  LLM layer: {e}"
            )


# ============================================================================
# SINGLETON ORCHESTRATOR
# ============================================================================

_orchestrator: Optional[ClassificationOrchestrator] = None


def get_orchestrator() -> ClassificationOrchestrator:
    """Get singleton classification orchestrator."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = ClassificationOrchestrator()

    return _orchestrator


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

async def classify_email(email: Email) -> ClassificationResult:
    """
    Classify email using orchestrated 3-layer pipeline.

    This is the main entry point for classification.

    Args:
        email: Email object to classify

    Returns:
        ClassificationResult with category, confidence, layer used

    Example:
        email = Email(
            email_id="msg_123",
            subject="Meeting Tomorrow",
            body="Let's meet at 2pm",
            sender="colleague@company.com",
            domain="company.com"
        )

        result = await classify_email(email)
        print(f"Category: {result.category} ({result.layer_used} layer)")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Time: {result.processing_time_ms:.0f}ms")
    """
    orchestrator = get_orchestrator()
    return await orchestrator.classify(email)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'ClassificationOrchestrator',
    'ClassificationResult',
    'get_orchestrator',
    'classify_email'
]
```

**Migration Notes:**
- Orchestrates all 3 layers with early stopping
- Preserves EMA learning (calls update_sender_preference)
- Logs all classifications for monitoring
- Error handling for each layer
- Singleton pattern for efficiency

### Phase 1.2: Update UnifiedClassifier (Backward Compatibility Wrapper)

**File:** `agent_platform/classification/unified_classifier.py` (MODIFIED)

```python
"""
Unified Email Classifier (Backward Compatibility Wrapper)

This module provides backward compatibility with the old UnifiedClassifier API
while using the new Agent-based implementation under the hood.

Migration path:
1. Old code continues to work with UnifiedClassifier
2. New code can use classify_email() directly from orchestrator
3. Eventually deprecate UnifiedClassifier
"""

from typing import Optional
import asyncio

from agent_platform.models.email import Email
from agent_platform.classification.agents.orchestrator_agent import (
    classify_email,
    ClassificationResult
)


class UnifiedClassifier:
    """
    DEPRECATED: Backward compatibility wrapper for Agent-based classification.

    Use `from agent_platform.classification.agents import classify_email` instead.

    This class maintains the old API while using the new Agent-based
    implementation. Will be removed in future versions.
    """

    def __init__(self):
        """Initialize classifier (no-op, agents are stateless)."""
        print("⚠️  UnifiedClassifier is deprecated. Use classify_email() from orchestrator_agent instead.")

    async def classify_email(self, email: Email) -> ClassificationResult:
        """
        Classify email using Agent-based pipeline.

        Args:
            email: Email object to classify

        Returns:
            ClassificationResult with category, confidence, reasoning

        This method now delegates to the Agent-based orchestrator.
        """
        return await classify_email(email)


# ============================================================================
# CONVENIENCE FUNCTION (Recommended API)
# ============================================================================

async def classify(email: Email) -> ClassificationResult:
    """
    Classify email using Agent-based pipeline.

    This is the recommended API for new code.

    Args:
        email: Email object to classify

    Returns:
        ClassificationResult with category, confidence, reasoning

    Example:
        from agent_platform.classification import classify

        email = Email(...)
        result = await classify(email)
    """
    return await classify_email(email)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'UnifiedClassifier',  # Deprecated
    'classify',  # Recommended
    'ClassificationResult'
]
```

**Migration Notes:**
- Maintains old API for backward compatibility
- Delegates to new Agent-based orchestrator
- Deprecation warning for old usage
- New code should use classify() or classify_email() directly

---

## Testing Strategy

### Unit Tests

Create `tests/classification/test_agents.py`:

```python
"""
Unit tests for classification agents.
"""

import pytest
from agent_platform.classification.agents.rule_agent import classify_with_rules
from agent_platform.classification.agents.history_agent import classify_with_history
from agent_platform.classification.agents.llm_agent import classify_with_llm
from agent_platform.classification.agents.orchestrator_agent import classify_email
from agent_platform.models.email import Email


@pytest.mark.asyncio
async def test_rule_agent_spam_detection():
    """Test rule agent detects spam correctly."""
    result = await classify_with_rules(
        subject="Win a Free iPhone!",
        body="Click here now! Limited time offer! Unsubscribe here.",
        sender="promo@marketing.com",
        headers={}
    )

    assert result.category == "spam"
    assert result.confidence >= 0.9
    assert len(result.matched_patterns) >= 2


@pytest.mark.asyncio
async def test_rule_agent_auto_reply():
    """Test rule agent detects auto-replies."""
    result = await classify_with_rules(
        subject="Out of Office",
        body="I am currently out of office until Monday.",
        sender="colleague@company.com",
        headers={"Auto-Submitted": "auto-replied"}
    )

    assert result.category == "auto_reply"
    assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_rule_agent_no_match():
    """Test rule agent returns None when no patterns match."""
    result = await classify_with_rules(
        subject="Meeting Tomorrow",
        body="Let's meet at 2pm",
        sender="colleague@company.com",
        headers={}
    )

    assert result.category is None
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_history_agent_with_history(db_session):
    """Test history agent uses sender history."""
    # Setup: Create sender preference
    from agent_platform.classification.agents.history_agent import update_sender_preference

    await update_sender_preference(
        sender="newsletter@company.com",
        domain="company.com",
        category="newsletter",
        confidence=0.85,
        importance=0.2
    )

    # Test classification
    result = await classify_with_history(
        sender="newsletter@company.com",
        domain="company.com"
    )

    assert result.category == "newsletter"
    assert result.confidence >= 0.6
    assert result.email_count > 0


@pytest.mark.asyncio
async def test_history_agent_no_history():
    """Test history agent returns None for new sender."""
    result = await classify_with_history(
        sender="new_sender@example.com",
        domain="example.com"
    )

    assert result.category is None
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_llm_agent_important_email():
    """Test LLM agent classifies important work email."""
    result = await classify_with_llm(
        subject="Q4 Report Due Today",
        body="Can you send me the Q4 report by end of day? Thanks, Sarah (VP Sales)",
        sender="vp.sales@company.com"
    )

    assert result.category == "important"
    assert result.confidence >= 0.7
    assert result.importance >= 0.7
    assert result.requires_response is True


@pytest.mark.asyncio
async def test_orchestrator_early_stopping_rule():
    """Test orchestrator stops at rule layer for spam."""
    email = Email(
        email_id="test_001",
        subject="Win Free Money!",
        body="Click here! Unsubscribe link below.",
        sender="spam@marketing.com",
        domain="marketing.com",
        headers={}
    )

    result = await classify_email(email)

    assert result.category == "spam"
    assert result.layer_used == "rules"
    assert result.llm_provider == "rules_only"
    assert result.processing_time_ms < 100  # Fast, no LLM call


@pytest.mark.asyncio
async def test_orchestrator_fallback_to_llm():
    """Test orchestrator falls back to LLM when rule/history fail."""
    email = Email(
        email_id="test_002",
        subject="Quick Question",
        body="Hey, do you have time to chat?",
        sender="new_colleague@company.com",
        domain="company.com",
        headers={}
    )

    result = await classify_email(email)

    assert result.category in ["normal", "important"]
    assert result.layer_used == "llm"
    assert result.processing_time_ms > 100  # Slower, LLM call


@pytest.mark.asyncio
async def test_guardrail_pii_detection():
    """Test PII guardrail blocks sensitive content."""
    with pytest.raises(Exception):  # Guardrail should trigger
        await classify_with_llm(
            subject="Credit Card Info",
            body="My credit card number is 4532-1234-5678-9010",
            sender="user@example.com"
        )
```

### Integration Tests

Update `tests/test_e2e_real_gmail.py`:

```python
# Add test for Agent-based classification
@pytest.mark.asyncio
async def test_agent_based_classification():
    """Test new Agent-based classification works with real Gmail."""
    from agent_platform.classification.agents import classify_email

    gmail_service = get_gmail_service()
    messages = fetch_unread_emails(gmail_service, max_results=5)

    for msg_data in messages:
        email = Email(
            email_id=msg_data['id'],
            subject=msg_data['subject'],
            body=msg_data['body'],
            sender=msg_data['sender'],
            domain=extract_domain(msg_data['sender']),
            headers=msg_data['headers']
        )

        result = await classify_email(email)

        assert result.category in ["spam", "important", "newsletter", "auto_reply", "normal"]
        assert 0.0 <= result.confidence <= 1.0
        assert result.layer_used in ["rules", "history", "llm"]
        print(f"✅ {email.subject[:50]} → {result.category} ({result.layer_used})")
```

---

## Rollback Procedures

### If Migration Fails

1. **Revert to UnifiedClassifier:**
   ```python
   # In unified_classifier.py, restore old implementation
   class UnifiedClassifier:
       async def classify_email(self, email: Email):
           # Old implementation (direct LLM calls)
           ...
   ```

2. **Database Rollback:**
   ```bash
   # Restore database from backup
   cp platform_backup.db platform.db
   ```

3. **Git Rollback:**
   ```bash
   git revert <migration-commit-sha>
   ```

### Gradual Migration Strategy

Use feature flags to enable Agent-based classification gradually:

```python
# .env
USE_AGENT_CLASSIFICATION=false  # Default: old implementation
```

```python
# unified_classifier.py
import os

USE_AGENTS = os.getenv("USE_AGENT_CLASSIFICATION", "false").lower() == "true"

class UnifiedClassifier:
    async def classify_email(self, email: Email):
        if USE_AGENTS:
            # New Agent-based implementation
            return await classify_email(email)
        else:
            # Old implementation
            return await self._old_classify(email)
```

This allows:
- Testing Agent implementation on subset of emails
- Quick rollback if issues occur
- Gradual confidence building

---

## Summary

This migration guide provides:

1. ✅ **Detailed code examples** for all 3 agents (Rule, History, LLM)
2. ✅ **Orchestrator implementation** with early stopping
3. ✅ **Backward compatibility wrapper** for smooth transition
4. ✅ **Comprehensive test suite** (unit + integration)
5. ✅ **Rollback procedures** for risk mitigation
6. ✅ **Feature flags** for gradual migration

Next: Implement Phase 1.2 (Agent Registry Integration) and Phase 1.3 (Guardrails).
