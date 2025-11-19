# Next Steps: OpenAI Agents SDK Integration

**Status:** Planning Phase
**Last Updated:** 2025-11-19
**Goal:** Integrate `agent_platform/` classification system with OpenAI Agents SDK and merge `modules/email/` into unified architecture

---

## Executive Summary

Currently we have **two parallel systems** that need to be integrated:

1. **`agent_platform/`** - Email classification system (3-layer: Rule → History → LLM)
   - ❌ Does NOT use OpenAI Agents SDK
   - ❌ Direct LLM API calls
   - ❌ Custom orchestration
   - ✅ Advanced classification logic
   - ✅ Adaptive learning (EMA)
   - ✅ Review/digest system

2. **`modules/email/`** - Agent-based email automation
   - ✅ DOES use OpenAI Agents SDK
   - ✅ `Agent` class, `Runner.run()`
   - ✅ Guardrails with decorators
   - ✅ Agent registry pattern
   - ✅ Draft generation, orchestration

**Original Vision:** OpenAI Agents SDK everywhere with Agent Registry pattern

**Integration Strategy:** Extract proven classification logic, wrap with Agent SDK patterns, merge `modules/email/` capabilities

---

## 🎯 PRESERVATION PRINCIPLE

**CRITICAL: This is NOT a rewrite - it's interface wrapping!**

All classification logic (pattern matching, EMA learning, early stopping) remains **100% identical**. We're only changing HOW we call the code, not WHAT the code does.

**What stays unchanged:**
- ✅ Rule layer pattern matching (spam keywords, newsletter detection, auto-reply patterns)
- ✅ History layer EMA learning (α=0.15 formula)
- ✅ Early stopping thresholds (0.85 confidence)
- ✅ Confidence scores (0.95 for spam, 0.90 for newsletter, etc.)
- ✅ Database queries and SenderPreference updates
- ✅ Review queue routing logic

**What changes:**
- 🔄 Interface: Agent with tools instead of class methods
- 🔄 Orchestration: Runner.run() instead of direct calls
- 🔄 Discovery: Agent Registry for discoverability

**Think of it as:** Putting the same proven engine in a better, more modular chassis.

---

## Phase 1: Architectural Integration (Priority 1)

### 1.1 Extract Classification Logic & Wrap with Agents SDK

**Current State:**
```python
# agent_platform/classification/unified_classifier.py
class UnifiedClassifier:
    async def classify_email(self, email: Email) -> ClassificationResult:
        # Direct LLM calls, no Agent pattern
        response, provider = await llm_provider.complete(messages, ...)
```

**Target State:**
```python
# agent_platform/classification/agents/rule_agent.py
from agents import Agent

rule_agent = Agent(
    name="rule_classifier",
    instructions="Apply rule-based email classification...",
    output_type=RuleClassification,
)

# agent_platform/classification/agents/history_agent.py
history_agent = Agent(
    name="history_classifier",
    instructions="Use sender/domain history for classification...",
    output_type=HistoryClassification,
)

# agent_platform/classification/agents/llm_agent.py
llm_agent = Agent(
    name="llm_classifier",
    instructions="Deep semantic analysis for difficult emails...",
    output_type=LLMClassification,
)

# agent_platform/classification/orchestrator.py
from agents import Runner

class ClassificationOrchestrator:
    async def classify(self, email: Email) -> ClassificationResult:
        # Try rule layer
        rule_result = await Runner.run(rule_agent, email.content)
        if rule_result.confidence >= 0.85:
            return rule_result  # Early stopping

        # Try history layer
        history_result = await Runner.run(history_agent, email)
        if history_result.confidence >= 0.85:
            return history_result  # Early stopping

        # Fall back to LLM layer
        llm_result = await Runner.run(llm_agent, email.content)
        return llm_result
```

**Migration Approach (Extract + Wrap):**

1. **EXTRACT** existing functions from rule_layer.py, history_layer.py, llm_layer.py
   - Copy pattern matching code AS-IS (no changes!)
   - Make functions standalone (no class dependencies)

2. **WRAP** extracted functions as Agent tools
   - Register functions with ToolFunction.from_function()
   - Create Agent with instructions that call our tools

3. **ORCHESTRATE** with Agent Runner
   - Replace direct function calls with Runner.run()
   - Maintain early stopping logic (0.85 threshold)

