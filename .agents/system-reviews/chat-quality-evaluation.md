# System Review: chat-quality-evaluation

**Generated:** 2026-02-26

## Meta Information
- Plan reviewed: `.agents/plans/chat-quality-evaluation.md`
- Execution report: `.agents/execution-reports/chat-quality-evaluation.md`
- Executor: Team-based parallel (lead + 2 agents: pipeline-engineer, test-engineer)
- Date: 2026-02-26

---

## Overall Alignment Score: 9/10

**Scoring rationale:**
- All 5 tasks completed, all acceptance criteria met
- Single divergence (import placement) was a plan internal inconsistency, self-corrected by both agents independently
- All 5 validation levels passed — no DB dependency, so all were agent-executable (contrast with prior eval features)
- Parallel execution worked cleanly: Wave 1 agents self-resolved without blocking each other
- -1 for the plan internal inconsistency between pipeline spec and test spec (preventable)
- No technical debt introduced; zero regressions across 127 tests

The plan was exceptionally prescriptive — full code implementations embedded inline for all three new
files, explicit interface contracts, patterns referenced with file + line numbers. This level of
specification is why execution was fast (~15 minutes), clean, and required only one correction.

---

## Divergence Analysis

### Divergence 1: `_rs` import moved to module level

```yaml
divergence: from services.retrieval_service import retrieval_service as _rs
planned: import inside run_chat_quality_pipeline() function body (plan pipeline spec, line 254)
actual: import at module level (line 16 of chat_quality_pipeline.py)
reason: T7 test spec required monkeypatch.setattr(mod._rs, ...) which needs _rs accessible
        as eval.chat_quality_pipeline._rs — impossible if imported only inside a function
classification: good ✅
justified: yes
root_cause: Plan internal inconsistency — pipeline spec said in-function, test spec T7 said
            module-level attribute access. Both parallel agents identified the same fix independently.
impact: Positive — module-level import is cleaner design. Functionally equivalent for the
        retrieval wrapper mechanism (Python module cache means same singleton object either way).
```

**Assessment:** Entirely self-correcting. Both the pipeline-engineer and test-engineer independently
diagnosed the same issue — a strong signal that the plan was comprehensible enough to reason about
even where it had a gap. The root cause is a specific and repeatable planning mistake: when a plan
specifies both a module and its unit tests, the import placement in the module spec must be validated
against the mock patterns in the test spec. An in-function import is invisible to
`monkeypatch.setattr(mod.symbol)` — this is a pytest monkeypatching constraint that should be
surfaced during planning, not discovered during execution.

The execution report recommends adding a "testability constraints" section to plans that reference
`monkeypatch` or `patch`. This is the right fix.

---

## Pattern Compliance

- ✅ **Wave-based parallel execution with interface contracts** — Wave 0 (blocker) → Wave 1
  (parallel: pipeline + tests) → Wave 2 (orchestrator + run_tests.sh check). Interface contracts
  explicit: "Task 0.1 provides `EvalSample.required_arg_keywords`", "Task 1.1 provides
  `run_chat_quality_pipeline(...) -> dict`". Followed CLAUDE.md parallel agent pattern exactly.

- ✅ **`finally` block for retrieval wrapper** — Plan specified this explicitly as a required pattern.
  Implementation uses `try/finally` to guarantee `_rs.retrieve_relevant_chunks` is restored even
  on stream exceptions. Consistent with the CLAUDE.md async generator cleanup pattern.

- ✅ **pyarrow mock pattern** — Copied from `evaluate.py` lines 25-27 as instructed. Pattern works.
  However, this is now the **third file** with this identical 3-line block. The previous system
  review (ragas-tool-call-accuracy) recommended creating `eval/compat.py` to consolidate this
  before the next eval module. That recommendation was not acted on, and the technical debt has
  compounded. See System Improvement Actions.

- ✅ **RAGAS 0.4.x API** — `EvaluationDataset`, `SingleTurnSample`, legacy metric singletons.
  Consistent with `evaluate.py` and `evaluate_tool_selection.py`.

- ✅ **Eval CLI uses print()** — Consistent with `evaluate.py`. Eval scripts are standalone CLI
  tools, not HTTP handlers. The CLAUDE.md "no print in production code" rule targets
  routers/services/models, not eval entry points. Executor applied this correctly.

