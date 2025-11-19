# Directory Cleanup & Reorganization Plan

**Status:** Planning Phase
**Last Updated:** 2025-11-19
**Goal:** Organize codebase for clarity, maintainability, and alignment with OpenAI Agents SDK patterns

---

## Current State Analysis

### Root Directory (27 files, 18 .md)

```
agent-platform/
├── *.md (18 files) - Mixed documentation scattered in root
├── *.py (9 files) - Scripts and initialization
├── agent_platform/ - Main package (classification system)
├── modules/email/ - Agent-based email automation (SDK patterns)
├── scripts/ - Testing and operational scripts
├── tests/ - Test suite
├── credentials/ - OAuth credentials
├── tokens/ - Cached OAuth tokens
├── user-feedback/ - User stories and todos
├── venv/ - Virtual environment
└── Various config files (.env, .gitignore, requirements.txt)
```

### Problems Identified

1. **Documentation Chaos:**
   - 18 markdown files in root
   - 7 PHASE_X files should be in docs/
   - SETUP_GUIDE.md vs DEPLOYMENT.md redundancy
   - README.md vs PROJECT_SUMMARY.md overlap

2. **Dual Email Systems:**
   - `agent_platform/` - Classification (no SDK)
   - `modules/email/` - Automation (with SDK)
   - Need to merge into unified structure

3. **Script Organization:**
   - All scripts in `scripts/` without categorization
   - Testing scripts mixed with operational scripts
   - Database init scripts duplicated (3 versions)

4. **Naming Inconsistencies:**
   - `platform/` vs `agent_platform/` confusion
   - `tests/` flat structure (no organization by module)

5. **Hidden Complexity:**
   - No clear entry points
   - New developers struggle to understand structure
   - No architecture diagrams

---

## Target Structure

### Proposed Directory Tree