**Files to Create:**
- `agent_platform/classification/agents/rule_agent.py` (extracted pattern matching + Agent wrapper)
- `agent_platform/classification/agents/history_agent.py` (extracted EMA learning + Agent wrapper)
- `agent_platform/classification/agents/llm_agent.py` (extracted prompts + Agent wrapper with guardrails)
- `agent_platform/classification/agents/orchestrator_agent.py` (orchestration logic with Runner.run())

**Files to Modify:**
- `agent_platform/classification/unified_classifier.py` → Thin backward-compat wrapper
- `agent_platform/classification/rule_layer.py` → Archive (logic moved to agents/rule_agent.py)
- `agent_platform/classification/history_layer.py` → Archive (logic moved to agents/history_agent.py)
- `agent_platform/classification/llm_layer.py` → Archive (logic moved to agents/llm_agent.py)

### 1.2 Integrate Agent Registry Pattern

**Register Classification Agents:**
```python
# agent_platform/module.py (NEW FILE)
from agent_platform.core.registry import get_registry
from agent_platform.classification.agents import (
    rule_agent,
    history_agent,
    llm_agent,
    orchestrator_agent
)

def register_classification_module():
    registry = get_registry()

    # Register module
    registry.register_module(
        name="classification",
        version="1.0.0",
        description="Email classification with 3-layer architecture"
    )

    # Register agents with capabilities
    registry.register_agent(
        module_name="classification",
        agent_name="rule_classifier",
        agent_instance=rule_agent,
        agent_type="classifier",
        capabilities=["email_classification", "spam_detection", "newsletter_detection"]
    )

    registry.register_agent(
        module_name="classification",
        agent_name="history_classifier",
        agent_instance=history_agent,
        agent_type="classifier",
        capabilities=["email_classification", "sender_preference_learning"]
    )

    registry.register_agent(
        module_name="classification",
        agent_name="llm_classifier",
        agent_instance=llm_agent,
        agent_type="classifier",
        capabilities=["email_classification", "semantic_analysis"]
    )

    registry.register_agent(
        module_name="classification",
        agent_name="orchestrator",
        agent_instance=orchestrator_agent,
        agent_type="orchestrator",
        capabilities=["email_classification", "early_stopping", "adaptive_routing"]
    )
```

**Files to Create:**
- `agent_platform/module.py` (classification module registration)
- `agent_platform/core/registry.py` (if not exists, copy from modules/email pattern)

### 1.3 Add Guardrails to Classification

**Integrate Guardrails from modules/email:**
```python
# agent_platform/classification/guardrails/classification_guardrails.py
from agents import input_guardrail, output_guardrail, GuardrailFunctionOutput

@input_guardrail
async def check_email_pii(ctx, agent, email_content: str):
    """Block classification if email contains sensitive PII."""
    # Reuse PII detection from modules/email/guardrails/
    from modules.email.guardrails.pii_guardrail import pii_detector_agent

    result = await Runner.run(pii_detector_agent, email_content)

    return GuardrailFunctionOutput(
        output_info={'pii_detected': result.contains_pii},
        tripwire_triggered=result.contains_pii  # Stop if PII found
    )

@input_guardrail
async def check_phishing(ctx, agent, email_content: str):
    """Block classification if email is potential phishing."""
    from modules.email.guardrails.phishing_guardrail import phishing_detector_agent

    result = await Runner.run(phishing_detector_agent, email_content)

    return GuardrailFunctionOutput(
        output_info={'phishing_detected': result.is_phishing},
        tripwire_triggered=result.is_phishing
    )

# Apply to agents
llm_agent = Agent(
    name="llm_classifier",
    instructions="...",
    output_type=LLMClassification,
    input_guardrails=[check_email_pii, check_phishing]
)
```

**Files to Create:**
- `agent_platform/classification/guardrails/classification_guardrails.py`

**Dependencies:**
- Reuse `modules/email/guardrails/pii_guardrail.py`
- Reuse `modules/email/guardrails/phishing_guardrail.py`

### 1.4 Merge modules/email into agent_platform

**Directory Reorganization:**

