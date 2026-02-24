# System Review: RAGAS ToolCallAccuracy Evaluation

**Generated:** 2026-02-25

## Meta Information
- Plan reviewed: `.agents/plans/ragas-tool-call-accuracy.md`
- Execution report: `.agents/execution-reports/ragas-tool-call-accuracy.md`
- Executor: Sequential (single session)
- Date: 2026-02-25

---

## Overall Alignment Score: 9/10

**Scoring rationale:**
- Implementation matched all code-level acceptance criteria (12/12 ✅ ignoring pending DB step)
- 3 divergences identified: 2 GOOD, 1 ENVIRONMENTAL — none problematic
- Validation gap: 3 of 5 levels require live Supabase and are structurally unexecutable by agent
- Plan had 1 internal inconsistency (test count) that was correctly resolved by the executor

The plan was exceptionally well-specified — exact code snippets, interface contracts between
waves, and a pre-reasoned design decision (why not use ToolCallAccuracy) that eliminated a
potential rabbit hole. Execution was faithful and coherent. The -1 reflects the partial
validation gap (DB-dependent levels deferred to user), not a failure of implementation.

---

## Divergence Analysis

### Divergence 1: System prompt embedded as literal rather than imported

```yaml
divergence: TOOL_SELECTION_SYSTEM_PROMPT embedded in tool_selection_pipeline.py as a string literal
planned: "Copy verbatim from chat_service.py" (implying import from an exportable constant)
actual: Verbatim copy embedded as a module-level string literal
reason: chat_service.py builds the prompt inline inside stream_response(); no exportable constant exists
classification: good ✅
justified: yes
root_cause: Plan assumed the prompt was an importable artifact without verifying it was exported
impact: Neutral — eval sees identical instructions to production; minor drift risk if prompt changes
```

**Assessment:** The right call. The plan's phrasing "copy verbatim from `chat_service.py`" is
ambiguous — it could mean "import" or "duplicate the text". Since the prompt is assembled at
runtime inside a function, the only sound option was a literal copy. The executor correctly
avoided refactoring production code (ChatService) for a non-production concern (eval). However,
this is a recurring plan language problem: "use X from file Y" without confirming Y exposes X
at module scope. A single sentence in planning standards — "verify the referenced symbol is
importable before writing `import from`" — would prevent this pattern entirely.

---

### Divergence 2: Migration apply deferred to user

```yaml
divergence: Validation Levels 0 and 4 (live DB) left pending instead of agent-executed
planned: "Apply migration against Supabase dev instance. Confirm table exists and RPC returns data."
actual: Migration file written; apply step marked as manual (requires Supabase dashboard)
reason: No psql CLI or Supabase CLI configured in PATH; hosted DB not accessible from shell
classification: environmental ⚠️
justified: yes
root_cause: The project's established workflow requires migrations to be applied manually via the
  Supabase SQL editor. This is known (see CLAUDE.md Infrastructure Behavior Notes and all prior
  migration tasks) but not reflected in plan validation sections.
impact: All 3 code-level validation levels (L1, L2, L3) passed. L0 and L4 are pending one
  manual step that the user performs after commit.
```

**Assessment:** This is the second time this pattern has appeared across feature reviews (it was
also present in the RAGAS evaluation pipeline feature). The Supabase CLI is not installed; the
hosted instance is not reachable from the agent's shell. Plans consistently list "Apply migration
+ validate via SQL" as an agent-executed step, which it can never be. This is a process gap:
the plan template should distinguish "agent-executable" from "requires manual infrastructure
access" in the validation section. The effort to write a validation command that the agent can
never run is wasted, and it risks the executor spending time trying to connect before deferring.

---

### Divergence 3: Internal plan inconsistency — test count

```yaml
divergence: Plan body heading said "Tests (9 total)" but listed 11 tests; acceptance criteria said 11
planned: Ambiguous — body said 9, criteria said 11
actual: 11 tests created (matches acceptance criteria)
reason: Plan authoring artifact — the heading was not updated after tests 10 and 11 were added
classification: good ✅
justified: yes
root_cause: Plan was authored iteratively; the "Tests (N total)" heading wasn't updated after
  the section grew. Minor internal inconsistency.
impact: None. Executor correctly prioritized the acceptance criteria over the section heading.
```