```
agent-platform/
│
├── README.md                          # Main project overview (short, links to docs/)
├── .env                               # Environment configuration
├── .gitignore
├── requirements.txt
├── pyproject.toml                     # NEW: Modern Python packaging
│
├── docs/                              # 📚 ALL DOCUMENTATION HERE
│   ├── README.md                      # Documentation index
│   ├── ARCHITECTURE.md                # High-level architecture
│   ├── SETUP_GUIDE.md                 # Setup instructions (for devs)
│   ├── DEPLOYMENT.md                  # Deployment guide (for ops)
│   ├── NEXT_STEPS.md                  # Future development plan
│   ├── ARCHITECTURE_MIGRATION.md      # SDK migration guide
│   ├── ROADMAP.md                     # Timeline and milestones
│   ├── DIRECTORY_CLEANUP.md           # This file
│   ├── CONNECTION_TESTS.md            # Testing guide
│   ├── PROJECT_SUMMARY.md             # Complete project summary
│   │
│   ├── phases/                        # Phase completion documents
│   │   ├── PHASE_1_AGENTS_SETUP.md
│   │   ├── PHASE_2_CLASSIFICATION.md
│   │   ├── PHASE_3_ORCHESTRATION.md
│   │   ├── PHASE_4_REVIEW.md
│   │   ├── PHASE_5_SCHEDULER.md
│   │   ├── PHASE_6_TESTING.md
│   │   └── PHASE_7_E2E_TESTING.md
│   │
│   ├── api/                           # API documentation
│   │   ├── classification.md          # Classification API
│   │   ├── orchestration.md           # Orchestration API
│   │   └── agents.md                  # Agent registry API
│   │
│   └── diagrams/                      # Architecture diagrams (mermaid/png)
│       ├── classification_pipeline.md
│       ├── agent_registry.md
│       └── email_workflow.md
│
├── agent_platform/                    # 🎯 MAIN PACKAGE
│   ├── __init__.py
│   ├── module.py                      # NEW: Module registration for classification
│   │
│   ├── classification/                # Email classification (REFACTORED TO SDK)
│   │   ├── __init__.py
│   │   ├── unified_classifier.py      # Backward compat wrapper (deprecated)
│   │   │
│   │   ├── agents/                    # NEW: Agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── rule_agent.py          # Rule-based classifier agent
│   │   │   ├── history_agent.py       # History-based classifier agent
│   │   │   ├── llm_agent.py           # LLM-based classifier agent
│   │   │   └── orchestrator_agent.py  # Classification orchestrator
│   │   │
│   │   ├── guardrails/                # NEW: Classification guardrails
│   │   │   ├── __init__.py
│   │   │   ├── pii_guardrail.py       # PII detection
│   │   │   ├── phishing_guardrail.py  # Phishing detection
│   │   │   └── compliance_guardrail.py # Compliance checks
│   │   │
│   │   ├── layers/                    # OLD: Layer implementations (DEPRECATED)
│   │   │   ├── rule_layer.py          # Move logic to agents/rule_agent.py
│   │   │   ├── history_layer.py       # Move logic to agents/history_agent.py
│   │   │   └── llm_layer.py           # Move logic to agents/llm_agent.py
│   │   │
│   │   └── models.py                  # Pydantic models for classification
│   │
│   ├── drafts/                        # 📧 DRAFT GENERATION (MERGED FROM modules/email)
│   │   ├── __init__.py
│   │   ├── module.py                  # Module registration for drafts
│   │   │
│   │   ├── agents/                    # Draft generation agents
│   │   │   ├── __init__.py
│   │   │   ├── tone_agents.py         # Professional, casual, empathetic
│   │   │   └── orchestrator_agent.py  # Draft orchestrator
│   │   │
│   │   └── models.py                  # Pydantic models for drafts
│   │
│   ├── review/                        # Review queue & digest system
│   │   ├── __init__.py
│   │   ├── module.py                  # Module registration
│   │   ├── queue_manager.py           # Review queue management
│   │   ├── digest.py                  # Digest email generation
│   │   │
│   │   ├── agents/                    # NEW: Review agents
│   │   │   ├── __init__.py
│   │   │   └── digest_agent.py        # Digest generation agent
│   │   │
│   │   └── models.py
│   │
│   ├── labels/                        # NEW: Gmail label & Ionos folder sync
│   │   ├── __init__.py
│   │   ├── module.py                  # Module registration
│   │   ├── mapping.py                 # Label mapping configuration
│   │   │
│   │   ├── agents/                    # Label mapping agents
│   │   │   ├── __init__.py
│   │   │   ├── label_mapper_agent.py  # Gmail label mapper
│   │   │   └── ionos_folder_mapper_agent.py  # Ionos folder mapper
│   │   │
│   │   └── models.py
│   │
│   ├── rag/                           # NEW: RAG vector database (Phase 4)
│   │   ├── __init__.py
│   │   ├── module.py                  # Module registration
│   │   ├── vector_store.py            # ChromaDB wrapper
│   │   ├── chunking.py                # Smart chunking strategies
│   │   └── models.py
│   │
│   ├── tools/                         # 🔧 EMAIL TOOLS (MERGED FROM modules/email)
│   │   ├── __init__.py
│   │   ├── gmail_tools.py             # Gmail API operations
│   │   └── ionos_tools.py             # IMAP/SMTP operations
│   │
│   ├── guardrails/                    # 🛡️ SHARED GUARDRAILS (MERGED)
│   │   ├── __init__.py
│   │   ├── pii_guardrail.py           # PII detection
│   │   ├── phishing_guardrail.py      # Phishing detection
│   │   └── compliance_guardrail.py    # Compliance checks
│   │
│   ├── orchestration/                 # NEW: Master email orchestrator
│   │   ├── __init__.py
│   │   ├── module.py                  # Module registration
│   │   ├── email_orchestrator.py      # Master orchestrator (classify → draft → send)
│   │   └── models.py
│   │
│   ├── core/                          # Core platform infrastructure
│   │   ├── __init__.py
│   │   ├── config.py                  # Configuration management
│   │   ├── registry.py                # Agent registry
│   │   └── modes.py                   # Mode enum (DRAFT, AUTO_REPLY, MANUAL)
│   │
│   ├── db/                            # Database layer
│   │   ├── __init__.py
│   │   ├── database.py                # Database connection & session
│   │   ├── models.py                  # SQLAlchemy models
│   │   └── migrations/                # Alembic migrations (future)
│   │
│   ├── llm/                           # LLM provider abstraction
│   │   ├── __init__.py
│   │   └── providers.py               # Unified LLM provider (Ollama + OpenAI)
│   │
│   ├── models/                        # Shared Pydantic models
│   │   ├── __init__.py
│   │   ├── email.py                   # Email model
│   │   └── common.py                  # Common models
│   │
│   └── monitoring.py                  # Metrics & logging
│
├── scripts/                           # 🛠️ SCRIPTS (ORGANIZED BY CATEGORY)
│   ├── setup/                         # Setup scripts (run once)
│   │   ├── init_db.py                 # Database initialization
│   │   └── init_credentials.py        # Credential setup helper
│   │
│   ├── testing/                       # Testing scripts
│   │   ├── test_gmail_auth.py         # Gmail OAuth test
│   │   ├── test_openai_connection.py  # OpenAI API test
│   │   ├── test_all_connections.py    # Comprehensive health check
│   │   └── test_classification.py     # Quick classification test
│   │
│   ├── operations/                    # Operational scripts (run repeatedly)
│   │   ├── run_classifier.py          # Run classifier on inbox
│   │   ├── run_orchestrator.py        # Run full email workflow
│   │   ├── run_scheduler.py           # Start scheduler daemon
│   │   └── analyze_mailbox_history.py # Mailbox analysis
│   │
│   └── maintenance/                   # Maintenance scripts
│       ├── clean_old_tokens.py        # Clean expired OAuth tokens
│       ├── backup_database.py         # Database backup
│       └── reset_preferences.py       # Reset sender preferences
│
├── tests/                             # 🧪 TESTS (ORGANIZED BY MODULE)
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   │
│   ├── classification/                # Classification tests
│   │   ├── __init__.py
│   │   ├── test_rule_agent.py
│   │   ├── test_history_agent.py
│   │   ├── test_llm_agent.py
│   │   └── test_orchestrator.py
│   │
│   ├── drafts/                        # Draft generation tests
│   │   ├── __init__.py
│   │   └── test_tone_agents.py
│   │
│   ├── review/                        # Review system tests
│   │   ├── __init__.py
│   │   └── test_digest_agent.py
│   │
│   ├── tools/                         # Email tools tests
│   │   ├── __init__.py
│   │   ├── test_gmail_tools.py
│   │   └── test_ionos_tools.py
│   │
│   ├── integration/                   # Integration tests
│   │   ├── __init__.py
│   │   ├── test_e2e_real_gmail.py     # E2E test with real Gmail
│   │   └── test_full_workflow.py      # Full orchestration test
│   │
│   └── db/                            # Database tests
│       ├── __init__.py
│       └── test_models.py
│
├── credentials/                       # OAuth credentials (gitignored)
│   ├── gmail_account_1.json
│   ├── gmail_account_2.json
│   └── ...
│
├── tokens/                            # Cached OAuth tokens (gitignored)
│   ├── gmail_account_1_token.json
│   └── ...
│
├── user-feedback/                     # User stories and feedback
│   ├── user-stories/
│   └── to-dos/
│
└── archive/                           # NEW: Archive for deprecated code
    ├── modules/                       # Old modules/email/ (after merge)
    ├── old_classifier/                # Old classification layers
    └── deprecated_scripts/            # Old scripts
```