```
Before:
├── agent_platform/           # Classification only
│   ├── classification/
│   ├── review/
│   └── ...
└── modules/
    └── email/                # Draft generation, orchestration
        ├── agents/
        ├── guardrails/
        └── tools/

After:
└── agent_platform/
    ├── classification/       # Classification agents (refactored to SDK)
    │   ├── agents/
    │   │   ├── rule_agent.py
    │   │   ├── history_agent.py
    │   │   ├── llm_agent.py
    │   │   └── orchestrator_agent.py
    │   ├── guardrails/
    │   └── module.py         # Classification module registration
    ├── drafts/               # MERGED from modules/email/agents/responder.py
    │   ├── agents/
    │   │   ├── tone_agents.py  # Professional, casual, empathetic
    │   │   └── orchestrator_agent.py
    │   └── module.py
    ├── guardrails/           # MERGED from modules/email/guardrails/
    │   ├── pii_guardrail.py
    │   ├── phishing_guardrail.py
    │   └── compliance_guardrail.py
    ├── tools/                # MERGED from modules/email/tools/
    │   ├── gmail_tools.py
    │   └── ionos_tools.py
    └── core/
        └── registry.py       # Agent registry (existing pattern)
```

**Migration Steps:**
1. Copy `modules/email/guardrails/` → `agent_platform/guardrails/`
2. Copy `modules/email/tools/` → `agent_platform/tools/`
3. Refactor `modules/email/agents/responder.py` → `agent_platform/drafts/agents/`
4. Merge `modules/email/agents/orchestrator.py` logic into classification orchestrator
5. Update all imports across codebase
6. Archive `modules/` directory

**Files to Create:**
- `agent_platform/drafts/agents/tone_agents.py`
- `agent_platform/drafts/agents/orchestrator_agent.py`
- `agent_platform/drafts/module.py`

**Files to Move:**
- `modules/email/guardrails/*.py` → `agent_platform/guardrails/`
- `modules/email/tools/*.py` → `agent_platform/tools/`

---

## Phase 2: Feature Integration (Priority 2)

### 2.1 Integrate Draft Generation into Classification Workflow

**Current Separation:**
- Classification: `agent_platform/classification/`
- Draft generation: `modules/email/agents/responder.py`

**Target Integration:**
```python
# agent_platform/orchestration/email_orchestrator.py
from agents import Agent, Runner

class EmailOrchestrator:
    """
    Master orchestrator for complete email workflow:
    1. Classify email (rule → history → llm)
    2. Generate draft if needed (based on mode)
    3. Apply review routing (based on confidence)
    """

    async def process_email(self, email: Email, mode: Mode) -> ProcessingResult:
        # Step 1: Classify
        classification = await Runner.run(
            orchestrator_agent,  # Classification orchestrator
            email.content
        )

        # Step 2: Route based on mode and confidence
        if mode == Mode.MANUAL:
            return ProcessingResult(
                classification=classification,
                action="label_only"
            )

        elif mode == Mode.DRAFT or (mode == Mode.AUTO_REPLY and classification.confidence < 0.85):
            # Generate draft
            draft = await Runner.run(
                draft_orchestrator_agent,  # Draft generation orchestrator
                email_content=email.content,
                classification=classification
            )

            return ProcessingResult(
                classification=classification,
                draft=draft,
                action="save_draft"
            )

        elif mode == Mode.AUTO_REPLY and classification.confidence >= 0.85:
            # Auto-send
            draft = await Runner.run(draft_orchestrator_agent, ...)

            return ProcessingResult(
                classification=classification,
                draft=draft,
                action="send_email"
            )
```

**Files to Create:**
- `agent_platform/orchestration/email_orchestrator.py`
- `agent_platform/orchestration/module.py`

### 2.2 Integrate Review & Digest System

**Current State:**
- Review queue: `agent_platform/review/queue_manager.py`
- Digest generation: `agent_platform/review/digest.py`

**Target Integration with Agents:**
```python
# agent_platform/review/agents/digest_agent.py
from agents import Agent

digest_agent = Agent(
    name="digest_generator",
    instructions="""
    Generate a daily email digest for review queue items.

    For each item, create:
    - Subject line preview
    - Classification summary (category, confidence, importance)
    - Recommended action
    - HTML action buttons (Approve, Reject, Edit)

    Group by confidence level: High, Medium, Low
    """,
    output_type=DigestEmail
)

# Usage
async def generate_daily_digest():
    queue_items = get_review_queue_items()

    digest = await Runner.run(
        digest_agent,
        queue_items=queue_items
    )

    send_digest_email(digest)
```

