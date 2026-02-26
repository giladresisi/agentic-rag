# Execution Report: RAGAS Evaluation Pipeline

**Date:** 2026-02-25
**Plan:** `.agents/plans/ragas-evaluation-pipeline.md`
**Executor:** Sequential (initial pipeline by prior agent) + session follow-up (behavioral tests + integration fixture)
**Outcome:** ✅ Success

---

## Executive Summary

The RAGAS evaluation pipeline was built across two sessions. The first session (prior agent, commit `ca4c1e4`) implemented the core pipeline: golden dataset, retrieval+generation runner, RAGAS scoring entry point, 4 structural unit tests, and 6 postmortem documents. This session closed the behavioral test coverage gap identified in PROGRESS.md, added a self-contained integration test fixture that ingests docs and runs live retrieval/generation assertions, and added a process improvements note for the `ai-dev-env:execute` skill.

**Key Metrics:**
- **Tasks Completed:** All plan tasks + 3 user-requested extras
- **Tests Added:** 8 new (4 unit behavioral + 1 parametrized×3 + 1 RAGAS dataset shape + 2 integration)
- **Test Pass Rate:** 12/12 (100%) — 10 automated unit, 2 integration verified live
- **Files Modified/Created:** 5 modified, 1 created (`conftest.py`)
- **Lines Changed:** +357/-9 (this session); +1,188/-6 (full feature across both sessions)
- **Alignment Score:** 9/10

---

## Implementation Summary

### Prior session (commit `ca4c1e4`) — Core pipeline

| File | Purpose |
|------|---------|
| `backend/eval/dataset.py` | 15 `EvalSample` golden Q&A pairs across 6 postmortem docs |
| `backend/eval/pipeline.py` | `run_rag_pipeline(question)` — retrieval + structured LLM generation |
| `backend/eval/evaluate.py` | RAGAS scoring + LangSmith push (RAGAS 0.4.3 API) |
| `backend/eval/tests/test_eval_pipeline.py` | 4 structural unit tests (dataset shape, pipeline return type) |
| `backend/eval/postmortems/*.md` | 6 incident postmortem source documents |
| `backend/eval/requirements-eval.txt` | Eval-only deps (ragas, datasets) |

### This session — Behavioral tests + integration fixture

**1. Behavioral unit tests** (added to `test_eval_pipeline.py`):
- `test_pipeline_includes_all_retrieved_contexts` — verifies all 3 returned chunks are in `contexts`, in order
- `test_pipeline_passes_contexts_to_llm` — spies on `create_structured_completion` call_args, asserts both chunks + separator + question appear in the user message
- `test_off_topic_queries_return_no_context_fallback[x3]` — parametrized over 3 unrelated questions, all must return the anti-hallucination fallback
- `test_build_ragas_dataset_shape` — calls `build_ragas_dataset` with fake pipeline results, asserts `EvaluationDataset` has 15 samples with correct RAGAS field names

**2. Integration test fixture** (`backend/eval/tests/conftest.py`):
- Session-scoped `eval_ingestion_setup` fixture gated by `EVAL_DOCS_INGESTED=true` in `.env`
- Signs in with `TEST_EMAIL`/`TEST_PASSWORD` via Supabase auth to get the real user UUID (required to satisfy `documents.user_id` FK constraint)
- Cleans only eval postmortem docs for that user (by filename match, not full table wipe)
- Calls `process_document()` directly — same ingestion code path as HTTP endpoint, no server needed
- `extract_metadata=False` skips LLM metadata step for speed
- Yields the user UUID to tests; docs left in place for `evaluate.py` manual run

**3. `run_rag_pipeline` signature change** (`pipeline.py`):
- Added optional `user_id` parameter (default: placeholder UUID)
- Integration tests pass the real test user UUID so retrieval filter matches ingested docs

**4. `.env.example`**: Added `EVAL_DOCS_INGESTED=false` with warning note about DB cleanup behavior

**5. `PROGRESS.md`**: Updated feature status to ✅ Complete; added integration test pass confirmation; added Process Improvements section for `ai-dev-env:execute` skill coverage discipline

---

## Divergences from Plan

### Divergence #1: Only 4 of the planned behavioral scenarios were unit-testable

**Classification:** ⚠️ ENVIRONMENTAL

