# Development Roadmap: Email Agent Platform

**Last Updated:** 2025-11-19
**Status:** Planning Phase → Execution Starting

---

## Vision

Transform email management from manual burden to AI-powered assistant using OpenAI Agents SDK patterns with:
- 🤖 Intelligent classification (3-layer pipeline)
- 📧 Context-aware draft generation
- 🔄 Continuous learning from user feedback
- 🛡️ Security-first guardrails
- 🎯 Multi-account orchestration

---

## Current Status (Phase 0-6: ✅ Complete)

### What's Done

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| **Phase 1** | ✅ Complete | Agent setup, OAuth, basic structure |
| **Phase 2** | ✅ Complete | 3-layer classification (Rule → History → LLM) |
| **Phase 3** | ✅ Complete | Draft generation, orchestration |
| **Phase 4** | ✅ Complete | Review queue, digest system |
| **Phase 5** | ✅ Complete | APScheduler, automated workflows |
| **Phase 6** | ✅ Complete | E2E testing infrastructure, monitoring |

### What Works Now

- ✅ Email classification with 80-85% accuracy
- ✅ Early stopping optimization (80% emails skip LLM)
- ✅ Adaptive learning with EMA (α=0.15)
- ✅ Review queue with confidence-based routing
- ✅ Daily digest email generation
- ✅ Multi-account support (Gmail + Ionos)
- ✅ OAuth2 authentication
- ✅ Database persistence (SQLite)
- ✅ Monitoring & metrics collection

### What Needs Work

- ❌ **OpenAI Agents SDK integration** - Classification uses direct LLM calls (not SDK patterns)
- ❌ **Architecture alignment** - Two separate systems (`agent_platform/` + `modules/email/`)
- ❌ **Directory organization** - 18 markdown files in root, scattered structure
- ❌ **Guardrails** - No PII/phishing protection on classification
- ❌ **Agent Registry** - No centralized agent discovery
- ❌ **Label Sync** - No Gmail label / Ionos folder integration
- ❌ **RAG Memory** - No vector database for context

---

## Roadmap Overview (6 Weeks)

```
Week 1-2: Phase 7 - OpenAI Agents SDK Integration
Week 3:   Phase 8 - Feature Integration & Testing
Week 4:   Phase 9 - Gmail Label Sync
Week 5:   Phase 10 - RAG Vector Database
Week 6:   Phase 11 - Production Deployment
```

---

## Phase 7: OpenAI Agents SDK Integration (Weeks 1-2)

**Goal:** Refactor classification system to use OpenAI Agents SDK patterns

### Week 1: Agent Implementation