- ✅ **eval_utils.get_eval_user_id() reused** — No reinvention of existing utilities.

- ✅ **LangSmith dataset naming convention** — `ir-copilot-chat-quality` consistent with
  `ir-copilot-eval` and `ir-copilot-tool-selection` naming pattern.

- ⚠️ **pyarrow boilerplate now in 3 files** — `evaluate.py`, `evaluate_tool_selection.py`,
  `evaluate_chat_quality.py`. Each future eval entry point will add a fourth. The previous review
  flagged this; it persists.

- ⚠️ **Task 2.2 (run_tests.sh) was a no-op** — The plan included a task to check and potentially
  update `run_tests.sh`. The glob on line 41 already covered `eval/tests/` so no change was needed.
  The task was correct to check (defensive), but inflated the task count and wave count slightly.
  Plans should label these as "verify-only" tasks to set correct expectations.

---

## System Improvement Actions

### Update CLAUDE.md:

- [ ] Add "testability constraints" note for plans using monkeypatch:
  ```markdown
  ### Plan Testability: Import Placement vs Mock Patterns

  When a plan specifies both a module and its unit tests, the **import placement** in the
  module must be cross-checked against the test mock patterns before finalizing:

  - `monkeypatch.setattr(mod.symbol, ...)` requires `symbol` to be a **module-level attribute**
  - `patch("module.path.symbol")` requires `symbol` to be importable at module scope
  - In-function imports are invisible to both patterns (not accessible as `mod.symbol`)

  **Rule:** If any test uses `monkeypatch.setattr(mod.X, ...)` or `patch("...X")`, verify
  that X is declared at module level (not inside a function). Add this as a planning
  cross-check when specifying both a module and its tests in the same plan.

  **Example of the gap:**
  ```python
  # Plan spec (pipeline) — in-function import (WRONG for testability)
  async def run_chat_quality_pipeline(...):
      from services.retrieval_service import retrieval_service as _rs  # ← invisible to monkeypatch
      ...

  # Plan spec (test T7) — module-level attribute access (requires module-level import)
  import eval.chat_quality_pipeline as mod
  monkeypatch.setattr(mod._rs, "retrieve_relevant_chunks", fake_retrieve)  # ← needs mod._rs
  ```
  ```

- [ ] Add note on `eval/compat.py` extraction (previously recommended, still unactioned):
  ```markdown
  ### Eval Module Boilerplate (pyarrow + sys.path)

  Every eval entry point (`evaluate*.py`) and test file that imports ragas requires this
  at the top. **Do not copy-paste.** Import from `eval/compat.py`:

  ```python
  # eval/compat.py (create if missing):
  import sys, os
  from unittest.mock import MagicMock as _MagicMock
  sys.modules.setdefault("pyarrow.dataset", _MagicMock())
  sys.modules.setdefault("pyarrow._dataset", _MagicMock())
  sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
  ```

  ```python
  # In each eval entry point — first import:
  import eval.compat  # noqa: F401 — must precede any ragas/datasets import
  ```

  **Why pyarrow is mocked:** pyarrow.dataset DLL blocked by Windows Application Control.
  No-op on Linux/Cloud Run.

  **Status:** Currently copied verbatim in evaluate.py, evaluate_tool_selection.py,
  evaluate_chat_quality.py. Consolidation deferred but should happen before next eval module.
  ```

- [ ] Add `--dry-run --limit 1` smoke validation pattern for eval scripts:
  ```markdown
  ### Eval Script Validation Pattern

  For eval scripts that call live LLMs and Supabase, add a `--dry-run --limit 1` smoke
  test to the plan's validation commands:

  ```bash
  # After unit tests pass, run live smoke test (requires .env + ingested docs):
  cd backend && uv run python eval/evaluate_chat_quality.py --dry-run --limit 1
  ```

  This catches runtime wiring issues (service imports, provider config, retrieval connection)
  without running a full 15-sample evaluation. Include in plan as "Level 4: Live smoke test"
  to separate from unit tests.
  ```

### Update plan-feature skill:

- [ ] Add cross-check requirement for import placement when specifying module + tests in same plan:
  ```markdown
  ### Testability Cross-Check (When Plan Specifies Module + Tests)

  Before finalizing a plan that specifies both a module and its unit tests, verify:
  - [ ] Any symbol accessed via `monkeypatch.setattr(mod.X, ...)` is at module scope in the module spec
  - [ ] Any symbol accessed via `patch("path.to.X")` is importable at module scope
  - [ ] In-function imports are not used for symbols that tests need to patch

  Mark this as a "Testability Constraints" note in the plan's Patterns to Follow section.
  ```

### No New Commands Needed

The existing `plan-feature` and `execute` skill coverage is adequate. The above CLAUDE.md
additions address the identified gaps at the right level (authoring guidelines).

---

## Key Learnings

### What worked well:

1. **Parallel agent resilience:** Both Wave 1 agents independently identified and corrected
   the same import placement inconsistency without blocking each other or requiring orchestrator
   intervention. This validates the parallel execution model — agents with sufficient context
   can self-correct minor plan gaps. The ~0 minutes lost on this issue is the best possible
   outcome for a plan gap.

2. **Full code in task bodies:** Every task in the plan included complete Python code, not
   prose descriptions. This produced correct implementations on the first attempt and eliminated
   the "pattern discovery" overhead that causes divergences in less-specified plans.

3. **Wave 0 as a clean blocker:** Making the dataset extension a standalone Wave 0 meant both
   Wave 1 agents could start with a known contract (`required_arg_keywords` guaranteed on all
   15 samples). The interface was clean, the dependency unambiguous.

4. **All validations agent-executable:** Unlike the previous eval feature (ragas-tool-call-accuracy),
   this plan had no DB migrations — so all 5 validation levels could be executed by the agent
   with no manual prerequisites. The execution report shows 5/5 validation commands passing.
   This is the ideal state for plan validation.

5. **keyword check before RAGAS pattern:** Running the deterministic keyword check first (no
   API calls) before the ~2-minute RAGAS phase is a good workflow design. The plan documented
   this clearly in the NOTES section ("Why keyword check before RAGAS?"), preventing the
   executor from questioning the ordering.

### What needs improvement:

1. **Plan cross-check: module spec vs test mock patterns:** The single divergence (import
   placement) was caused by not cross-checking the pipeline spec against T7's mock pattern.
   This is a repeatable mistake whenever a plan specifies both a module and its tests with
   monkeypatching. A 30-second mental check during planning prevents a discovered-at-execution gap.

2. **pyarrow boilerplate now in 3 files:** The previous system review (ragas-tool-call-accuracy)
   explicitly flagged this and recommended `eval/compat.py` as the fix. That recommendation
   was not implemented before this feature. The debt is now larger. It must be addressed before
   the fourth eval entry point is created.

3. **Task 2.2 (run_tests.sh) was defensive overhead:** The plan included a full wave task to
   check whether `run_tests.sh` needed updating. It didn't. For "verify and skip if already
   covered" tasks, plans should mark them as `VERIFY-ONLY (no-op if X already covers Y)` to
   avoid agents spending time on task setup/teardown for zero-change work.

4. **Automation target 70% vs 80% goal:** The plan-feature skill targets 80%+ automation. This
   plan achieved 70% (7/10). The 3 manual tests require live infra (real OpenAI + Supabase +
   ingested docs), which is a legitimate blocker for automation. However, the plan should
   explicitly justify the manual percentage rather than just labeling them "manual" in the
   testing summary.

### For next implementation:

1. **Create `eval/compat.py` before the next eval entry point.** Then update existing files.
   This is now urgent — it was already deferred once.

2. **Add "Testability Constraints" note to plans** that specify both a module and tests using
   monkeypatching. Verify import placement is at module scope before finalizing.

3. **Add `--dry-run --limit 1` as Level 4 validation** in eval script plans to catch live
   wiring issues without a full run.

---

## Process Quality Assessment

**Planning Phase:** ✅ Excellent
- Plan was highly prescriptive: complete code for all 3 new files, explicit wave structure with
  interface contracts, patterns referenced with file + line numbers, RAGAS API version pinned.
  Single gap: import placement inconsistency between pipeline spec and T7 test spec (preventable
  with a cross-check). Plan length: 595 lines (within 500-700 target).