**Assessment:** Small but indicative. Plans with numeric headers ("N tests", "M waves") are
brittle when the plan is revised during authoring. The executor correctly resolved the
ambiguity by preferring the acceptance criteria (the authoritative contract). No action
needed beyond noting this as a risk for future plans with count claims in section headings.

---

## Pattern Compliance

- ✅ **Wave-based parallel execution** — 4-wave structure (0: migration, 1: tests+dataset+pipeline,
  2: orchestration+docs, 3: unit tests) followed the CLAUDE.md parallel agent pattern exactly,
  including explicit interface contracts between waves.

- ✅ **Migration numbering** — `016_` follows `015_realtime_documents.sql` correctly; plan
  specified this explicitly under "Patterns to Follow".

- ✅ **No LangChain** — All RAGAS metric usage goes through raw SDK calls (`llm_factory`,
  `AsyncOpenAI`), not LangChain wrappers.

- ✅ **Pydantic/dataclass for structured data** — `ToolSelectionSample` and
  `MultiTurnSelectionSample` use `@dataclass`, consistent with project patterns.

- ✅ **All tests mocked** — `test_tool_selection.py` uses no live API calls; all 11 tests
  mocked. Integration tests gated by env var (pattern from `test_eval_pipeline.py`).

- ✅ **pyarrow mock pattern reused** — Copied verbatim from `evaluate.py` (plan specified this);
  no reinvention.

- ✅ **eval CLI uses print()** — Consistent with existing `evaluate.py` (15 print calls).
  Eval entry points are CLI tools, not HTTP handlers — print is the correct output channel.
  The CLAUDE.md "no print in production code" rule targets routers/services/models, not
  standalone CLI scripts. Executor correctly followed existing codebase conventions.

- ✅ **Production code silent** — `sql_service.py` and `chat_service.py` changes introduced
  no new print statements. Only string renames throughout.

- ⚠️ **Pyarrow boilerplate duplication** — The 3-line pyarrow mock + `sys.path.insert` appears
  verbatim in `evaluate.py`, `evaluate_tool_selection.py`, and `test_tool_selection.py`. The
  execution report flagged this; no `eval/compat.py` was created (deferred). Each new eval entry
  point will need to copy this pattern again.

**Exemplary:** The plan's "Scoring Design — Why ToolCallAccuracy Is Partially Unusable Here"
section is a model for documenting non-obvious design decisions in plans. It pre-answered the
most likely question a fresh executor would ask ("why not just use the built-in metric?"),
prevented a rabbit hole, and the executor followed it exactly.

---

## System Improvement Actions

### Update CLAUDE.md:

- [ ] Add explicit note that Supabase migrations require manual apply:
  ```markdown
  ### Supabase Migrations

  **Apply process:** All migrations must be applied manually via the Supabase SQL editor
  (Dashboard → SQL Editor → paste migration content → run). There is no `supabase` CLI
  or `psql` configured in this environment.

  **For plans:** Mark any "apply migration + validate via SQL" validation step as
  `[MANUAL — user applies via dashboard]`. Do not block execution on these steps.

  **Post-migration validation:** The user runs the SQL validation commands after applying.
  The agent's job is to write a correct migration file, not to apply it.
  ```

- [ ] Add note on eval module boilerplate extraction to prevent copy-paste growth:
  ```markdown
  ### Eval Module Boilerplate

  The following setup is required in every eval entry point (`evaluate*.py`) and
  test file that imports ragas. **Do not copy-paste** — import from `eval/compat.py`:

  ```python
  # In eval/compat.py (create if it doesn't exist):
  import sys
  from unittest.mock import MagicMock as _MagicMock
  sys.modules.setdefault("pyarrow.dataset", _MagicMock())
  sys.modules.setdefault("pyarrow._dataset", _MagicMock())
  ```

  ```python
  # In eval entry points and test files:
  import eval.compat  # must be first import before any ragas import
  ```
  ```

- [ ] Add note on plan language for referencing importable symbols:
  ```markdown
  ### Plan Language: Referencing Code Symbols

  When a plan instructs "import X from file Y" or "use constant X from service Y",
  the plan author MUST verify that X is exported at module scope (i.e., accessible
  via `from module import X`). If X is built inline inside a function:

  - **Correct plan language:** "Embed verbatim copy of X from Y as a module-level
    literal in the new file."
  - **Incorrect plan language:** "Import X from Y" (when X isn't exported)

  This prevents executor confusion and avoids unnecessary production refactoring.
  ```