---

## Migration Steps

### Step 1: Create New Directory Structure

```bash
# Create docs/ hierarchy
mkdir -p docs/phases docs/api docs/diagrams

# Create agent_platform/ subdirectories
mkdir -p agent_platform/classification/agents
mkdir -p agent_platform/classification/guardrails
mkdir -p agent_platform/drafts/agents
mkdir -p agent_platform/review/agents
mkdir -p agent_platform/labels/agents
mkdir -p agent_platform/rag
mkdir -p agent_platform/orchestration

# Create scripts/ subdirectories
mkdir -p scripts/setup
mkdir -p scripts/testing
mkdir -p scripts/operations
mkdir -p scripts/maintenance

# Create tests/ subdirectories
mkdir -p tests/classification
mkdir -p tests/drafts
mkdir -p tests/review
mkdir -p tests/tools
mkdir -p tests/integration
mkdir -p tests/db

# Create archive/
mkdir -p archive
```

### Step 2: Move Documentation Files

```bash
# Move all markdown files to docs/
mv *.md docs/  # Except README.md

# Move README.md content to docs/README.md, create new short README.md
# (Manual step)

# Move PHASE files to docs/phases/
mv docs/PHASE_*.md docs/phases/

# Organize remaining docs
# (Manual step: categorize files into api/, diagrams/, etc.)
```