**Execution Phase:** ✅ Strong
- All 5 tasks completed in wave order. Zero architecture deviations. Single plan gap (import
  placement) self-corrected by both agents in Wave 1 — no blocking coordination, no time lost.
  Team-based execution delivered the expected ~2x Wave 1 speedup.

**Validation Phase:** ✅ Complete
- All 5 validation levels executed and passed by the agent (no manual prerequisites). This is
  the cleanest validation outcome across all eval feature implementations to date.
  127/127 backend tests passing with zero regressions.

**Documentation:** ✅ Complete
- Execution report written, PROGRESS.md updated, system review written. Code comments present
  in new files. No gaps.

---

## Recommended CLAUDE.md Additions

### 1. Import Placement vs Test Mock Patterns

```markdown
### Plan Testability: Import Placement vs Mock Patterns

When a plan specifies both a module and its unit tests, cross-check import placement against
test mock patterns before finalizing:

- `monkeypatch.setattr(mod.X, ...)` requires X to be a **module-level attribute**
- `patch("path.to.module.X")` requires X to be importable at module scope
- In-function imports are invisible to monkeypatching

**Rule:** If any test uses `monkeypatch.setattr(mod.X, ...)`, verify X is declared at module
level in the module spec. Add this as a "Testability Constraints" note in the plan.
```

### 2. Eval Module Boilerplate (update existing CLAUDE.md entry)

*(Previous review recommended this; still not added. Add before next eval module.)*

```markdown
### Eval Module Boilerplate (pyarrow + sys.path)

Files: evaluate.py, evaluate_tool_selection.py, evaluate_chat_quality.py all contain this
verbatim block. Extract to eval/compat.py before creating another eval entry point:

```python
# eval/compat.py:
import sys, os
from unittest.mock import MagicMock as _MagicMock
sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```
Then in each eval file: `import eval.compat  # noqa: F401` as first import.
```

### 3. Eval Script Smoke Validation

```markdown
### Eval Script Validation

For plans that include eval scripts calling live LLMs/Supabase, add these validation levels:

**Level 3 (agent-executable):** pytest unit tests (all mocked)
**Level 4 (smoke — requires .env + ingested docs):**
```bash
cd backend && uv run python eval/evaluate_FEATURE.py --dry-run --limit 1
```
Expected: 1 question processed, RAGAS scores printed, no LangSmith push.
This catches live wiring issues (provider config, retrieval) without a full run.

**Level 5 (full run):** Remove --limit, remove --dry-run. Do outside plan validation.
```

---

## Conclusion

**Overall Assessment:** A clean, well-executed implementation with one self-corrected plan gap.
The plan's high specification density (full code inline, interface contracts, explicit RAGAS API
patterns) is the primary reason execution was fast and divergence-free in substance. The single
divergence was an internal plan inconsistency — the kind that a quick cross-check during planning
would catch. The team-based execution model proved resilient: both agents independently correcting
the same gap without blocking is the best possible outcome for a minor plan inconsistency.

Two technical debt items persist from the previous feature's system review that need resolution
before the next eval module:
1. `eval/compat.py` extraction (now in 3 files, will be 4)
2. Plan testability cross-check (import placement vs mock patterns)

**Process Improvements Identified:**
- [ ] Add import placement vs mock pattern cross-check to CLAUDE.md
- [ ] Create `eval/compat.py` (deferred from ragas-tool-call-accuracy review — now overdue)
- [ ] Add `--dry-run --limit 1` smoke test as Level 4 validation for eval script plans
- [ ] Update plan-feature skill: add testability cross-check requirement for module+tests plans

**Recommended Actions (priority order):**
1. **[High]** Create `eval/compat.py` — already deferred once, now 3 files affected, must happen
   before the next eval entry point is created
2. **[High]** Add import placement cross-check note to CLAUDE.md — prevents recurrence of this
   plan gap pattern
3. **[Medium]** Add eval script smoke validation pattern to CLAUDE.md — practical guidance for
   future eval plan authors
4. **[Low]** Update plan-feature skill with testability cross-check requirement — good guard rail
   but low urgency since agents can self-correct (as demonstrated here)

**Ready for Next Module:** Yes — all 127 tests passing, no regressions, changes unstaged for
user review.