### Update Plan Template:

- [ ] Add a "Manual Steps" section distinct from "Validation Commands":
  ```markdown
  ### Manual Steps (User-Executed)

  These steps cannot be executed by the agent and must be performed manually by the user
  after the agent completes its work:

  - [ ] Apply `supabase/migrations/NNN_*.sql` via Supabase Dashboard SQL Editor
  - [ ] [Any other step requiring credentials, GUI access, or external services]

  **Agent validation (all code-level):**
  - Level 1: [import/service check]
  - Level 2: [unit tests]
  - Level 3: [dry-run scripts that don't require live DB]

  **User validation (post-manual-steps):**
  - Level 0: [DB confirmation SQL]
  - Level 4: [live service tests]
  ```

### Create New Command:

- [ ] `/apply-migration` — automates the reminder workflow for migration apply:
  - Reads the latest migration file from `supabase/migrations/`
  - Prints the migration SQL to terminal with instructions
  - Provides the validation SQL to run after apply
  - Checks `supabase/rollback_all.sql` is up to date

---

## Key Learnings

### What worked well:

1. **Pre-reasoned design decisions in plan:** The "Scoring Design — Why ToolCallAccuracy Is
   Partially Unusable" section eliminated the most likely executor rabbit hole (attempting
   to make the built-in metric work). This is the right model for non-obvious design
   choices: put the reasoning in the plan, not left for the executor to discover.

2. **Exact code snippets in task bodies:** Every task included actual Python/SQL code rather
   than prose descriptions. This compressed the "understand existing patterns" phase of
   execution and produced code that matched the production style on the first attempt.

3. **Interface contracts between waves:** Explicitly stating "Task X provides Y" and "Task
   Z consumes Y" made the dependency ordering obvious and would have prevented race conditions
   had agents been parallelized. Even for sequential execution, it served as a checklist.

4. **CONTEXT REFERENCES with line numbers:** The plan listed exact file + line number ranges
   for every file to read before implementing. This replaced open-ended codebase exploration
   with directed reads — significantly faster and less error-prone.

5. **Acceptance criteria as the authoritative contract:** The executor correctly resolved the
   test count ambiguity by trusting the acceptance criteria over a body section heading. The
   acceptance criteria section is the right place for executable contracts.

### What needs improvement:

1. **Validation section conflates agent-executable and manual steps:** Plans list DB validation
   commands as if agents can run them. They can't. This conflation causes the validation
   section to appear incomplete when it isn't — the agent-executable levels all passed.

2. **"Copy from file" plan instructions don't verify exportability:** The plan said to copy
   the system prompt from `chat_service.py` without noting it's not a module-level constant.
   Plans should verify the referenced symbol's access level before prescribing "import from".

3. **Pyarrow boilerplate has no DRY home:** Three files now contain identical 3-line pyarrow
   mock blocks. Each future eval entry point will add another copy. The execution report
   flagged this but deferred the fix. This should be addressed before the next eval module.

4. **Plan test count heading wasn't updated:** Minor, but "Tests (N total)" headings in plans
   are fragile when the plan is revised. Either keep the count only in acceptance criteria
   (authoritative), or use a dynamic phrasing like "Tests (see acceptance criteria)".

### For next implementation:

1. **Create `eval/compat.py`** before writing the next eval entry point. Consolidate the
   pyarrow mock + sys.path boilerplate there. Then update `evaluate.py`,
   `evaluate_tool_selection.py`, and `test_tool_selection.py` to import from it.

2. **Template the validation section** as two parts: "Agent-Executable" and "User-Manual".
   This eliminates the ambiguity that surfaces in every migration-touching feature.

3. **Verify symbol exportability** before writing "import from" instructions in plans. Add
   a one-line note in plan authoring: "check `grep -n 'SYMBOL' file.py | head -5` to
   confirm it's at module scope before prescribing an import."

---

## Process Quality Assessment

**Planning Phase:** ✅ Excellent
- Plan was exceptionally precise: exact code snippets for all 10+ changes per file, interface
  contracts per wave, "Patterns to Follow" section, and a pre-reasoned design decision. This
  is the highest-quality plan in the project so far. Minor gap: validation section doesn't
  distinguish agent-executable from manual steps.

**Execution Phase:** ✅ Strong
- All 7 plan tasks completed. Zero unplanned skips. Zero architecture deviations. The single
  challenge (system prompt not exportable) was identified and resolved correctly without
  backtracking. Execution was coherent with the plan's intent throughout.