**File Mapping:**

| Current Location | New Location |
|------------------|--------------|
| README.md | docs/PROJECT_OVERVIEW.md |
| README.md (new, short) | README.md |
| PROJECT_SUMMARY.md | docs/PROJECT_SUMMARY.md |
| SETUP_GUIDE.md | docs/SETUP_GUIDE.md |
| DEPLOYMENT.md | docs/DEPLOYMENT.md |
| NEXT_STEPS.md | docs/NEXT_STEPS.md |
| ARCHITECTURE_MIGRATION.md | docs/ARCHITECTURE_MIGRATION.md |
| DIRECTORY_CLEANUP.md | docs/DIRECTORY_CLEANUP.md |
| CONNECTION_TESTS.md | docs/CONNECTION_TESTS.md |
| PHASE_1_*.md | docs/phases/PHASE_1_*.md |
| PHASE_2_*.md | docs/phases/PHASE_2_*.md |
| ... | ... |

### Step 3: Reorganize Scripts

```bash
# Setup scripts
mv scripts/init_db.py scripts/setup/
# Create scripts/setup/init_credentials.py (new)

# Testing scripts
mv scripts/test_gmail_auth.py scripts/testing/
mv scripts/test_openai_connection.py scripts/testing/
mv scripts/test_all_connections.py scripts/testing/

# Operational scripts
mv scripts/run_classifier.py scripts/operations/
mv scripts/run_responder.py scripts/operations/  # If exists
mv scripts/run_scheduler.py scripts/operations/
mv scripts/analyze_mailbox_history.py scripts/operations/

# Maintenance scripts
# (Create new scripts in scripts/maintenance/)
```

### Step 4: Merge modules/email into agent_platform

```bash
# Copy guardrails
cp modules/email/guardrails/*.py agent_platform/guardrails/

# Copy tools
cp modules/email/tools/*.py agent_platform/tools/

# Refactor agents
# (Manual: Extract responder logic to agent_platform/drafts/agents/)

# Archive old modules/
mv modules/ archive/modules_old/
```

**Detailed Merge Plan:**