**Planned:** 3 behavioral test scenarios (in-distribution, new-document, no-context)
**Actual:** 2 of 3 covered by integration tests; new-document scenario documented as manual-only
**Reason:** "New-document queries" test requires uploading a document via the app UI and querying it — no way to automate this without a full E2E harness that controls document ownership and ingestion timing
**Root Cause:** Plan did not distinguish between unit-testable behavioral scenarios and true E2E scenarios requiring live ingestion
**Impact:** Neutral — the gap is documented and the remaining two scenarios are fully covered
**Justified:** Yes

### Divergence #2: Integration tests use real test user UUID, not placeholder

**Classification:** ✅ GOOD

**Planned:** `user_id="00000000-0000-0000-0000-000000000000"` (placeholder) throughout
**Actual:** Conftest signs in with test credentials to get real UUID; `run_rag_pipeline` now accepts `user_id` param
**Reason:** `documents.user_id` has a FK constraint to the `users` table — the placeholder UUID is not a real Supabase auth user and causes a `23503` constraint violation on insert
**Root Cause:** Plan note said "admin bypasses RLS, placeholder UUID is safe" — true for retrieval, false for insertion
**Impact:** Positive — correctly models real usage; pipeline now supports multi-user eval scenarios
**Justified:** Yes

### Divergence #3: RAGAS 0.4.3 API (prior session divergence, documented here)

**Classification:** ⚠️ ENVIRONMENTAL

**Planned:** `Dataset.from_dict()` (RAGAS 0.1.x API)
**Actual:** `EvaluationDataset` + `SingleTurnSample` (RAGAS 0.4.3 API); metrics from `ragas.metrics.collections`
**Reason:** Installed version was 0.4.3; plan was written against 0.1.x docs
**Root Cause:** Plan documentation lag — RAGAS had a major API break between 0.1.x and 0.2.x
**Impact:** Neutral — implementation is correct for installed version
**Justified:** Yes

---

## Test Results

**Tests Added (this session):** 8 test cases across 5 functions

| Test | Type | Result |
|------|------|--------|
| `test_pipeline_includes_all_retrieved_contexts` | Unit (mocked) | ✅ PASS |
| `test_pipeline_passes_contexts_to_llm` | Unit (mocked) | ✅ PASS |
| `test_off_topic_queries_return_no_context_fallback[cake]` | Unit (parametrized) | ✅ PASS |
| `test_off_topic_queries_return_no_context_fallback[FIFA]` | Unit (parametrized) | ✅ PASS |
| `test_off_topic_queries_return_no_context_fallback[Bitcoin]` | Unit (parametrized) | ✅ PASS |
| `test_build_ragas_dataset_shape` | Unit (lazy ragas import) | ✅ PASS |
| `test_in_distribution_query_live` | Integration (live DB + LLM) | ✅ PASS |
| `test_no_context_query_live` | Integration (live DB + LLM) | ✅ PASS |

**Full suite:** 12/12 passed (36.5s with integration tests; 8.9s unit-only)

---

## Validation Results

| Level | Command | Status | Notes |
|-------|---------|--------|-------|
| Unit tests | `uv run python -m pytest eval/tests/ -v` | ✅ 10/10 | No env vars required |
| Integration tests | `EVAL_DOCS_INGESTED=true uv run python -m pytest eval/tests/ -v` | ✅ 12/12 | Requires live Supabase + OpenAI |
| Default run (flag false) | `uv run python -m pytest eval/tests/ -v` | ✅ 10 passed, 2 skipped | Correct behavior |

---

## Challenges & Resolutions

**Challenge 1: FK constraint on placeholder user_id**
- **Issue:** `documents.user_id` FK to `users` table; placeholder UUID `00000000-...` not a real Supabase auth user
- **Root Cause:** Plan note about "admin bypasses RLS" was correct for retrieval but not for insert — RLS bypass ≠ FK bypass
- **Resolution:** Sign in with `TEST_EMAIL`/`TEST_PASSWORD` via `supabase.auth.sign_in_with_password()` to get real UUID; pass it through fixture → test → `run_rag_pipeline(user_id=...)`
- **Time Lost:** ~1 iteration (one failing test run)
- **Prevention:** Document in plan: "admin client bypasses RLS but not FK constraints — any direct DB insert must use a real user UUID"