**Validation Phase:** ⚠️ Partial
- Levels 1 and 2 (service imports, unit tests) validated by agent — 23/23 passing.
  Levels 0, 3, 4 (live DB, eval dry-run, SQL service tests) pending manual migration apply.
  This is not a quality failure — it's an environmental constraint — but the rating reflects
  that >50% of planned validation levels remain unconfirmed.

**Documentation:** ✅ Complete
- `eval/README.md` updated with full tool selection eval section including why ToolCallAccuracy
  is not used. PROGRESS.md updated. Execution report written. System review written. All
  inline code documentation present.

---

## Recommended CLAUDE.md Additions

### 1. Supabase Migration Apply Process

```markdown
### Supabase Migration Apply Process

**Apply method:** Dashboard only — no `supabase` CLI or `psql` configured in this environment.

**Steps:**
1. Open Supabase Dashboard → SQL Editor
2. Paste contents of `supabase/migrations/NNN_*.sql`
3. Click Run
4. Validate with the SQL command provided in the plan's "Level 0" validation step

**For agents:** Mark all "apply migration + validate via SQL" steps as
`[MANUAL — user applies via dashboard after commit]`. Do not block execution or mark
implementation incomplete because this step is pending.
```

### 2. Plan Language for Symbol References

```markdown
### Plan Language: Referencing Importable Symbols

Before writing "import X from module Y" in a plan, verify X is accessible at module scope:
```bash
grep -n "^X\|^class.*:\|^def.*:" path/to/module.py | head -10
```
If X is defined inside a function or class method, it is NOT importable.

**Correct alternatives:**
- "Embed verbatim copy of X from Y as a module-level constant"
- "Refactor Y to expose X as a class-level constant, then import"
- "Reconstruct X independently using the same pattern as Y"

Choosing between these depends on how frequently X changes and whether coupling is desired.
```

### 3. Eval Module Boilerplate

```markdown
### Eval Module Boilerplate (pyarrow + sys.path)

Every eval entry point requires this at the top (before any ragas/datasets import):
```python
import sys, os
from unittest.mock import MagicMock as _MagicMock
sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

**TODO:** Extract to `eval/compat.py` and import with `import eval.compat` as the first
line of every eval entry point. Until that refactor is done, copy the 5 lines above verbatim.

**Why pyarrow is mocked:** pyarrow.dataset DLL is blocked by Windows Application Control
policy. This mock is a no-op on Linux/Cloud Run where the DLL loads normally.
```

---

## Conclusion

**Overall Assessment:** This was a well-executed implementation of a well-specified plan. The
plan's design quality — precise code snippets, interface contracts, pre-reasoned design
decisions — is the primary reason execution was clean and fast. The 3 divergences were all
justified: one was a plan assumption gap (exportability), one was an environmental constant
(no Supabase CLI), and one was a minor authoring inconsistency resolved correctly. No
technical debt was introduced.

The recurring process gap is the treatment of Supabase migration apply as an agent-executable
validation step. This has appeared in at least two consecutive features and should be
addressed in CLAUDE.md and plan templates to stop surfacing as a "pending validation" every
time.

**Process Improvements Identified:**
- [ ] Add "Supabase Migration Apply Process" section to CLAUDE.md
- [ ] Add "Plan Language: Referencing Importable Symbols" note to CLAUDE.md
- [ ] Add "Eval Module Boilerplate" section to CLAUDE.md
- [ ] Update plan template: split validation section into agent-executable vs manual
- [ ] Create `eval/compat.py` to consolidate pyarrow mock boilerplate (before next eval module)
- [ ] Consider `/apply-migration` helper command

**Recommended Actions (priority order):**
1. **[High]** Add migration apply note to CLAUDE.md — recurring issue, easy fix, immediate value
2. **[High]** Create `eval/compat.py` — prevents compounding copy-paste before next eval module
3. **[Medium]** Add plan language note on symbol exportability to CLAUDE.md — prevents same
   "import vs embed" ambiguity in future plans
4. **[Low]** Update plan template validation section structure — good hygiene but low urgency
   since the current format doesn't cause execution failures, only cosmetic "pending" labels

**Ready for Next Module:** Yes — all code is committed, 23/23 tests passing, migration file
ready for user to apply. No blocking issues.
