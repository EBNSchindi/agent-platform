# Session Notes - 2025-11-20

## Session Summary

**Duration:** ~4 hours
**Branch:** `feature/ensemble-classification-system`
**Status:** Phase 2 Part 1/5 Complete

---

## What Was Accomplished

### ✅ Phase 1 Complete (PR #8 Merged)

**Quick Win 1: Dokumentation Updates**
- Created `docs/phases/PHASE_1_STEP_2_COMPLETE.md` (~450 lines)
- Updated `PROJECT_SCOPE.md` (10 sections)
  - Version 2.1.0
  - Email Extraction marked as complete
  - Stats: ~6,430 lines code, 54 tests
  - Roadmap: 60% complete (3/5 steps)
- Added Extraction patterns to `CLAUDE.md`

**Quick Win 2: Classification Layer Rebalancing**
- Rule Layer Confidence adjustments:
  - Auto-Reply: 0.90 → 0.70
  - Newsletter: 0.85 → 0.65
  - System: 0.80 → 0.50 (**solves No-Reply problem!**)
- Threshold adjustments:
  - high_confidence: 0.85 → 0.90
  - medium_confidence: 0.60 → 0.65
- Created `docs/phases/PHASE_1_STEP_3_REBALANCING_PHASE1.md` (~550 lines)

**Results:**
- PR #8 merged successfully
- +1,233 insertions, -43 deletions
- No-Reply problem automatically solved
- 40% more emails reach History/LLM layers

---

## Phase 2 Started: 3-Layer Ensemble System

### Philosophy Shift

**From (Early-Stopping):**
```
Email → Rule Layer (0.65) → STOP ❌
```

**To (Ensemble Scoring):**
```
Email → All 3 Layers Parallel
       ├─ Rule Layer → Score
       ├─ History Layer → Score
       └─ LLM Layer → Score
             ↓
       Weighted Combination
             ↓
       Final Classification
```

### ✅ Part 1/5: Ensemble Models (Complete)

**File:** `agent_platform/classification/models.py` (+267 lines)

**Models Added:**
1. **LayerScore** - Individual layer result
2. **ScoringWeights** - Configurable weights (HITL adjustable)
3. **DisagreementInfo** - Layer disagreement tracking
4. **EnsembleClassification** - Combined ensemble result

**Key Features:**
- Weights default: Rule=0.20, History=0.30, LLM=0.50
- Bootstrap mode support (different weights for learning phase)
- Agreement metrics & confidence boosting
- Disagreement detection for HITL review

**Commit:** `03311a9` - "WIP: Phase 2 - Ensemble System Models (Part 1/5)"

---

## Next Session: Part 2/5 - Ensemble Classifier

### Tasks Remaining

**High Priority (Next Session):**
1. ✅ **1.1 Models** (~268 lines) - DONE
2. ⏳ **1.2 Ensemble Classifier** (~300 lines, 3-4h)
   - File: `agent_platform/classification/ensemble_classifier.py` (NEW)
   - Parallel execution of all 3 layers (asyncio.gather)
   - Weighted score combination
   - Agreement detection & boosting
   - Disagreement logging
3. ⏳ **1.3 Smart LLM Conditionals** (~100 lines, 1h)
   - Performance optimization: Skip LLM bei Agreement
   - Saves ~60-70% LLM costs
4. ⏳ **1.4 Migration** (~50 lines, 1-2h)
   - Rename UnifiedClassifier → LegacyClassifier
   - Set EnsembleClassifier as default
   - Update orchestrator

**Medium Priority:**
5. ⏳ **2.1 Scoring Weights Config** (2h)
6. ⏳ **2.2 Disagreement Tracking** (2h)
7. ⏳ **3.1 Whitelist/Blacklist** (1-2h)
8. ⏳ **3.2 History Layer Boost** (1h)

**Low Priority:**
9. ⏳ **4.1 Unit Tests** (1-2h)
10. ⏳ **4.2 Integration Tests** (1h)
11. ⏳ **5.1 Phase 2 Doc** (~600 lines)
12. ⏳ **5.2 PROJECT_SCOPE update** (~30 lines)

---

## Implementation Notes

### Ensemble Classifier Core Logic (Next)