**Challenge 2: `pytest.mark.skipif` evaluates at collection time**
- **Issue:** First attempt used `_SKIP_INTEGRATION = not os.getenv(...)` as a module-level variable; when Supabase env vars were set but `EVAL_DOCS_INGESTED` wasn't, tests ran and failed instead of skipping
- **Root Cause:** `skipif` condition is frozen at import time — can't be influenced by fixture setup
- **Resolution:** Moved skip logic into the fixture itself (`pytest.skip()` inside fixture body based on runtime env var check); integration tests depend on fixture rather than using `skipif`
- **Time Lost:** ~1 iteration
- **Prevention:** For env-var-gated integration tests, always use fixture-level `pytest.skip()` rather than module-level `skipif`

---

## Files Modified

**Eval tests (2 files):**
- `backend/eval/tests/test_eval_pipeline.py` — 8 new test cases, header docstring update, removed `_SKIP_INTEGRATION` variable (+141/-9)
- `backend/eval/tests/conftest.py` — new session fixture for DB clean + ingestion + user_id yield (+166/0)

**Pipeline (1 file):**
- `backend/eval/pipeline.py` — optional `user_id` parameter added to `run_rag_pipeline` (+14/-1)

**Config/docs (2 files):**
- `backend/.env.example` — `EVAL_DOCS_INGESTED=false` added (+5/0)
- `PROGRESS.md` — feature status, test table, integration pass confirmation, process improvements note (+59/-1)

**Total this session:** ~357 insertions, 9 deletions across 5 files

---

## Success Criteria Met

- [x] All plan acceptance criteria met (carried forward from prior session)
- [x] Behavioral unit tests cover multi-chunk retrieval, LLM message construction, anti-hallucination (3 variants), RAGAS dataset shape
- [x] Integration tests self-contained — clean DB, ingest docs, run assertions, no manual setup
- [x] Integration tests skip cleanly when `EVAL_DOCS_INGESTED=false` (default)
- [x] Both integration tests pass against live Supabase + OpenAI
- [x] `run_rag_pipeline` remains backward-compatible (user_id defaults to placeholder)
- [x] Process improvements documented in PROGRESS.md for `ai-dev-env:execute` skill
- [ ] New-document ingestion test — documented as manual-only (requires E2E harness)

---

## Recommendations for Future

**Plan Improvements:**
- Distinguish behavioral test scenarios by testability tier: unit-mockable / integration-skippable / manual-only. Label each scenario at planning time so executors know which approach to take.
- When a plan uses a placeholder user_id for DB operations, note explicitly: "FK constraints are NOT bypassed by admin client — use a real auth user UUID for any insert."

**Process Improvements:**
- The `ai-dev-env:execute` skill should require a coverage audit at the end of each task: enumerate every code path introduced, confirm which are tested, and surface untested paths before marking complete. (Full note in PROGRESS.md Process Improvements section.)

**CLAUDE.md Updates:**
- Add pattern: "Integration test fixtures that gate on env vars should use `pytest.skip()` inside the fixture body, not `pytest.mark.skipif` with a module-level variable — the latter evaluates at collection time before any fixture runs."

---

## Conclusion

**Overall Assessment:** The RAGAS evaluation pipeline is fully implemented and validated. The core pipeline (golden dataset, retrieval+generation runner, RAGAS scoring, LangSmith push) was built in the prior session. This session closed the behavioral test gap that was left open: 8 new test cases cover all unit-testable paths, and the two integration scenarios that require live infrastructure now run automatically via a self-contained fixture. The one remaining untested scenario (new-document ingestion) is correctly classified as manual-only and documented. The `run_rag_pipeline` signature change is backward-compatible and the default pipeline behavior is unchanged.

**Alignment Score:** 9/10 — all plan deliverables met; two minor divergences (FK constraint, `skipif` timing) were resolved cleanly with no feature compromises. The RAGAS API version mismatch (prior session) was handled well. Score deducted 1 point for the new-document test scenario remaining manual.

**Ready for Production:** Yes — eval module is additive, no production code paths modified. The postmortem docs are now ingested in Supabase under the test user and are available for an immediate `evaluate.py` run.