| modules/email/ | agent_platform/ |
|----------------|-----------------|
| agents/classifier.py | classification/agents/llm_agent.py (refactored) |
| agents/responder.py | drafts/agents/tone_agents.py + orchestrator_agent.py |
| agents/orchestrator.py | orchestration/email_orchestrator.py |
| agents/backup.py | Keep in archive (implement later with SDK) |
| guardrails/*.py | guardrails/*.py (copy + update imports) |
| tools/*.py | tools/*.py (copy + update imports) |
| schemas.py | Merge into classification/models.py, drafts/models.py |

### Step 5: Reorganize Tests

```bash
# Move existing tests to appropriate subdirectories
# (Manual: categorize tests by module)

# Create new test structure
# tests/classification/test_*.py
# tests/drafts/test_*.py
# etc.
```

### Step 6: Update Imports Throughout Codebase

**Before:**
```python
from modules.email.guardrails.pii_guardrail import pii_detector_agent
from modules.email.tools.gmail_tools import fetch_unread_emails
```

**After:**
```python
from agent_platform.guardrails.pii_guardrail import pii_detector_agent
from agent_platform.tools.gmail_tools import fetch_unread_emails
```

**Automated Migration Script:**

Create `scripts/maintenance/update_imports.py`:
```python
#!/usr/bin/env python3
"""
Update imports after directory reorganization.

Replaces:
- from modules.email.* → from agent_platform.*
- from platform.* → from agent_platform.*
"""

import os
import re
from pathlib import Path

def update_imports_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace imports
    original_content = content
    content = re.sub(r'from modules\.email\.', 'from agent_platform.', content)
    content = re.sub(r'from platform\.', 'from agent_platform.', content)
    content = re.sub(r'import modules\.email\.', 'import agent_platform.', content)

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Updated: {filepath}")

def main():
    # Update all Python files
    for filepath in Path('.').rglob('*.py'):
        if 'venv' not in str(filepath) and 'archive' not in str(filepath):
            update_imports_in_file(filepath)

if __name__ == '__main__':
    main()
```

### Step 7: Create New README.md (Short Overview)

**New README.md:**
```markdown
# Email Agent Platform

Multi-agent email automation platform built with OpenAI Agents SDK.

## Features

- 🤖 **AI-Powered Classification** - 3-layer pipeline (Rule → History → LLM)
- 📧 **Smart Draft Generation** - 3 tone variants (professional, casual, empathetic)
- 🔄 **Adaptive Learning** - EMA-based sender preference learning
- 🛡️ **Security Guardrails** - PII detection, phishing protection, compliance
- 📊 **Review & Digest** - Daily digest emails for low-confidence items
- ⏰ **Automated Scheduling** - APScheduler for inbox checks and backups

## Quick Start

```bash
# 1. Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys and credentials

# 3. Initialize database
python scripts/setup/init_db.py

# 4. Test connections
python scripts/testing/test_all_connections.py

# 5. Run classification
python scripts/operations/run_classifier.py
```

## Documentation

📚 **Complete documentation:** [docs/](docs/)

- [Setup Guide](docs/SETUP_GUIDE.md) - Detailed setup instructions
- [Architecture](docs/ARCHITECTURE.md) - System architecture overview
- [Next Steps](docs/NEXT_STEPS.md) - Future development roadmap
- [API Reference](docs/api/) - API documentation

## Architecture

```
Classification Pipeline (Early Stopping):
  Rule Layer (40-60% hit, <1ms) → History Layer (20-30% hit, <10ms) → LLM Layer (10-20%, 1-3s)
```

Built with:
- OpenAI Agents SDK
- Python 3.10+
- Gmail API / IMAP
- SQLAlchemy + SQLite
- Pydantic (Structured Outputs)

## Testing

```bash
# Health check
python scripts/testing/test_all_connections.py

# E2E test with real Gmail
python tests/integration/test_e2e_real_gmail.py
```

## License

MIT

---

For detailed documentation, see [docs/](docs/).
```

### Step 8: Clean Up Root Directory

**Files to Keep in Root:**
- README.md (new, short version)
- .env
- .env.example
- .gitignore
- requirements.txt
- pyproject.toml (NEW)
- LICENSE

**Files to Move/Archive:**
- All *.md → docs/
- test_*.py → tests/ (if any remain)
- init_*.py → scripts/setup/

### Step 9: Create pyproject.toml (Modern Python Packaging)

**New File:** `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-platform"
version = "1.0.0"
description = "Multi-agent email automation platform"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["email", "automation", "ai", "agents", "openai"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "openai>=1.0.0",
    "agents>=0.1.0",
    "google-auth>=2.0.0",
    "google-auth-oauthlib>=0.5.0",
    "google-api-python-client>=2.0.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.0.0",
    "apscheduler>=3.10.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/agent-platform"
Documentation = "https://github.com/yourusername/agent-platform/tree/main/docs"
Repository = "https://github.com/yourusername/agent-platform"

[tool.setuptools]
packages = ["agent_platform"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Enable gradually
```

### Step 10: Update .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
build/
dist/
*.egg-info/

# Environment
.env
.env.local

# Credentials & Tokens
credentials/*.json
tokens/*.json
!credentials/.gitkeep
!tokens/.gitkeep

# Database
*.db
*.sqlite
platform.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log

# OS
.DS_Store
Thumbs.db

# Archive (keep in git for reference, but exclude from builds)
archive/
```

---

## Validation Checklist

After reorganization, validate:

### Structure Validation

- [ ] All markdown files in `docs/`
- [ ] No Python files in root (except setup.py if added)
- [ ] Scripts organized by category
- [ ] Tests organized by module
- [ ] `modules/email/` archived
- [ ] All imports updated

### Import Validation

```bash
# Run import checker
python scripts/maintenance/update_imports.py

# Verify no broken imports
python -m pytest tests/ --collect-only
```

### Test Validation

```bash
# Run all tests
python -m pytest tests/

# Run specific module tests
python -m pytest tests/classification/
python -m pytest tests/integration/
```

### Documentation Validation

- [ ] README.md links work
- [ ] All docs/ files accessible
- [ ] Phase documents properly organized
- [ ] API docs complete

### Package Validation

```bash
# Test package installation
pip install -e .

# Test imports
python -c "from agent_platform.classification import classify_email"
python -c "from agent_platform.tools.gmail_tools import fetch_unread_emails"
```

---

## Rollback Plan

If reorganization causes issues:

```bash
# Rollback via git
git checkout <commit-before-reorganization>

# Or restore from backup
cp -r agent-platform_backup/* .
```

**Recommendation:** Create full backup before starting:
```bash
cp -r agent-platform/ agent-platform_backup/
```

---

## Benefits After Cleanup

### For Developers

1. ✅ **Clear Structure** - Easy to find code
2. ✅ **Organized Docs** - All documentation in `docs/`
3. ✅ **Categorized Scripts** - Setup vs testing vs operations
4. ✅ **Modular Tests** - Tests organized by module
5. ✅ **Modern Packaging** - pyproject.toml for clean installs

### For Maintainability

1. ✅ **Single Email System** - No more dual systems confusion
2. ✅ **SDK-First Architecture** - All agents use OpenAI SDK patterns
3. ✅ **Clear Deprecation Path** - Old code in archive/
4. ✅ **Consistent Naming** - agent_platform everywhere
5. ✅ **Import Clarity** - Logical import paths

### For Onboarding

1. ✅ **Short README** - Quick overview in root
2. ✅ **Documentation Index** - docs/README.md guides to right docs
3. ✅ **Clear Entry Points** - scripts/operations/ for running things
4. ✅ **Testing Guide** - scripts/testing/ for health checks
5. ✅ **Architecture Docs** - docs/diagrams/ for visual understanding

---

## Timeline

**Estimated Time:** 1-2 days

- **Day 1 Morning:** Create directory structure, move files
- **Day 1 Afternoon:** Update imports, run validation
- **Day 2 Morning:** Test all functionality, fix issues
- **Day 2 Afternoon:** Documentation updates, final validation

---

## Next Steps

After cleanup:

1. **Start Phase 1.1** - Refactor classification to agents (see ARCHITECTURE_MIGRATION.md)
2. **Create Architecture Diagrams** - docs/diagrams/ for visual docs
3. **Write API Documentation** - docs/api/ for each module
4. **Setup CI/CD** - GitHub Actions for automated testing

---

## Summary

This cleanup transforms:

**From:**
```
❌ 18 markdown files scattered in root
❌ Two separate email systems (agent_platform + modules/email)
❌ Flat script organization
❌ Flat test organization
❌ Confusing structure for new developers
```

**To:**
```
✅ All docs in docs/ with clear hierarchy
✅ Single unified agent_platform with SDK patterns
✅ Scripts organized by purpose (setup/testing/operations/maintenance)
✅ Tests organized by module
✅ Clear, navigable structure for new developers
✅ Modern Python packaging with pyproject.toml
```

Result: **Professional, maintainable, SDK-first codebase** ready for production.