```python
class EnsembleClassifier:
    async def classify(self, email: EmailToClassify) -> EnsembleClassification:
        # Step 1: Run all layers in parallel
        rule_score, history_score, llm_score = await asyncio.gather(
            self.rule_layer.classify(email),
            self.history_layer.classify(email),
            self.llm_layer.classify(email),
        )

        # Step 2: Get weights (bootstrap vs production)
        weights = self.weights.get_weights(
            is_bootstrap=self.is_bootstrap_phase(email.account_id)
        )

        # Step 3: Weighted combination
        final_importance = (
            rule_score.importance * weights[0] +
            history_score.importance * weights[1] +
            llm_score.importance * weights[2]
        )

        # Step 4: Agreement check
        if self._all_agree(rule_score, history_score, llm_score):
            confidence_boost = 0.2  # +20%
        elif not self._any_agree(...):
            confidence_boost = -0.2  # -20%
            self._log_disagreement(...)

        # Step 5: Build result
        return EnsembleClassification(...)
```

### Smart LLM Skip Logic (Next)

```python
def should_use_llm(self, rule_score, history_score) -> bool:
    # User override
    if user_wants_always_llm():
        return True

    # Disagreement
    if rule_score.category != history_score.category:
        return True

    # Low confidence
    avg_conf = (rule_score.confidence + history_score.confidence) / 2
    if avg_conf < 0.70:
        return True

    # Important emails
    if rule_score.importance > 0.80 or history_score.importance > 0.80:
        return True

    # Otherwise skip LLM (save costs!)
    return False
```

---

## Key Decisions Made

### User Preferences (HITL)

1. **Ensemble System over Bootstrap Mode**
   - User wanted: "LLM soll grundsätzlich bei jeder Email agieren"
   - Solution: All layers run, weighted combination
   - Instead of: Fixed 100-email bootstrap phase

2. **Scoring System over Early-Stopping**
   - Old: Rule (0.65) → Stop
   - New: Rule (0.65) + History (0.80) + LLM (0.92) → Weighted avg
   - Benefit: Maximum confidence and accuracy

3. **Dynamic Weights with HITL**
   - User can adjust weights (Rule/History/LLM)
   - System suggests adjustments based on disagreement
   - Bootstrap weights for learning phase

4. **Agreement-Based Confidence**
   - All 3 agree → +20% confidence boost
   - All disagree → -20% penalty + HITL review
   - Partial agreement → +10% boost

---

## Performance Considerations

### Smart LLM Skip (Optional)
- **Without skip:** 100% LLM usage → expensive
- **With skip:** ~30-40% LLM usage → 60-70% cost savings
- **Trigger:** Only use LLM when:
  - Rule + History disagree
  - Both have low confidence (<0.70)
  - Email is important (>0.80)
  - User enabled "Always LLM"

### Expected Metrics
- Rule Layer: Always runs (~1ms)
- History Layer: Always runs (~10ms)
- LLM Layer: Conditional (1-3s when used)
- Total: ~10ms-3s depending on LLM skip

---

## Files Modified This Session

```
agent_platform/classification/
├── models.py                        (+267 lines) ✅
├── importance_rules.py              (modified) ✅ [Phase 1]
└── orchestration/
    └── classification_orchestrator.py (modified) ✅ [Phase 1]

docs/phases/
├── PHASE_1_STEP_2_COMPLETE.md      (new, ~450 lines) ✅
└── PHASE_1_STEP_3_REBALANCING_PHASE1.md (new, ~550 lines) ✅

PROJECT_SCOPE.md                     (modified, 10 sections) ✅
CLAUDE.md                            (modified, +70 lines) ✅
```

**Total:** ~1,500 lines added/modified

---

## Git Status

**Current Branch:** `feature/ensemble-classification-system`
**Base Branch:** `main`
**Commits:**
- `03311a9` - WIP: Phase 2 - Ensemble System Models (Part 1/5)

**Previous PR:**
- PR #8 - "Classification Layer Rebalancing Phase 1" (MERGED)

---

## Next Steps (For Next Session)

1. **Start with:** Implement `EnsembleClassifier` class
2. **Files to create:**
   - `agent_platform/classification/ensemble_classifier.py`
3. **Reference implementations:**
   - `unified_classifier.py` for patterns
   - `importance_rules.py` for layer interfaces
4. **Test strategy:**
   - Unit tests after classifier complete
   - Integration tests with real emails
   - Manual testing with disagreement scenarios

**Estimated Time:** 8-10 hours remaining for Phase 2

---

## Questions for User (HITL)

**Answered:**
- ✅ Bootstrap Mode → Yes, but with Ensemble approach
- ✅ Ensemble vs Early-Stopping → Ensemble (all layers run)
- ✅ Weight adjustability → Yes, HITL parameter tuning

**Open:**
- Web UI for weight tuning? (or CLI-only for now?)
- Notification method for disagreements? (Email/Terminal/Both?)
- Auto-adjustment of weights based on accuracy? (or manual only?)

---

**Session End:** 2025-11-20 10:30 UTC
**Next Session:** Continue with EnsembleClassifier implementation
**Priority:** High (Core functionality)