**Files to Create:**
- `agent_platform/review/agents/digest_agent.py`
- `agent_platform/review/module.py`

---

## Phase 3: Gmail Label Integration (Priority 3)

From `user-feedback/user-stories/user-story_label_sync.md`:

### 3.1 Centralized Label Mapping Agent

**Create Label Mapping Agent:**
```python
# agent_platform/labels/agents/label_mapper_agent.py
from agents import Agent

label_mapper_agent = Agent(
    name="label_mapper",
    instructions="""
    Map email classification categories to Gmail labels.

    Mapping rules:
    - SPAM → Gmail: Spam
    - IMPORTANT → Gmail: Important
    - NEWSLETTER → Gmail: Newsletters
    - AUTO_REPLY → Gmail: Auto-Reply
    - NORMAL → No special label

    Return label actions to apply.
    """,
    output_type=LabelActions
)
```

**Files to Create:**
- `agent_platform/labels/agents/label_mapper_agent.py`
- `agent_platform/labels/mapping.py` (mapping configuration)
- `agent_platform/labels/module.py`

### 3.2 Ionos Folder Mapping

**Extend Label Mapper for Ionos:**
```python
# agent_platform/labels/agents/ionos_folder_mapper_agent.py
ionos_folder_mapper_agent = Agent(
    name="ionos_folder_mapper",
    instructions="""
    Map email classification categories to Ionos IMAP folders.

    Mapping rules:
    - SPAM → IMAP Folder: Spam
    - IMPORTANT → IMAP Folder: Important
    - NEWSLETTER → IMAP Folder: Newsletters
    - NORMAL → IMAP Folder: INBOX (no move)

    Return IMAP MOVE commands.
    """,
    output_type=IonosFolderActions
)
```

**Files to Create:**
- `agent_platform/labels/agents/ionos_folder_mapper_agent.py`

---

## Phase 4: RAG Vector Database (Priority 4)

From `user-feedback/user-stories/user-story_email_rag_memory.md`:

### 4.1 ChromaDB Setup

**Create Vector Store:**
```python
# agent_platform/rag/vector_store.py
import chromadb

class EmailVectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="email_history",
            metadata={"description": "Email content and metadata for RAG"}
        )

    async def add_email(self, email: Email, classification: ClassificationResult):
        """Add email to vector store after classification."""
        self.collection.add(
            documents=[email.content],
            metadatas=[{
                "email_id": email.email_id,
                "sender": email.sender,
                "subject": email.subject,
                "category": classification.category,
                "importance": classification.importance,
                "timestamp": email.date.isoformat()
            }],
            ids=[email.email_id]
        )

    async def search_similar_emails(self, query: str, n_results: int = 5):
        """Find similar emails for RAG context."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
```

**Files to Create:**
- `agent_platform/rag/vector_store.py`
- `agent_platform/rag/chunking.py` (smart chunking strategy)
- `agent_platform/rag/module.py`

### 4.2 RAG-Enhanced Classification Agent

**Integrate RAG into LLM Layer:**
```python
# agent_platform/classification/agents/llm_agent.py (UPDATED)
from agent_platform.rag.vector_store import EmailVectorStore

async def rag_enhanced_classification(email: Email):
    vector_store = EmailVectorStore()

    # Retrieve similar emails
    similar_emails = await vector_store.search_similar_emails(
        query=email.content,
        n_results=5
    )

    # Build context for LLM
    context = f"""
    Similar emails from history:
    {format_similar_emails(similar_emails)}

    Email to classify:
    {email.content}
    """

    # Run LLM agent with RAG context
    result = await Runner.run(llm_agent, context)

    return result
```

---

## Phase 5: Directory Cleanup (Priority 5)

See `DIRECTORY_CLEANUP.md` for detailed reorganization plan.

**High-Level Changes:**
1. Create `docs/` directory for all markdown files
2. Merge `modules/email/` into `agent_platform/`
3. Consolidate database initialization scripts
4. Organize scripts by purpose (setup, testing, operations)

---

## Implementation Timeline