#### Day 1-2: Extract Logic & Create Agent Wrappers
**Tasks (PRESERVATION PRINCIPLE: Extract existing code, don't rewrite!):**
- [ ] Create `agent_platform/classification/agents/rule_agent.py`
  - **EXTRACT** pattern matching from `rule_layer.py` AS-IS (no logic changes!)
  - **WRAP** extracted functions as Agent tools
  - Add structured output with `RuleClassification` Pydantic model
  - No guardrails needed (deterministic)
- [ ] Create `agent_platform/classification/agents/history_agent.py`
  - **EXTRACT** EMA learning from `history_layer.py` AS-IS (α=0.15 preserved!)
  - **WRAP** database queries as Agent tool
  - Add `get_sender_history()` tool function
  - Preserve EMA learning formula (no changes!)
- [ ] Create `agent_platform/classification/agents/llm_agent.py`
  - **EXTRACT** classification prompts from `llm_layer.py` AS-IS
  - **WRAP** with Agent interface
  - Add input guardrails: PII detection, phishing detection
  - Add output guardrail: classification validation

**Deliverables:**
- 3 agent files with **extracted + wrapped** logic (not new logic!)
- Pydantic models for structured outputs
- Guardrails for LLM agent

**CRITICAL:** Classification results must be IDENTICAL to current implementation!

**Validation:**
```bash
# Test each agent independently
python -c "from agent_platform.classification.agents.rule_agent import classify_with_rules; import asyncio; asyncio.run(classify_with_rules('Win Free iPhone!', 'Click here', 'spam@example.com', {}))"
```

#### Day 3-4: Create Classification Orchestrator
**Tasks (PRESERVATION: Same early stopping logic!):**
- [ ] Create `agent_platform/classification/agents/orchestrator_agent.py`
  - **PRESERVE** 3-layer pipeline (rule → history → llm)
  - **PRESERVE** early stopping threshold (0.85 confidence - unchanged!)
  - **PRESERVE** EMA learning updates (α=0.15 - unchanged!)
  - Replace direct calls with Runner.run() (interface change only!)
  - Add monitoring integration
- [ ] Update `unified_classifier.py` as backward compatibility wrapper
  - Deprecation warning
  - Delegate to new orchestrator
  - Maintain old API (no breaking changes!)

**Deliverables:**
- Classification orchestrator with **same early stopping logic**
- Backward-compatible wrapper
- Monitoring integration

**CRITICAL:** Early stopping must work identically (80% emails skip LLM, same as before!)

**Validation:**
```bash
# Test orchestrator
python tests/classification/test_orchestrator.py
```

#### Day 5-7: Agent Registry Integration
**Tasks:**
- [ ] Create `agent_platform/module.py` (classification module registration)
  - Register classification module
  - Register 4 agents (rule, history, llm, orchestrator)
  - Define capabilities for each agent
- [ ] Create `agent_platform/core/registry.py` (if not exists)
  - Implement `AgentRegistry` class
  - `register_module()`, `register_agent()`, `discover_agents()`, `get_agent()` methods
- [ ] Update initialization scripts to register classification module
  - Add registration call to setup scripts

**Deliverables:**
- Agent registry implementation
- Classification module registered
- Agent discovery working

**Validation:**
```bash
# Test agent discovery
python -c "from agent_platform.core.registry import get_registry; registry = get_registry(); print(registry.discover_agents('email_classification'))"
```

### Week 2: Merge & Testing

#### Day 8-10: Merge modules/email into agent_platform
**Tasks:**
- [ ] Copy `modules/email/guardrails/` → `agent_platform/guardrails/`
  - Update imports in copied files
  - Ensure guardrails work with classification agents
- [ ] Copy `modules/email/tools/` → `agent_platform/tools/`
  - Update imports
  - Test Gmail/Ionos tools
- [ ] Refactor `modules/email/agents/responder.py` → `agent_platform/drafts/agents/`
  - Extract tone agents (professional, casual, empathetic)
  - Create draft orchestrator agent
  - Register drafts module
- [ ] Archive `modules/` directory
  - Move to `archive/modules_old/`
  - Update gitignore

**Deliverables:**
- Guardrails merged and working
- Email tools merged
- Draft agents refactored to SDK pattern
- Old modules archived

**Validation:**
```bash
# Test merged tools
python -c "from agent_platform.tools.gmail_tools import fetch_unread_emails; print('Tools working')"
```

#### Day 11-14: Testing & Bug Fixes
**Tasks:**
- [ ] Write unit tests for all agents
  - `tests/classification/test_rule_agent.py`
  - `tests/classification/test_history_agent.py`
  - `tests/classification/test_llm_agent.py`
  - `tests/classification/test_orchestrator.py`
- [ ] Run E2E tests with real Gmail
  - Update `tests/integration/test_e2e_real_gmail.py`
  - Test with 10-20 real emails
  - **COMPARE:** Old vs new classification results (must be identical!)
- [ ] Fix bugs discovered in testing
- [ ] Performance benchmarking
  - **VERIFY:** Processing time ≤ current implementation (no regression!)
  - **VERIFY:** Early stopping works (80% emails skip LLM, same as before!)
  - **VERIFY:** LLM usage percentage ≤ 20% (same as before!)

**Deliverables:**
- Complete unit test suite (>80% coverage)
- Passing E2E tests
- Bug fixes
- Performance benchmarks

**Validation:**
```bash
# Run all tests
pytest tests/ -v
# Expected: All tests pass
```

**Success Criteria:**
- [ ] All classification agents use OpenAI SDK patterns
- [ ] **Classification results IDENTICAL to current implementation** (100% match on test set)
- [ ] **Early stopping preserved** (80% emails skip LLM, same threshold 0.85)
- [ ] **EMA learning preserved** (α=0.15 formula unchanged)
- [ ] Agent registry operational
- [ ] E2E tests pass with SDK-based agents
- [ ] **No logic regression** (pattern matching, confidence scores identical)
- [ ] **No performance regression** (<10% slower than before)
- [ ] All imports updated (no `modules.email.*`)

---

## Phase 8: Feature Integration & Unified Orchestration (Week 3)

**Goal:** Integrate draft generation, review routing into unified email orchestrator

### Day 15-17: Email Orchestrator Implementation
**Tasks:**
- [ ] Create `agent_platform/orchestration/email_orchestrator.py`
  - Master orchestrator: classify → draft → send/review
  - Mode-based routing (Manual, Draft, Auto-Reply)
  - Confidence-based decision making
  - Integration with review queue
- [ ] Register orchestration module with registry
- [ ] Create operational script: `scripts/operations/run_orchestrator.py`
  - Process inbox with full workflow
  - Multi-account support
  - Metrics reporting

**Deliverables:**
- Email orchestrator agent
- Unified workflow (classification → draft → action)
- Operational script

**Validation:**
```bash
# Test orchestrator on 5 emails
python scripts/operations/run_orchestrator.py --account gmail_2 --max-emails 5
```

### Day 18-19: Review System Integration
**Tasks:**
- [ ] Create `agent_platform/review/agents/digest_agent.py`
  - Convert digest generation to Agent pattern
  - HTML email generation with action buttons
  - Grouping by confidence level
- [ ] Update review queue to work with new orchestrator
- [ ] Test daily digest generation

**Deliverables:**
- Digest agent implementation
- Review queue integrated with orchestrator
- Daily digest working

**Validation:**
```bash
# Generate test digest
python -c "from agent_platform.review.agents.digest_agent import generate_digest; import asyncio; asyncio.run(generate_digest())"
```

### Day 20-21: Integration Testing & Polish
**Tasks:**
- [ ] E2E test with complete workflow
  - Classification → Draft → Review → Digest
  - Test all 3 modes
  - Test multi-account processing
- [ ] Update monitoring to track orchestrator metrics
- [ ] Performance optimization
- [ ] Bug fixes

**Deliverables:**
- Passing E2E tests for complete workflow
- Monitoring integrated
- Performance optimized

**Success Criteria:**
- [ ] Draft generation integrated into classification workflow
- [ ] Review routing works based on confidence
- [ ] All modes (Manual, Draft, Auto-Reply) functional
- [ ] Daily digest emails generated correctly
- [ ] Processing time <5s per email (average)

---

## Phase 9: Gmail Label & Ionos Folder Sync (Week 4)

**Goal:** Automatic label/folder synchronization based on classification

### Day 22-23: Label Mapping Implementation
**Tasks:**
- [ ] Create `agent_platform/labels/mapping.py`
  - Centralized label mapping configuration
  - Category → Gmail label mapping
  - Category → Ionos folder mapping
- [ ] Create `agent_platform/labels/agents/label_mapper_agent.py`
  - Agent to determine label actions
  - Gmail API label operations
- [ ] Create `agent_platform/labels/agents/ionos_folder_mapper_agent.py`
  - Agent to determine folder moves
  - IMAP folder operations

**Deliverables:**
- Label mapping configuration
- Gmail label mapper agent
- Ionos folder mapper agent

**Validation:**
```bash
# Test label mapping
python -c "from agent_platform.labels.mapping import get_label_for_category; print(get_label_for_category('spam'))"
```

### Day 24-25: Database Consistency & Testing
**Tasks:**
- [ ] Add label sync tracking to database
  - `label_sync_log` table for audit trail
  - Track label changes per email
- [ ] Implement label change detection
  - Periodic Gmail label polling
  - Feedback integration (label changes → preference updates)
- [ ] Test label sync with real Gmail
  - Apply labels to 10 test emails
  - Verify labels appear correctly

**Deliverables:**
- Database schema for label tracking
- Label change detection working
- Tested with real Gmail account

**Validation:**
```bash
# Test E2E label sync
python scripts/testing/test_label_sync.py
```

### Day 26: Ionos Integration & Polish
**Tasks:**
- [ ] Test Ionos folder moves
  - Move 5 test emails to folders
  - Verify IMAP operations work
- [ ] Update orchestrator to include label sync
  - Add label sync step after classification
- [ ] Documentation update

**Deliverables:**
- Ionos folder sync working
- Orchestrator includes label sync
- Documentation updated

**Success Criteria:**
- [ ] Gmail labels sync automatically based on classification
- [ ] Ionos folders sync automatically
- [ ] Database tracks all label changes
- [ ] Label changes feed back into preference learning
- [ ] No Gmail API rate limit issues

---

## Phase 10: RAG Vector Database (Week 5)

**Goal:** Add email context memory using ChromaDB for improved classification

### Day 27-28: ChromaDB Setup & Integration
**Tasks:**
- [ ] Install ChromaDB: `pip install chromadb`
- [ ] Create `agent_platform/rag/vector_store.py`
  - `EmailVectorStore` class
  - `add_email()`, `search_similar_emails()` methods
  - Persistent storage configuration
- [ ] Create `agent_platform/rag/chunking.py`
  - Smart chunking strategies
  - Email-specific chunking (subject, body, sender separate)
  - Metadata extraction

**Deliverables:**
- ChromaDB vector store implementation
- Email chunking strategy
- Persistent storage configured

**Validation:**
```bash
# Test vector store
python -c "from agent_platform.rag.vector_store import EmailVectorStore; store = EmailVectorStore(); print('Vector store initialized')"
```

### Day 29-30: RAG-Enhanced Classification
**Tasks:**
- [ ] Update `llm_agent.py` to use RAG context
  - Retrieve 5 similar emails before classification
  - Add similar email context to LLM prompt
  - Test accuracy improvement
- [ ] Batch email embedding
  - Script to embed existing mailbox history
  - Process 100-200 emails from analysis
- [ ] Performance optimization
  - Caching frequently accessed embeddings
  - Batch processing for efficiency

**Deliverables:**
- RAG-enhanced LLM agent
- Mailbox history embedded
- Performance optimized

**Validation:**
```bash
# Test RAG classification
python scripts/testing/test_rag_classification.py
```

### Day 31: Testing & Evaluation
**Tasks:**
- [ ] Measure accuracy improvement
  - Compare RAG vs non-RAG classification
  - Use 50 test emails
  - Calculate accuracy delta
- [ ] Measure performance impact
  - Processing time with RAG
  - Memory usage
- [ ] Tune vector search parameters
  - Number of results (n_results)
  - Similarity threshold

**Deliverables:**
- Accuracy benchmarks (RAG vs baseline)
- Performance benchmarks
- Tuned parameters

**Success Criteria:**
- [ ] ChromaDB operational and storing emails
- [ ] RAG context improves classification accuracy by ≥5%
- [ ] Processing time remains <2s per email
- [ ] Vector search works efficiently

---

## Phase 11: Production Deployment & Cleanup (Week 6)

**Goal:** Directory cleanup, documentation, production readiness

### Day 32-33: Directory Reorganization
**Tasks:**
- [ ] Execute `DIRECTORY_CLEANUP.md` plan
  - Create `docs/` hierarchy
  - Move all markdown files to `docs/`
  - Reorganize scripts by category
  - Reorganize tests by module
  - Archive `modules/` and old code
- [ ] Update all imports
  - Run `scripts/maintenance/update_imports.py`
  - Fix any broken imports
- [ ] Create `pyproject.toml`
  - Modern Python packaging
  - Dependency specification
  - Development dependencies

**Deliverables:**
- Clean directory structure
- All imports working
- Modern packaging setup

**Validation:**
```bash
# Validate structure
python scripts/testing/test_all_connections.py
pytest tests/ -v
```

### Day 34-35: Documentation & Diagrams
**Tasks:**
- [ ] Create architecture diagrams
  - Classification pipeline diagram
  - Agent registry diagram
  - Email workflow diagram (Mermaid)
- [ ] Update all documentation
  - README.md (short version)
  - docs/ARCHITECTURE.md
  - docs/api/ (API reference for each module)
- [ ] Create deployment guide
  - Production deployment steps
  - Environment configuration
  - Monitoring setup

**Deliverables:**
- Architecture diagrams
- Complete documentation
- Deployment guide

**Validation:**
- [ ] All links work
- [ ] Diagrams render correctly
- [ ] Documentation covers all features

### Day 36: Production Testing & Launch
**Tasks:**
- [ ] Full E2E test with production config
  - Test with all 4 email accounts
  - Process 50 emails per account
  - Verify all features work
- [ ] Performance benchmarking
  - Measure throughput (emails/minute)
  - Memory usage monitoring
  - Database size tracking
- [ ] Setup production monitoring
  - APScheduler jobs configured
  - Metrics collection enabled
  - Error alerting configured
- [ ] Final polish
  - Fix any remaining bugs
  - Code cleanup
  - Remove debug logging

**Deliverables:**
- Production-ready system
- Performance benchmarks
- Monitoring configured

**Success Criteria:**
- [ ] All tests passing (unit + integration + E2E)
- [ ] Directory structure clean and organized
- [ ] Documentation complete and accurate
- [ ] Production deployment successful
- [ ] System processing emails autonomously
- [ ] Monitoring operational

---

## Future Phases (Post-Week 6)

### Phase 12: Advanced Features (Optional)

- **Smart Reply Suggestions** - Suggest reply snippets
- **Calendar Integration** - Meeting request handling
- **Attachment Analysis** - Document classification
- **Multi-Language Support** - German + English
- **Advanced Analytics** - Email trends, sender insights
- **Mobile App** - iOS/Android client

### Phase 13: Scale & Optimization

- **PostgreSQL Migration** - Replace SQLite for production
- **Redis Caching** - Cache frequently accessed data
- **Celery Task Queue** - Distributed processing
- **Docker Deployment** - Containerization
- **Kubernetes** - Orchestration at scale

---

## Metrics & KPIs

### Success Metrics

| Metric | Baseline (Current) | Target (Week 6) |
|--------|-------------------|-----------------|
| Classification Accuracy | 80-85% | ≥90% (with RAG) |
| Early Stopping Rate | 80% | ≥85% |
| Processing Time (avg) | 500ms | <2s (with RAG) |
| LLM Usage | 20% of emails | ≤15% |
| Test Coverage | ~60% | ≥80% |
| Documentation Coverage | ~40% | 100% |

### Weekly Milestones

| Week | Milestone | Success Criteria |
|------|-----------|------------------|
| 1-2 | SDK Integration | All agents use OpenAI SDK |
| 3 | Unified Orchestration | Complete workflow working |
| 4 | Label Sync | Gmail labels syncing |
| 5 | RAG Memory | Vector search working |
| 6 | Production Launch | System autonomous |

---

## Risk Management

### High Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation with SDK | High | Benchmarking, optimization |
| RAG accuracy doesn't improve | Medium | Tune parameters, alternative strategies |
| Gmail API rate limits | High | Rate limiting, caching, batch processing |
| Import conflicts during merge | Medium | Automated import updater, careful testing |

### Contingency Plans

1. **If SDK migration breaks classification:**
   - Feature flag to revert to old implementation
   - Gradual rollout (A/B testing)

2. **If RAG is too slow:**
   - Make RAG optional (feature flag)
   - Use RAG only for low-confidence emails

3. **If label sync causes issues:**
   - Disable auto-sync, require manual approval
   - Add safety checks (e.g., don't auto-delete)

---

## Team & Resources

### Required Skills

- Python 3.10+ (advanced async/await)
- OpenAI Agents SDK patterns
- SQLAlchemy ORM
- Gmail API / IMAP
- Vector databases (ChromaDB)
- Testing (pytest, integration tests)

### Estimated Effort

- **Total:** 6 weeks (30 working days)
- **Phases 7-8:** 3 weeks (15 days) - Critical path
- **Phases 9-10:** 2 weeks (10 days) - Feature additions
- **Phase 11:** 1 week (5 days) - Polish & deploy

### Dependencies

- OpenAI API access (gpt-4o)
- Gmail API OAuth credentials
- Ionos IMAP/SMTP credentials
- Development environment (Python 3.10+)
- Test Gmail account with sample emails

---

## Communication Plan

### Weekly Progress Reports

**Format:**
```markdown
# Week X Progress Report

## Completed
- [ ] Task 1
- [ ] Task 2

## In Progress
- [ ] Task 3

## Blockers
- Issue 1

## Next Week
- Task 4
- Task 5

## Metrics
- Tests passing: X/Y
- Coverage: X%
- Processing time: Xms
```

### Milestone Reviews

- End of Week 2: SDK Integration Review
- End of Week 3: Feature Integration Review
- End of Week 5: Pre-Production Review
- End of Week 6: Launch Review

---

## Summary Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     6-WEEK ROADMAP                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Week 1-2:  Phase 7 - OpenAI Agents SDK Integration           │
│             ├─ Create 3 classification agents                  │
│             ├─ Orchestrator with early stopping                │
│             ├─ Agent registry integration                      │
│             └─ Merge modules/email                             │
│                                                                 │
│  Week 3:    Phase 8 - Feature Integration                     │
│             ├─ Unified email orchestrator                      │
│             ├─ Review system with agents                       │
│             └─ Complete workflow testing                       │
│                                                                 │
│  Week 4:    Phase 9 - Gmail Label Sync                        │
│             ├─ Label mapping agents                            │
│             ├─ Database consistency                            │
│             └─ Ionos folder sync                               │
│                                                                 │
│  Week 5:    Phase 10 - RAG Vector Database                    │
│             ├─ ChromaDB setup                                  │
│             ├─ RAG-enhanced classification                     │
│             └─ Performance tuning                              │
│                                                                 │
│  Week 6:    Phase 11 - Production Deployment                  │
│             ├─ Directory cleanup                               │
│             ├─ Documentation & diagrams                        │
│             └─ Production launch                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Path:** Phases 7-8 (Weeks 1-3)
**Launch Date:** End of Week 6
**First Autonomous Email:** End of Week 3

---

## Next Steps (Immediate)

1. **Review this roadmap** - Confirm timeline and priorities
2. **Create development branch** - `git checkout -b feature/sdk-integration`
3. **Start Phase 7, Day 1** - Create rule_agent.py
4. **Setup weekly progress tracking** - Create GitHub project board
5. **Schedule milestone reviews** - Calendar invites for end of each phase

---

**Let's build this! 🚀**