### Week 1-2: Phase 1 (Architectural Integration)
- **Days 1-3:** Refactor classification layers to Agent pattern
- **Days 4-5:** Implement agent registry integration
- **Days 6-7:** Add guardrails and test integration
- **Days 8-10:** Merge modules/email into agent_platform
- **Deliverable:** Classification system using OpenAI Agents SDK

### Week 3: Phase 2 (Feature Integration)
- **Days 11-12:** Integrate draft generation workflow
- **Days 13-14:** Integrate review & digest system
- **Day 15:** End-to-end testing
- **Deliverable:** Unified email orchestration with all features

### Week 4: Phase 3 (Label Integration)
- **Days 16-17:** Gmail label mapping
- **Days 18-19:** Ionos folder mapping
- **Day 20:** Database consistency checks
- **Deliverable:** Complete label sync system

### Week 5: Phase 4 (RAG Integration)
- **Days 21-22:** ChromaDB setup and chunking
- **Days 23-24:** RAG-enhanced classification
- **Day 25:** Performance testing
- **Deliverable:** RAG-powered classification

### Week 6: Phase 5 (Cleanup & Documentation)
- **Days 26-27:** Directory reorganization
- **Days 28-29:** Documentation updates
- **Day 30:** Final E2E testing
- **Deliverable:** Production-ready system

---

## Success Criteria

### Phase 1: Architectural Integration
- [ ] All classification layers use `Agent` pattern
- [ ] All agents registered with `AgentRegistry`
- [ ] All agents have guardrails
- [ ] `modules/email/` merged into `agent_platform/`
- [ ] E2E tests pass with SDK-based agents

### Phase 2: Feature Integration
- [ ] Draft generation integrated into classification workflow
- [ ] Review queue uses agents for digest generation
- [ ] All modes (Draft, Auto-Reply, Manual) work correctly
- [ ] Confidence-based routing works

### Phase 3: Label Integration
- [ ] Gmail labels sync correctly
- [ ] Ionos folders sync correctly
- [ ] Database consistency maintained
- [ ] Label changes reflected in feedback loop

### Phase 4: RAG Integration
- [ ] ChromaDB operational
- [ ] Email embeddings stored correctly
- [ ] RAG context improves classification accuracy
- [ ] Performance acceptable (<2s per email)

### Phase 5: Cleanup
- [ ] Directory structure clean and logical
- [ ] All documentation updated
- [ ] No redundant files
- [ ] Clear separation of concerns

---

## Migration Risks & Mitigation

### Risk 1: Breaking Existing Classification Logic
**Mitigation:**
- Keep `agent_platform/classification/unified_classifier.py` as compatibility wrapper
- Run parallel testing (old vs new implementation)
- Gradual migration with feature flags

### Risk 2: Performance Degradation
**Mitigation:**
- Benchmark current vs SDK-based performance
- Maintain early stopping optimization
- Use async/await for parallel processing

### Risk 3: Data Loss During Migration
**Mitigation:**
- Database backup before migration
- Test migrations on copy of production DB
- Rollback plan for each phase

### Risk 4: Integration Conflicts
**Mitigation:**
- Use feature branches for each phase
- Comprehensive integration tests
- Code review for each merge

---

## Next Steps (Immediate Actions)

1. **Review this plan** - Confirm approach and priorities
2. **Create ARCHITECTURE_MIGRATION.md** - Detailed technical migration guide
3. **Create DIRECTORY_CLEANUP.md** - File reorganization plan
4. **Create ROADMAP.md** - Visual timeline and milestones
5. **Start Phase 1.1** - Refactor rule layer to Agent pattern (proof of concept)

---

## Questions for Discussion

1. **Phase Priorities:** Do you agree with the phase ordering? Should we swap any priorities?
2. **Timeline:** Is 6 weeks realistic? Should we compress or extend?
3. **Testing Strategy:** Should we build unit tests alongside migration or after?
4. **Backward Compatibility:** Do we need to maintain old API during migration?
5. **RAG Priority:** Is RAG (Phase 4) too early? Should it come after production deployment?

---

## References

- Original vision: `CLAUDE.md`
- Classification system: `agent_platform/classification/`
- Agent patterns: `modules/email/agents/`
- User feedback: `user-feedback/user-stories/`
- Test results: Phase 1-6 completion documents
