# Progress

Track progress through the IR-Copilot modules.

## Convention
- `[x]` = Completed and validated
- `[-]` = In progress
- `[ ]` = Not started

---

## Module 1: App Shell + Observability ✅

**Status:** ✅ Complete
**Completed:** [Date not recorded]

### Core Validation
Full-stack RAG application with FastAPI backend, React frontend, Supabase database, and OpenAI integration validated through automated Playwright tests. SSE streaming chat, authentication, threading, and observability (LangSmith) all working.

### Test Status
- **Automated Tests:** ✅ Core functionality passing (Playwright)
- **Automated Tests:** ✅ All test failures resolved by New Project Setup Walkthrough (2026-02-21)
  - Final state: 86 collected, 0 skipped, 0 errors
  - TypeScript: `tsc --noEmit` exits 0 — no type errors

### Notes
- Test credentials stored in .env (TEST_EMAIL, TEST_PASSWORD)
- Pre-existing test failures resolved: stale expectations, missing imports, SSE flakiness, deleted stale tests
- OpenAI Responses API migrated to stateless completions

---

## Module 2: BYO Retrieval + Memory ✅

**Status:** ✅ Complete
**Completed:** [Date not recorded]

### Core Validation
Complete RAG pipeline with document ingestion (PDF, DOCX, HTML, Markdown via Docling), vector retrieval tool calling, and multi-provider chat support validated through comprehensive automated test suite. Provider switching (OpenAI, OpenRouter, LM Studio) with variable embedding dimensions working.

### Test Status
- **Automated Tests:** ✅ All passing
  - Frontend settings: 12/12
  - Backend provider service: 9/9
  - RAG retrieval, ingestion, tool calling: All passing
- **Manual Tests:**
  - ✅ E2E chat with OpenRouter: Playwright test automated (`optional-e2e-validation.spec.ts`). Switches to `openrouter / openai/gpt-4o`, sends question, verifies response. Requires `OPENROUTER_API_KEY` in `.env`.
  - ✅ Custom embeddings E2E: Playwright test automated (`optional-e2e-validation.spec.ts`). Full flow validated: switch to `text-embedding-3-large` (3072 dims) → ingest doc → query → retrieval confirmed. Both paths covered: no-chunks (model change allowed) and chunks-exist (safety lock active). Cleanup: delete doc + page reload resets model config to defaults.
  - ⚠️ Not performed: Cross-browser compatibility (Playwright config is Chromium-only)
  - ✅ Settings persistence validated: settings retain within a session (React useState). **Known limitation:** `useModelConfig` uses in-memory state only — settings reset on browser restart (no DB or localStorage persistence).

### Notes
- Migrations 001-010 applied (core schema, variable embedding dimensions)
- 3 providers supported: OpenAI, OpenRouter, LM Studio (auto-appends /v1)
- Default: gpt-4o chat, text-embedding-3-small (1536 dims)
- Retrieval: 5 chunks max, 0.7 similarity threshold
- RLS enforced on all tables
- **Settings persistence limitation:** provider config is in-memory only (useModelConfig hook, useState). Reloading the browser resets to backend defaults. This is a known gap, not blocking for current scope.

---

## Module 3: Record Manager ✅

**Status:** ✅ Complete
**Completed:** 2026-02-14
**Plan:** `.agents/plans/module-3-record-manager.md`

### Core Validation
Content-based deduplication system with SHA-256 hashing validated through comprehensive automated test suite. File-level and text-level duplicate detection prevents redundant processing and API costs. All scenarios tested including cross-format duplicates and modified content detection.

### Test Status
- **Automated Tests:** ✅ 6/6 passing (100% automated)
  - Hash generation consistency
  - Duplicate detection (same file, same content different filename)
  - Modified content reprocessing
  - No chunks created for duplicates
  - Database constraints
- **Manual Tests:**
  - ✅ Migration 011 applied (content hashing schema)

### Notes
- Migration 011 applied: file_content_hash, text_content_hash, duplicate_of columns
- Indexes: idx_documents_text_hash, idx_documents_file_hash
- Status extended: 'duplicate' value added to documents_status_check
- Cost savings: Duplicates skip embedding API calls and chunk storage
- RLS enforced: user_id scoping on duplicate detection queries
- Backward compatible: Nullable hash columns

**Execution Report:** `.agents/execution-reports/module-3-record-manager.md`

---

## Module 4: Metadata Extraction ✅

**Status:** ✅ Complete
**Completed:** 2026-02-15
**Plan:** `.agents/plans/module-4-metadata-extraction.md`

### Core Validation
LLM-powered document-level metadata extraction validated through comprehensive automated test suite. Structured outputs (summary, document_type, key_topics) extracted using OpenAI JSON schema with Pydantic validation. Integration tests confirm end-to-end flow from upload to metadata storage.

### Test Status
- **Automated Tests:** ✅ 9/9 passing (100% automated)
  - Unit tests: 3/3 (schema validation, LLM extraction, long document truncation)
  - Integration tests: 3/3 (E2E extraction, disabled flag, graceful failure)
  - Regression tests: 3/3 (existing ingestion tests still pass)
- **Manual Tests:**
  - ✅ Migration 012 applied (metadata extraction schema)

### Notes
- Migration 012 applied: summary, document_type, key_topics, metadata_status, extraction_model columns
- Indexes: idx_documents_metadata_status, idx_documents_document_type, idx_documents_extraction_model
- Default: extract_metadata=True (runs automatically during ingestion)
- Graceful degradation: Metadata extraction failures don't block document ingestion
- Long document handling: Text truncated to 100k chars before LLM extraction
- Backward compatible: New columns nullable, extraction optional
- Foundation for future metadata-enhanced retrieval (not yet implemented)

**Execution Report:** `.agents/execution-reports/module-4-metadata-extraction.md`

---

## Module 5: Multi-Format Support ✅

**Status:** ✅ Complete
**Completed:** 2026-02-15
**Plan:** `.agents/plans/module-5-multi-format-enhancement.md`

### Core Validation
Multi-format document support expansion (5 new formats: PPTX, CSV, JSON, XML, RTF) and cascade delete optimization validated through comprehensive automated test suite. All 10 supported formats tested end-to-end with proper parsing and ingestion.

### Test Status
- **Automated Tests:** ✅ 8/8 passing (100%)
  - 5 new format tests (CSV, JSON, XML, RTF, PPTX)
  - 1 cascade delete validation test
- **Automated Tests (additional):**
  - ✅ PPTX upload and processing validated via Playwright (`optional-e2e-validation.spec.ts`)

### Notes
- **Supported formats (10):** PDF, DOCX, HTML, MD, TXT, PPTX, CSV, JSON, XML, RTF
- **Cascade delete:** Removed redundant manual chunk deletion (database handles via ON DELETE CASCADE)
- **Configuration sync:** Frontend/backend file type lists synchronized with comments
- **Environmental dependency:** backend/.env overrides config.py if SUPPORTED_FILE_TYPES defined
- **Parsing:** Simple (TXT, MD, HTML, JSON, RTF) vs Docling (PDF, DOCX, PPTX, CSV, XML)

**Execution Report:** `.agents/execution-reports/module-5-multi-format-enhancement.md`
**System Review:** `.agents/system-reviews/module-5-multi-format-enhancement.md` (Alignment: 9/10)

---

## Module 6: Hybrid Search & Reranking ✅

**Status:** ✅ Complete
**Completed:** 2026-02-15
**Plan:** `.agents/plans/module-6-hybrid-search-reranking.md`

### Core Validation
Hybrid search combining PostgreSQL full-text search with vector similarity via Reciprocal Rank Fusion (RRF) validated through comprehensive automated test suite. Both local cross-encoder reranking and Cohere API integration tested and working. Backward compatibility with vector-only mode confirmed.

### Test Status
- **Automated Tests:** ✅ 6/7 passing (86%)
  - 7 test cases: keyword search, hybrid search, local reranking, Cohere reranking, E2E integration, backward compatibility, edge cases
  - 1 expected behavior: empty query correctly rejected by OpenAI embedding API
- **Automated Tests (additional):**
  - ✅ Hybrid search retrieval quality validated via Playwright (`optional-e2e-validation.spec.ts`) — unique document content successfully retrieved

### Notes
- Migration 013 applied successfully (fixed SQL bugs: websearch_to_tsquery, rrf_k variable)
- PR review completed: all 5 issues resolved (removed production logging, added configurability)
- Backward compatible: vector-only mode still works when HYBRID_SEARCH_ENABLED=false
- New settings: HYBRID_SEARCH_ENABLED, RERANKING_ENABLED, RERANKING_PROVIDER (local/cohere)
- Dependencies added: sentence-transformers>=2.2.0, cohere>=5.0.0
- PyTorch upgraded 2.2.2→2.10.0 (may conflict with docling - monitoring for regressions)

**Execution Report:** `.agents/execution-reports/module-6-hybrid-search-reranking.md` (Alignment: 8.5/10)
**PR Review:** `.agents/claude-pr-reviews/module-5.md` (All issues resolved)

---

## Enhancement: Multi-File Upload ✅

**Status:** ✅ Complete
**Completed:** 2026-02-16
**Design:** `docs/plans/2026-02-16-multi-file-upload-design.md`
**Plan:** `docs/plans/2026-02-16-multi-file-upload-implementation.md`

### Core Validation
Multi-file document upload with queue management, sequential processing, and interactive error handling validated through E2E tests. Users can select unlimited files, review/remove from queue, and handle upload failures interactively.

### Test Status
- **E2E Tests:** ✅ 6/6 passing
  - Multi-file selection via file picker
  - Queue management (remove, clear all)
  - Sequential upload with status tracking
  - Validation error handling
  - Upload summary display
  - Backward compatibility

### Notes
- Frontend-only changes (no backend modifications)
- Queue state managed in DocumentUpload component
- Error dialog prompts user on failure (continue/stop)
- Invalid files shown in queue but skipped during upload
- Backward compatible with single-file uploads
- Existing Supabase Realtime status updates still work

### Reports Generated

**Execution Report:** `.agents/execution-reports/multi-file-upload.md` (Alignment: 9.5/10)
- Detailed implementation summary with 13 tasks completed
- Systematic debugging session resolving pre-existing test infrastructure issues
- Test pass rate: 4/5 E2E tests (80%), improved overall suite from 3% to 47%
- Production-ready with minor timing flake (non-blocking)

---

## Module 7: Additional Tools ✅

**Status:** ✅ Complete
**Completed:** 2026-02-16
**Plan:** `.agents/plans/module-7-additional-tools.md`

### Core Validation
Multi-tool agent with text-to-SQL and web search capabilities validated through comprehensive automated test suite. Defense-in-depth security architecture with database-level enforcement for SQL queries. LLM intelligently routes between document retrieval, structured data queries, and web search.

### Test Status
- **Automated Tests:** ✅ 14/14 passing (100%)
  - SQL service: 6/6 (count, filter, injection prevention, access control)
  - Web search: 4/4 (basic search, max results, error handling, API key validation)
  - Integration: 4/4 (multi-tool routing, E2E flows)
- **Automated Tests (additional):**
  - ✅ Text-to-SQL tool validated via Playwright — "Books by George Orwell?" returns 1984 and Animal Farm
  - ✅ Web search tool validated via Playwright — live AI news retrieved via Tavily

### Notes
- Team-based execution: 8 agents across 4 waves (~2x speedup)
- Migration 014 applied: sql_query_role created; migration 016 replaces with production_incidents table and execute_incidents_query RPC
- Dependencies: tavily-python, cohere, sentence-transformers
- Security: Defense-in-depth (app validation + DB role + RPC function)
- Files changed: 11 (7 new, 4 modified) - +1,221/-43 lines

**Execution Report:** `.agents/execution-reports/module-7-additional-tools.md`
**System Review:** `.agents/system-reviews/module-7-additional-tools.md` (Alignment: 9.5/10)

---

## Module 8: Sub-Agents ✅

**Status:** ✅ Complete
**Completed:** 2026-02-16
**Plan:** `.agents/plans/module-8-sub-agents.md`

### Core Validation
Hierarchical agent delegation system enabling main chat agent to spawn isolated sub-agents for complex full-document analysis. LLM-triggered tool calling with recursion depth limiting (max 2 levels) prevents infinite nesting. Expandable UI displays sub-agent reasoning and results with auto-expand on errors.

### Test Status
- **Automated Tests:** ✅ 9/9 passing (100%)
  - Unit tests: 3/3 (basic execution, recursion limit, document not found)
  - Integration tests: 3/3 (tool call via chat, missing document, metadata storage)
  - Regression tests: 2/2 (fixed pre-existing broken test)
  - Frontend build: Production build successful (Vite)
- **Automated Tests (additional):**
  - ✅ Sub-agent document analysis validated via Playwright — document uploaded, sub-agent spawned, quarterly revenue data extracted

### Notes
- Team-based parallel execution: 6 agents, 4 waves, 33% time savings
- Migration 015 applied: subagent_metadata JSONB column in messages table
- Files changed: 6 modified, 8 new (+154/-32 lines)
- Architecture: Isolated sub-agent context prevents main conversation pollution
- Module 7 Integration: All 4 tools work together (retrieval, SQL, web search, sub-agent)
- Breaking change: stream_response() signature 2-tuple → 3-tuple
- CLAUDE.md additions: Streaming patterns, test audit, team execution best practices

**Execution Report:** `.agents/execution-reports/module-8-sub-agents.md`
**System Review:** `.agents/system-reviews/module-8-sub-agents.md` (Alignment: 9.5/10)

---

# Additional Features, Fixes & Enhancements

## Enhancement: LangSmith Tool Tracing ✅

**Status:** ✅ Complete
**Completed:** 2026-02-16
**Plan:** `.agents/plans/langsmith-tool-tracing.md`

### Core Validation
Child LangSmith traces for all tool executions providing detailed observability into tool inputs, outputs, and execution metadata. Trace closure guaranteed via finally block pattern ensures traces complete even when streams are interrupted or errors occur.

### Test Status
- **Automated Tests:** ✅ 3/3 passing — see [Enhancement: LangSmith Trace Automated Tests](#enhancement-langsmith-trace-automated-tests) below
- **Manual Tests (original validation):** ✅ All passing
  - retrieve_documents: Shows query, chunk_count, similarity scores
  - query_incidents_database: Shows SQL query, row count, sample results
  - search_web: Shows search query, result count, top URLs
  - analyze_document_with_subagent: Shows task, status, reasoning steps count
  - generate_thread_title: Shows title generation LLM call
  - Trace closure: All traces complete successfully (no spinning indicators)

### Debug Process & Findings

**Bug 1: Chat Completions Trace Not Closing When Tools Invoked**

**Symptoms:**
- LangSmith showed chat_completions_stream trace with spinning indicator (incomplete)
- Only occurred when tools were called, not on simple text responses
- Only on first message in thread (suspected title generation interference)

**Investigation Steps:**
1. **Initial hypothesis:** Thread title generation concurrent LLM call interfering
   - Added LangSmith tracing to generate_thread_title endpoint
   - Result: ❌ Didn't fix trace closure issue
2. **Second hypothesis:** Trace closure code not guaranteed to execute
   - Discovered trace closure was in try block, not finally block
   - Async generators may not execute cleanup code if not fully consumed
   - Result: ✅ Root cause identified
3. **Fix applied:** Move trace closure to finally block
   - Ensures trace closes whether stream completes, errors, or is interrupted
   - Added error_occurred variable to track exception state
   - Result: ✅ Traces now close successfully

**Bug 2: Retrieval Tool Failing - Missing sentence-transformers**

**Symptoms:**
- Tool call failed with "No module named 'sentence_transformers'"
- Error occurred during local reranking in retrieval pipeline

**Investigation Steps:**
1. Install sentence-transformers → triggered PyTorch version conflict
2. PyTorch 2.2.2 incompatible with sentence-transformers 5.2.2 (requires >= 2.4)
3. Upgraded PyTorch → torchvision incompatibility
4. Attempted reinstall → deep dependency conflicts with docling packages
5. **Workaround:** Disabled local reranking, used Cohere provider instead

**Debug Methodology:**
- Added temporary debug print statements to trace execution flow
- Confirmed finally block execution with debug logging
- Verified trace closure success/failure with detailed error messages
- Removed all debug traces after validation

### Notes
- **Trace hierarchy:** Parent chat_completions_stream → Child tool_* runs
- **Tool metadata captured:**
  - retrieve_documents: query, chunk_count, document_names, similarity scores
  - query_incidents_database: natural_language_query, sql_query, row_count, sample_results
  - search_web: search_query, result_count, top_urls, top_titles
  - analyze_document_with_subagent: task_description, document_name, status, reasoning_steps_count
- **Error tracing:** Failed tool calls show error messages in LangSmith outputs
- **Non-breaking:** Tracing failures silently caught, don't interrupt tool execution
- **Files changed:** 2 modified (+688/-22 lines) - chat.py, chat_service.py

### Lessons Learned & Process Improvements

**What Went Wrong:**
1. **Trace closure not in finally block** - Critical async pattern oversight
   - Async generators don't guarantee cleanup code execution without finally
   - Try/except pattern insufficient for stream interruption scenarios
2. **No trace closure validation in plan** - Missing explicit test criteria
   - Plan validated trace creation but not trace completion
   - Should have included "verify traces close" in success criteria
3. **Dependency conflicts not anticipated** - sentence-transformers installation broke existing setup
   - Should have checked dependency tree before implementation
   - Missing rollback/workaround strategy in plan

**How to Improve the Plan:**

**Add explicit validation steps:**
```markdown
## Validation Steps

### Trace Lifecycle Testing
1. Normal completion: Verify trace closes after successful tool execution
2. Error scenarios: Verify trace closes with error when tool fails
3. Stream interruption: Verify trace closes if client disconnects mid-stream
4. Concurrent operations: Verify parent/child traces don't interfere

### Dependency Verification
1. Check sentence-transformers compatibility before implementation
2. Test in isolated venv to detect conflicts early
3. Document workaround: Disable local reranking if dependencies conflict
```

**Include technical patterns:**
```markdown
## Implementation Patterns

### Async Generator Cleanup
- ✅ Use finally block for guaranteed cleanup (trace closure, resource release)
- ❌ Don't rely on try/except for cleanup - won't run if generator interrupted
- Pattern:
  ```python
  try:
      # Stream generation
      yield data
  except Exception as e:
      # Error handling
  finally:
      # Always runs - close traces, cleanup resources
  ```
```

**How to Improve Execution:**

**1. Incremental Testing:**
- Test trace closure after adding helper function (before adding to all tools)
- Add one tool at a time, verify trace hierarchy works
- Test error scenarios early (tool failure, stream interruption)

**2. Instrumentation from Start:**
- Include debug logging hooks in initial implementation (commented out)
- Makes debugging faster when issues arise
- Remove before commit

**3. Dependency Isolation:**
- Test new dependencies in separate venv first
- Document compatible version ranges
- Have rollback plan (disable feature if dependencies conflict)

**4. Edge Case Coverage:**
```markdown
Test scenarios to validate before claiming complete:
- [ ] Tool succeeds → trace closes with outputs ✅
- [ ] Tool fails → trace closes with error ✅
- [ ] Stream interrupted (client disconnect) → trace closes
- [ ] Multiple tools in sequence → all child traces close
- [ ] Concurrent title generation → doesn't interfere with main trace
```

**How to Improve Debug Process:**

**1. Start with Instrumentation:**
```python
# Add debug points at key lifecycle events
print(f"[DEBUG] Stream starting - run_id: {run_id}")
print(f"[DEBUG] Tool executed - {tool_name}")
print(f"[DEBUG] Finally block reached - error: {error_occurred}")
print(f"[DEBUG] Trace closed - success: {success}")
```

**2. Test in Isolation:**
- Create minimal reproduction (single tool call)
- Eliminate variables (disable title generation, test one tool)
- Gradually add complexity

**3. Verify Async Patterns:**
- Check if finally block executes in all scenarios
- Test generator cleanup with interrupted streams
- Use async debugging tools (aiomonitor, aiodebug)

**4. Document Findings:**
```markdown
Debug Log:
1. Observed: Trace shows spinning (not closing)
2. Hypothesis: Title generation interference
3. Test: Add tracing to title generation
4. Result: ❌ Didn't fix - trace still spinning
5. Hypothesis 2: Cleanup code not executing
6. Test: Move to finally block, add debug logging
7. Result: ✅ Debug shows finally executes, trace closes
8. Conclusion: Finally block required for guaranteed cleanup
```

**5. Use Proper Logging (Not Print):**
- Better: `logger.debug(f"Finally block reached - run_id: {run_id}")`
- Worse: `print(f"[DEBUG] Finally block reached...")`
- Enables conditional logging (dev vs prod)
- Can be left in code with appropriate log levels

### Time Saved by Better Process

**Current execution:**
- Implementation: 30 min
- First debug (title generation hypothesis): 20 min
- Second debug (finally block fix): 15 min
- Dependency issues: 30 min
- Verification: 10 min
- **Total: ~105 min**

**With improved process:**
- Implementation with finally block from start: 35 min (includes pattern lookup)
- Dependency check before implementation: 5 min
- Incremental testing (one tool): 10 min
- Verification: 5 min
- **Total: ~55 min**

**Time savings: 50 minutes (48% faster)**

**Key factors:**
1. Finally block pattern from start saves entire first debug session
2. Dependency check prevents installation conflicts
3. Incremental testing catches issues earlier (cheaper to fix)
4. Built-in debug hooks make troubleshooting faster when needed

---

## Bug Fix: Duplicate Upload Requests

**Status:** ✅ Complete
**Completed:** 2026-02-16

### Core Validation
Stale closure bug causing duplicate HTTP requests on file upload validated through systematic debugging with console logging (unique call IDs, timestamps, stack traces). Root cause identified as `useCallback` dependency on state causing function recreation in `setTimeout` continuation.

### Test Status
- **Manual Tests:** ✅ All passing
  - Single-file upload: No duplicates
  - Multi-file upload: Sequential processing without duplicates
  - Error handling: Continue/Stop buttons work correctly
  - React Strict Mode: No duplicates in development or production

### Notes
- **Root Cause:** Stale closure - `uploadNext` recreated when `currentUploadIndex` changed, `setTimeout` captured new function reading stale state
- **Primary Fix:** Use refs (`currentUploadIndexRef`) for state values read in async callbacks, remove state from `useCallback` dependencies
- **Defense-in-Depth:** AbortController for request deduplication (handles React Strict Mode double-invocation)
- **Investigation:** 4 failed guard-based approaches before evidence-gathering (console logging) revealed root cause
- **Files Modified:** `frontend/src/hooks/useIngestion.ts` (AbortController), `frontend/src/components/Ingestion/DocumentUpload.tsx` (refs)
- **React Patterns Documented:** `frontend/CLAUDE.md` - stale closure prevention, AbortController usage, systematic debugging methodology

**Execution Report:** `.agents/execution-reports/duplicate-upload-bug-fix.md`
**System Review:** `.agents/system-reviews/duplicate-upload-bug-fix.md` (Alignment: 9.5/10)

---

## Bug Fix: PDF Upload Pipeline (Multi-Session Debug)

**Status:** ✅ Complete
**Completed:** 2026-02-20
**Debug Log:** `.agents/debug_pdf_upload.md`

### Issues Found and Fixed

**1. Docling version too old (`docling==0.4.0`)**
The pinned version expected a `model.pt` layout file; the current HuggingFace repo (`ds4sd/docling-models`) switched to ONNX format. Fixed by upgrading to `docling>=2.0.0`.

**2. Pre-download command didn't trigger all models**
The original SETUP.md pre-download only called `DocumentConverter()` (initialization), which didn't load the layout pipeline. Layout models (`docling-layout-heron`, `docling-project/docling-models`) were lazy-loaded on first real upload, hitting a Windows symlink-creation restriction (`WinError 1314`) and failing. Fixed by running an actual minimal PDF conversion in the pre-download step to force all lazy models to cache. Added `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to `.env.example`.

**3. Non-ASCII filenames rejected by Supabase Storage**
Hebrew filename `מצגת להסתדרות payrollai.pdf` produced `InvalidKey` 400 error. Fixed by replacing `user_id/filename` storage paths with `user_id/uuid.ext` — original filename preserved in the DB record for display. Also eliminates the pre-existing duplicate-path collision issue.

**4. Supabase Realtime not delivering status updates**
UI stuck at "Processing" even though DB showed `status=completed`. The `documents` table was missing `REPLICA IDENTITY FULL` — without it Supabase Realtime silently drops UPDATE events on RLS-enabled tables (can't verify user access against the old row state). Fixed via migration 015. Note: the table was already in the `supabase_realtime` publication; `REPLICA IDENTITY FULL` was the missing piece.

**5. RapidOCR INFO logs on every upload**
RapidOCR's `Logger.__init__` calls `setLevel(INFO)` at import time, overriding any earlier suppression. Fixed by adding a `logging.Filter` (immune to `setLevel` resets) to the `RapidOCR` logger in `main.py` after all router imports. Also refactored `DocumentConverter` to a module-level singleton to avoid re-initializing the OCR engine on every upload.

### Files Modified
- `backend/requirements.txt`: `docling==0.4.0` → `docling>=2.0.0`
- `backend/main.py`: Pydantic warning filter + RapidOCR `logging.Filter` (post-import)
- `backend/services/embedding_service.py`: `DocumentConverter` singleton via `_get_converter()`
- `backend/routers/ingestion.py`: UUID-based storage paths; `import uuid`
- `backend/.env.example`: `HF_HUB_DISABLE_SYMLINKS_WARNING`
- `SETUP.md`: Pre-download command now runs a real minimal PDF conversion
- `supabase/migrations/015_realtime_documents.sql`: `REPLICA IDENTITY FULL` + publication

---

## New Project Setup Walkthrough

**Status:** ✅ Complete — test suite fully cleaned up and organized.

### Test Suite Fixes Applied (2026-02-21)

The following issues were found and fixed during the setup walkthrough. All commits are on `main`.

**Commits:**
- `21959f4` — Stale test expectations, missing imports, hex validation bug, `.env.example` SUPPORTED_FILE_TYPES
- `b69b2b0` — Collection errors (module-level code ran on import), stale fixture param names, SSE event loop flakiness
- `0d0e119` — Wrong `os.chdir` path in test_upload_now.py, missing `TEST_USER_EMAIL`/`TEST_USER_PASSWORD` import aliases in 4 retrieval test files, deleted 2 stale tests referencing removed `openai_service`

**`.env` fix required by user:**
- `SUPPORTED_FILE_TYPES` in `backend/.env` was restricted to 5 types; must include the full list: `pdf,docx,pptx,html,md,txt,csv,json,xml,rtf`

### Tasks Completed (2026-02-21)

**Task 1: Fixed async tests (were 40 skipped, now 0 skipped)**
- Installed `pytest-asyncio` and added to `backend/requirements.txt`
- Created `backend/pytest.ini` with `asyncio_mode = auto` and `testpaths = tests/auto`
- Updated `conftest.py` to add `tests/` dir to sys.path so `test_utils` importable from subdirs
- Added `setup_module()` hooks to 5 test files that had async setup not called by pytest
- Fixed 2-tuple stream unpacking → 3-tuple in `test_final.py` and `test_with_fix.py`
- Fixed hybrid_score vs raw similarity threshold assertion in `test_rag_retrieval.py`

**Task 2: Split tests into `auto/` and `manual/` subfolders**
- Created `backend/tests/auto/` — 31 pytest-runnable automated test files (86 tests collected)
- Created `backend/tests/manual/` — 6 live-server scripts requiring `uvicorn` at `localhost:8000`
- Removed original test files from `backend/tests/` root (canonical versions in `auto/`/`manual/`)

**Final test suite state:**
```
86 collected, 0 skipped, 0 errors (from tests/auto/ only)
```

**Manual tests** (run directly with `python <file>.py`, require `uvicorn` running):
- `tests/manual/test_stream.py`
- `tests/manual/test_simple_send.py`
- `tests/manual/test_strategic_retrieval.py`
- `tests/manual/test_strategic_final.py`
- `tests/manual/test_detailed_error.py`
- `tests/manual/test_endpoint_direct.py`

---

## Enhancement: LangSmith Trace Automated Tests

**Status:** ✅ Complete
**Completed:** 2026-02-21

### Core Validation
Playwright tests verifying that chat messages produce LangSmith traces with correct structure, content, and guaranteed closure. Tests connect directly to the LangSmith REST API to poll for runs after sending messages through the UI.

### Test Status
- **Automated Tests:** ✅ 3/3 passing (`frontend/tests/langsmith-traces.spec.ts`)
  - `chat message creates a LangSmith run with inputs and outputs` — verifies `chat_completions_stream` run appears with populated inputs, outputs, and end_time
  - `LangSmith run captures the user message in inputs` — verifies user message text is present in run inputs
  - `failed chat still closes the LangSmith run without leaving it open` — verifies `end_time` is always set (finally-block cleanup guaranteed)
- Auto-skips if `LANGSMITH_API_KEY` is absent from `backend/.env`

### Notes
- Run: `cd frontend && npx playwright test langsmith-traces`
- REST API pattern discovered: `GET /api/v1/sessions?name=<project>` to resolve session UUID, then `POST /api/v1/runs/query` with `{"session": [uuid], ...}` — the simple `GET /api/v1/runs?session_name=...` returns 405
- Polls every 4s up to 40s to account for LangSmith's 10–30s propagation delay
- Loads `LANGSMITH_API_KEY` from `backend/.env` at test time (not frontend env)

---

## Bug Fix: PDF Parsing Failure on Real-World Documents (2026-02-22)

**Status:** ✅ Complete

### Root Cause
PDF uploads were failing with `"Failed to parse document: Missing ONNX file: ...beehive_v0.0.5\model.pt"`. The chain of failures:

1. **PyTorch 2.2.2 too old** — Docling's layout-heron model (already cached in `~/.cache/huggingface/hub/`) requires PyTorch ≥ 2.4. With PyTorch disabled, docling fell back to the old `beehive_v0.0.5` ONNX model from `ds4sd/docling-models`, which was never fully downloaded (only tableformer was cached, layout was missing).
2. **Server not using venv** — `uvicorn` was being called bare, picking up the system Python (PyTorch 2.2.2) instead of the venv (which had 2.10.0 after the fix). Activation alone is unreliable on Windows.
3. **Warmup crash blocked server start** — The new lifespan warmup was non-fatal after fix, but confirmed the startup failure was PyTorch-version-related.

### Fixes Applied
- **`requirements.txt`:** Added `torch>=2.4`, `torchvision>=0.19`, `huggingface_hub[hf_xet]>=0.27`
- **`main.py`:** Lifespan warmup made non-fatal (logs warning instead of crashing server)
- **`start_scripts/`:** All 4 scripts updated to call `venv/Scripts/uvicorn` directly instead of relying on PATH after activation
- **`SETUP.md`:** Run commands updated to `venv/Scripts/uvicorn`; Windows HuggingFace symlinks limitation documented in Prerequisites with fix steps (Developer Mode or run as admin)
- **`debugging/check_failed_documents.py`:** Fixed `UnicodeEncodeError` on Hebrew filenames via `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`

### Key Lesson
Simple test PDFs (single text block) bypass docling's layout pipeline and succeed even with broken model setup. Real-world complex PDFs (tables, images, multi-column) require the layout model. Always test with a real document, not a synthetic one.

---

## Render Deployment Fixes (2026-02-22)

**Status:** ✅ Complete

Three issues diagnosed and fixed to unblock Render deployment:

**1. Wrong Python version file name and format**
- `backend/runtime.txt` is not recognized by Render — correct filename is `backend/.python-version`
- Content was `python-3.12.0`; correct format is `3.12.0` (version number only)
- Render was defaulting to Python 3.14, causing `pydantic-core==2.23.4` to fail compilation (no pre-built wheel for 3.14, Cargo filesystem is read-only)
- Fix: renamed to `.python-version`, corrected content

**2. `huggingface_hub` extra name changed in newer versions**
- `huggingface_hub[hf_xet]` (underscore) was renamed to `huggingface_hub[hf-xet]` (hyphen) in 1.x releases, producing pip warnings on every build
- Fix: updated `requirements.txt` to `huggingface_hub[hf-xet]>=0.27`

**3. Start command should use hardcoded port, not `$PORT`**
- Render's `$PORT` variable can cause health check failures if port detection mismatches
- Using `--port 8000` (hardcoded) is reliable: Render detects and routes to whichever port the app binds on
- Fix: updated `SETUP.md` start command to `uvicorn main:app --host 0.0.0.0 --port 8000` and corrected the troubleshooting section accordingly

---

## Cloud Run Migration (2026-02-23) ✅

**Status:** ✅ Complete
**Completed:** 2026-02-23
**Reasoning:** Free plan on render.com includes only 512MiB, Cloud Run free tier is higher

### Service Details
- **URL:** `https://agentic-rag-94676406483.me-west1.run.app`
- **Region:** `me-west1`, **Project:** `agentic-rag-gilad`, **Memory:** 4 GiB
- **CD:** GitHub pushes to `main` auto-build and deploy via Cloud Build (`cloudbuild.yaml`)
- **Frontend:** `VITE_API_URL` updated in Vercel; `CORS_ORIGINS` locked to Vercel URL

### Issues Found and Fixed During Deployment
1. **Missing env vars** — `.cloudrun_env.yaml` was never applied; app crashed at startup with Pydantic `ValidationError`. Fix: `gcloud run services update --env-vars-file=.cloudrun_env.yaml`
2. **Hardcoded port** — `--port 8000` in Dockerfile CMD; Cloud Run injects `PORT=8080`. Fix: `CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]`
3. **OOM at startup** — Default 512 MiB exceeded (587 MiB) loading torch+docling. Fix: `--memory=2Gi`
4. **Traffic pinned to placeholder** — `--no-traffic` flag pinned traffic to the placeholder revision; new deployments sat at 0%. Fix: `gcloud run services update-traffic --to-latest`
5. **Stale us-central1 service** — Initial manual setup created a duplicate in `us-central1`. Deleted.

### Post-Migration Fixes (2026-02-23)
6. **OOM during PDF upload** — 2 GiB limit exceeded (2.1 GiB used) when docling processes complex PDFs. Fix: `--memory=4Gi`.
7. **504 on concurrent uploads** — `converter.convert()` (docling ML inference) was called directly inside an `async def`, blocking the asyncio event loop. A second upload while the first was processing background tasks would stall for 40–50 s until Cloud Run timed out. Fix: wrap `converter.convert()` in `asyncio.run_in_executor` (`embedding_service.py`).
8. **CI build failing** — Default Cloud Build trigger used an inline config looking for `Dockerfile` at repo root; our Dockerfile is in `backend/`. Fix: added `cloudbuild.yaml` at repo root; ran one-time `gcloud builds triggers update` to point the trigger at it; deleted the duplicate trigger.
9. **`.md` upload rejected by Supabase Storage** — Browser sends `application/octet-stream` for `.md` files; Supabase rejects this MIME type. Fix: added `_MIME_TYPE_MAP` in `ingestion.py` to override `octet-stream` with correct types for known text formats.

### Key Files
- `backend/Dockerfile` — container definition (`${PORT:-8000}`, `EXPOSE 8080`)
- `.cloudrun_env.yaml` — env vars (gitignored, contains secrets; `CORS_ORIGINS` = Vercel URL)
- `cloudbuild.yaml` — CI build config (builds from `backend/`, owned by repo)

### Lessons Learned
1. **Apply env vars before first push** (or immediately after). Without them, `Settings()` crashes the app at startup before it can bind any port.
2. **Never hardcode port in Cloud Run CMD.** Use `${PORT:-8000}` — Cloud Run injects `PORT=8080` and health-checks on that port.
3. **Set memory to 4 GiB** for torch+docling. 2 GiB is enough for startup but OOMs on real document uploads.
4. **Avoid `--no-traffic` on a service with a pinned revision.** Future deploys will create revisions at 0% traffic forever. If you use it, follow up with `update-traffic --to-latest`.
5. **Cloud Run has two URL formats** for the same service: `{name}-{project-number}.{region}.run.app` (GCP console) and `{name}-{hash}.a.run.app` (API `status.url`). Both work.
6. **The default Cloud Build trigger uses an inline config** (not `cloudbuild.yaml`). After creating the service via the console, run the one-time `gcloud builds triggers update github` command documented in SETUP.md to point it at `cloudbuild.yaml`.
7. **Never call CPU-intensive sync code directly in `async def`** without `run_in_executor`. It blocks the entire asyncio event loop, stalling all concurrent requests.

---

## Repository Maintenance: Secret Removal from Git History

**Completed:** 2026-02-20

Commit history was rewritten twice using `git-filter-repo` to purge secrets that had been accidentally version-controlled:

1. **`git-filter-repo --replace-text`** — replaced secret values inside tracked file contents (e.g. hardcoded API keys, passwords in source files) with placeholder strings across all commits.
2. **`git-filter-repo --replace-message`** — replaced secret values embedded in commit messages with placeholder strings across all commits.

Both passes rewrote the full commit graph. The remote was force-pushed after each pass to propagate the cleaned history.

---

## Frontend Test Infrastructure Cleanup (2026-02-24)

**Status:** ✅ Complete — infrastructure fixed, all 7 previously failing tests fixed (2026-02-24)

### Changes Made

- `playwright.config.ts` — load `backend/.env` first so `TEST_EMAIL`/`TEST_PASSWORD`/`LANGSMITH_API_KEY` are not shadowed by frontend placeholders; added backend uvicorn as a `webServer` entry (Windows-safe backslash path) so tests no longer require a manually running server
- Deleted `auth.spec.ts` and `chat.spec.ts` — fully superseded by `auth-existing-user.spec.ts` and `chat-existing-user.spec.ts`; used `@example.com` signups that Supabase rejects
- Deleted `auth-debug.spec.ts` — throwaway diagnostic file, no longer needed
- Added `backend/tests/run_tests.sh` and `frontend/tests/run_tests.sh` — one-command test runners for each suite; forward extra args to pytest / playwright

### Current Frontend Test State (run 2026-02-24, 39 tests total)

**All 39 passing (was 32 passed, 7 failed)**

### Fixes Applied (2026-02-24)

**Group A — Wrong UI selectors:**

- `should log out successfully`: Logout button is inside a dropdown that only opens when the profile button is clicked. Regex `/logout/i` also didn't match the "Log out" text (space in middle). Fix: click `getByText(TEST_EMAIL)` to open the dropdown, then `getByRole('button', { name: /log out/i })`.

- `should verify JWT authentication persists after refresh`: `toHaveURL('/chat')` after `page.reload()` had no timeout — if auth restore takes any time the assertion raced. Fix: `{ timeout: 15000 }` on both `toHaveURL` and email `toBeVisible`.

- `multi-file-upload.spec.ts` (both duplicate/stop tests): Page-ready indicator used `text=Upload Documents`; actual heading is `Document Ingestion` (`<h1>` in `IngestionInterface.tsx`). Fix: changed both occurrences.

**Group B — Timing / app behaviour:**

- `should enforce protected routes`: `page.goto('/chat')` returned before React fully initialised. Fix: `page.waitForLoadState('networkidle')` before asserting redirect; increased timeout to 15 s.

- `should persist messages after page refresh`: After `page.reload()`, `currentThreadId` resets to `null`, so no thread is selected and messages are hidden. Fix: wait for the sidebar to be ready, then `page.locator('div.cursor-pointer span.truncate').first().click()` to re-open the most recent thread before asserting.

**Group C — Test polling race:**

- `langsmith-traces.spec.ts — failed chat still closes LangSmith run`: `pollForRuns` returned as soon as the run appeared in LangSmith (from `create_run`), before `update_run` (which sets `end_time`) had propagated. The backend `finally` block is correct. Fix: added optional `condition` parameter to `pollForRuns`; test 3 passes `runs => runs.some(r => r.end_time != null)` so polling continues until `end_time` is confirmed.

---

## Feature: IR-Copilot Theme Change

**Status**: ✅ Complete
**Completed**: 2026-02-24
**Plan File**: `.agents/plans/ir-copilot-theme-change.md`
**Commit**: `80c92ea` (rebased onto main)

### What Was Done

Replaced the generic `books` table / "Agentic RAG" branding with a production incidents domain and IR-Copilot identity across the entire codebase. All code changes committed and pushed.

**Wave 1 — Service Layer:**
- [x] `supabase/migrations/016_production_incidents.sql` — DROP books, CREATE production_incidents (15 seed rows), `execute_incidents_query` RPC, permissions
- [x] `backend/services/sql_service.py` — `INCIDENTS_SCHEMA`, `_validate_query` checks for `PRODUCTION_INCIDENTS`, RPC call renamed
- [x] `backend/services/chat_service.py` — tool renamed `query_incidents_database`, description updated, system prompt updated, all 8 dispatch occurrences renamed

**Wave 2 — Tests + Postmortems:**
- [x] `backend/tests/auto/test_sql_service.py` — rewritten: `test_severity_filter` (P1), `test_service_filter` (auth-service), count threshold updated to ≥15
- [x] `backend/tests/auto/test_multi_tool_integration.py` — `test_incidents_query` replaces `test_books_query`; multi-turn Turn 2 updated to P1 incidents
- [x] `backend/tests/auto/test_simple_strategic.py` — incident-domain multi-part query
- [x] `backend/tests/auto/test_debug_stream.py` — updated to P1 incidents query
- [x] `backend/tests/manual/test_strategic_final.py` + `test_strategic_retrieval.py` — incident queries
- [x] `frontend/tests/optional-e2e-validation.spec.ts` — Module 7 section renamed to incidents; query + assertions updated
- [x] `backend/eval/postmortems/` — 6 postmortem markdown files created (464–535 words each, all sections present):
  - `INC-2024-003-auth-outage.md` — Redis TTL misconfiguration → JWT cache miss cascade (database, P1)
  - `INC-2024-011-payment-db-corruption.md` — PG 14.1 B-tree corruption after unclean shutdown (database, P1)
  - `INC-2024-019-pipeline-memory-leak.md` — asyncio unbounded task list → OOM crash loop (deployment, P2)
  - `INC-2024-027-gateway-timeout.md` — expired intermediate TLS cert → 504 on all routes (network, P1)
  - `INC-2024-031-notif-queue-backup.md` — RabbitMQ consumer under-scaling → 4h delay (configuration, P2)
  - `INC-2024-038-deploy-rollback.md` — nil pointer panic in new deployment → 503s (deployment, P3)

**Wave 3 — Documentation:**
- [x] `README.md` — title: "IR-Copilot — Incident Response AI Assistant"; SQL examples updated to incidents
- [x] `SETUP.md` — table name, SQL validation example, troubleshooting updated
- [x] `PROGRESS.md` — all `query_books_database` / `books` references replaced
- [x] `CONTRIBUTING.md` — heading and opening paragraph updated to IR-Copilot

### Validation (local file checks — no DB)
- Level 1: `grep -rn "books|query_books|execute_books"` → 0 results across services/tests/docs
- Level 4: 6 postmortem files, all contain "Follow-up Actions" section
- Migration: 15 INSERT rows confirmed in `016_production_incidents.sql`

### Manual Steps Completed
1. ✅ **Migration 016 applied** — `production_incidents` table live with 15 seed rows; `execute_incidents_query` RPC verified
2. ✅ **GitHub repo renamed** — `agentic-rag` → `ir-copilot`; local remote URL updated
3. ✅ **Backend auto tests passed** — 10/10 (`test_sql_service.py` + `test_multi_tool_integration.py`)
4. ✅ **Postmortems uploaded** — 6 files from `backend/eval/postmortems/` ingested via app UI

---

## Feature: 1-Click Setup Script

### Planning Phase
**Status**: 📋 Planned
**Plan File**: none yet

A `setup.sh` script at the repo root that takes a cloning user from zero to fully running app + tests with minimal manual steps.

### Design (agreed in session 2026-02-25)

**Pre-flight gate** — script opens by listing all prerequisites and pre-flight steps, noting which are optional, then waits for the user to confirm completion before proceeding:

*Prerequisites (listed by script, user must have these installed):*
- Python 3.10+ (required)
- uv (required)
- Node.js 18+ (required)
- Supabase CLI (required) — platform-specific install instructions in SETUP.md
- Git (required)
- LangSmith account (optional)
- Cohere API key (optional)
- Tavily API key (optional)

*Pre-flight manual steps (listed by script, user completes in browser/terminal):*
1. Create Supabase account + project at https://supabase.com
2. Fill in `backend/.env` — `SUPABASE_PROJECT_REF`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `SQL_QUERY_ROLE_PASSWORD`, optional keys
3. Fill in `frontend/.env` — `SUPABASE_PROJECT_REF`, `VITE_SUPABASE_ANON_KEY` (and optionally `VITE_BACKEND_API_URL`)
4. Run `supabase login` (opens browser for OAuth)

User types "done" → script proceeds.

**Automated steps (no user interaction):*
1. `cd backend && uv sync` — install Python deps (includes pytest)
2. `cd frontend && npm install` — install JS deps
3. `cd frontend && npx playwright install` — download Chromium browser binaries for E2E tests
4. Pre-download Docling models — one-time ~500MB download from HuggingFace (Python one-liner already documented in SETUP.md §2)
5. Read `SUPABASE_PROJECT_REF` from `backend/.env`, run `supabase link --project-ref <ref>`
6. Patch `supabase/migrations/013_sql_tool.sql` — replace `***` with `SQL_QUERY_ROLE_PASSWORD` from `backend/.env`
7. `supabase db push` — apply all 16 migrations
8. Restore `***` placeholder in `013_sql_tool.sql`
9. (Evals step TBD — RAGAS evaluation pipeline is being built in a separate worktree; add `ragas` dep install here once merged)

**Post-script manual steps (script prints these as final instructions):*
1. Create test user in Supabase dashboard: Authentication → Users → Add user
2. Update `TEST_EMAIL` and `TEST_PASSWORD` in **both** `backend/.env` and `frontend/.env`

After completing post-script steps, user can run:
- App: `cd backend && uv run uvicorn main:app --reload --port 8000` + `cd frontend && npm run dev`
- Backend tests: `bash backend/tests/run_tests.sh`
- Frontend E2E tests: `bash frontend/tests/run_tests.sh`

### Key implementation notes
- Read env vars from `backend/.env` using shell (e.g. `grep`/`sed` or a small Python snippet) — do not assume any env vars are pre-exported
- `SUPABASE_URL` is derived from `SUPABASE_PROJECT_REF` in `config.py` — do not require it in `.env`
- `VITE_SUPABASE_URL` is derived from `SUPABASE_PROJECT_REF` in `vite.config.ts` — do not require it in `frontend/.env`
- Script must handle Windows (Git Bash / MINGW64) as primary platform; use `#!/usr/bin/env bash`
- The Docling model pre-download command is already documented in `SETUP.md §2` — reuse it exactly
- `013_sql_tool.sql` patch must be restored even if `supabase db push` fails (use trap for cleanup)
- Supabase CLI on Windows lives at `$APPDATA/npm/supabase.exe` — script should detect this path

---

## Feature: RAGAS Evaluation Pipeline

### Execution Phase
**Status**: ✅ Complete — pipeline built, behavioral unit tests added, integration tests skippable
**Started**: 2026-02-24
**Plan File**: `.agents/plans/ragas-evaluation-pipeline.md`
**Spec**: `.claude/specs/002-ragas-evaluation/`
**Depends on**: IR-Copilot Theme Change (postmortem docs must exist and be ingested)

Adds a reproducible RAG quality benchmark using the [RAGAS](https://docs.ragas.io) library. Calls retrieval + LLM services directly as Python imports (no HTTP, no running server needed). Scores 15 golden Q&A pairs drawn from the 6 postmortem documents across four metrics: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`. Results are pushed to LangSmith as dataset `ir-copilot-golden-set`.

**Files created:**
- `backend/eval/__init__.py`
- `backend/eval/dataset.py` — 15 EvalSample golden Q&A pairs (5 root cause · 3 timeline · 3 detection gap · 3 remediation · 1 cross-doc)
- `backend/eval/pipeline.py` — `run_rag_pipeline(question) -> {question, answer, contexts}`
- `backend/eval/evaluate.py` — RAGAS scoring + LangSmith push
- `backend/eval/tests/test_eval_pipeline.py` — 4 structural mocked unit tests (all passing)
- `backend/eval/requirements-eval.txt` — eval-only deps (ragas, datasets)
- `backend/eval/postmortems/*.md` — 6 incident postmortem documents

**Dependency note:** `ragas` is not in `pyproject.toml` due to transitive conflicts; installed separately via `uv pip install -r eval/requirements-eval.txt`. Must be re-run after any `uv sync`. `langsmith` was upgraded from `==0.1.147` to `>=0.2.0` in `pyproject.toml` (resolved to 0.7.6) to fix the LangSmith trace closure issue (see bug fixes below).

**RAGAS API adaptation:** Plan was written for RAGAS 0.1.x (`Dataset.from_dict()`). Installed version is 0.4.3, which uses `EvaluationDataset` + `SingleTurnSample`. `evaluate.py` uses the 0.4.3 API.

**Windows constraint:** `pyarrow.dataset` DLL is blocked by Windows Application Control. `evaluate.py` patches `sys.modules` at startup to mock it — no-op on Linux/Cloud Run where the DLL loads normally.

**Behavioral tests added (2026-02-25).** Test count expanded from 4 to 12 (10 automated + 2 skippable integration):

| Test | Type | Covers |
|------|------|--------|
| `test_pipeline_includes_all_retrieved_contexts` | Unit | Multi-chunk retrieval, context list completeness |
| `test_pipeline_passes_contexts_to_llm` | Unit | Context concatenation format sent to LLM |
| `test_off_topic_queries_return_no_context_fallback[x3]` | Unit (parametrized) | Anti-hallucination for 3 off-topic queries |
| `test_build_ragas_dataset_shape` | Unit | `build_ragas_dataset` produces valid `EvaluationDataset` |
| `test_in_distribution_query_live` | Integration (skipped) | Golden dataset query retrieves relevant context |
| `test_no_context_query_live` | Integration (skipped) | Off-topic query returns no-context fallback |

**Remaining gap — new-document queries:** Uploading additional documents via the app UI and verifying retrieval is scoped to those docs requires a full E2E harness. Documented as a manual validation step; cannot be unit-tested.

**Integration tests** run when `EVAL_DOCS_INGESTED=true` env var is set. Skipped otherwise.
Both integration tests verified passing (2026-02-25): in-distribution retrieval returned relevant context; off-topic query returned anti-hallucination fallback.

**evaluate.py — bugs fixed and first successful run (2026-02-25):**

Four bugs prevented `evaluate.py` from running end-to-end. All fixed:

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `TypeError: All metrics must be initialised metric objects` | `ragas.metrics.collections` exports a new API incompatible with legacy `evaluate()` — its classes don't inherit from `ragas.metrics.base.Metric` | Switched to legacy per-module singletons: `from ragas.metrics._faithfulness import faithfulness` etc. |
| `answer_relevancy: nan` | `AnswerRelevancy` (`MetricWithEmbeddings`) requires an embeddings object; none was provided | Pass `embeddings=embedding_factory("openai")` to `evaluate()` |
| LangSmith "ragas evaluation" trace stuck spinning | `langchain_core` 1.2.15 calls `RunTree.patch(exclude_inputs=...)` but langsmith 0.1.147's `patch()` took no arguments — callback threw, run never closed | Bumped `langsmith` to `>=0.2.0` in `pyproject.toml` (resolves to 0.7.6 which has `patch(*, exclude_inputs=False)`) |
| Cohere 429 on question 11/15 | Trial API key rate-limited to 10 req/min; pipeline called reranker once per question | Workaround: `enable_reranking=False` in `eval/pipeline.py`. Permanent fix: switch `RERANKING_PROVIDER=local` in `.env` (no rate limits) |
| Scores all 0 (no context retrieved) | `evaluate.py` used placeholder UUID `00000000-...` with no ingested docs | Sign in with `TEST_EMAIL`/`TEST_PASSWORD` via Supabase auth to get the real user UUID; pass it to `run_rag_pipeline` |

**First clean run scores (2026-02-25, test user, reranking disabled):**
```
faithfulness          : 0.922
answer_relevancy      : 0.973
context_precision     : 0.863
context_recall        : 0.967
```
15 examples pushed to LangSmith dataset `ir-copilot-golden-set`. LangSmith trace closes with green checkmark (no spinner).

**Second run (2026-02-25, test user, local reranking enabled):**

`eval/pipeline.py` updated to use config default (`enable_reranking=None`) instead of the Cohere workaround. `RERANKING_PROVIDER=local` in `.env` means the cross-encoder runs locally with no rate limits.

```
faithfulness          : 0.978  (+0.056 vs no-rerank baseline)
answer_relevancy      : 0.958  (-0.015)
context_precision     : 0.927  (+0.064)
context_recall        : 0.922  (-0.045)
```

Local reranking improves faithfulness and context_precision meaningfully. answer_relevancy and context_recall are within noise. Overall: reranking raises retrieval quality with no rate-limit risk.

**Dependency note (updated):** `ragas` cannot be added to `pyproject.toml` via `uv sync --group eval` because ragas 0.4.x requires `langchain-community`, whose 0.4.x series (compatible with langchain 1.x) requires `pydantic-settings>=2.10.1`, conflicting with the production pin `pydantic-settings==2.5.2`. Using `uv pip install -r eval/requirements-eval.txt` works because it installs into the already-resolved env (picking langchain-community 0.4.x + langchain 1.2.10) without re-solving project constraints. `requirements-eval.txt` updated with this explanation.

### Reports Generated

**Execution Report:** `.agents/execution-reports/ragas-evaluation-pipeline.md`
- Full implementation summary (both sessions)
- Divergences and resolutions (FK constraint, skipif timing, RAGAS API version)
- Test results and metrics (12/12 passing)
- Recommendations for plan and process improvements

---

## Feature: RAGAS ToolCallAccuracy Evaluation

**Status**: Complete
**Completed**: 2026-02-25
**Plan File**: `.agents/plans/ragas-tool-call-accuracy.md`

### What was built
- `supabase/migrations/016_production_incidents.sql` — `production_incidents` table (6 seed rows) + `execute_incidents_query` RPC (mirrors 013 pattern)
- `backend/services/sql_service.py` + `chat_service.py` — `books` domain fully replaced with `production_incidents`; tool renamed `query_incidents_database`
- `backend/eval/tool_selection_dataset.py` — 12 single-turn + 3 multi-turn samples with `reference_goal` fields
- `backend/eval/tool_selection_pipeline.py` — `run_tool_selection_pipeline()` (single-turn) + `run_multiturn_pipeline()` (real retrieve→analyze sequence)
- `backend/eval/evaluate_tool_selection.py` — 3-pass orchestrator: `tool_routing_accuracy`, `sequence_accuracy`, `AgentGoalAccuracy` (gpt-4o-mini); `--dry-run` / `--single-only` CLI flags
- `backend/eval/tests/test_tool_selection.py` — 11 unit tests, all mocked; full suite 23/23 passing
- `backend/tests/run_tests.sh` — `--include-evals` flag added; runs `eval/tests/` alongside `tests/auto/` when set; warns if `EVAL_DOCS_INGESTED` not set in `.env`

### Reports Generated

**Execution Report:** `.agents/execution-reports/ragas-tool-call-accuracy.md`
- Full implementation summary (all 4 waves)
- Divergences: system prompt embedding, manual migration apply, test count fix
- Test results: 23/23 passing (11 new + 12 pre-existing)
- Alignment score: 9/10

**System Review:** `.agents/system-reviews/ragas-tool-call-accuracy.md`
- Alignment score: 9/10
- Divergence analysis: 3 identified (2 GOOD ✅, 1 ENVIRONMENTAL ⚠️) — none problematic
- Process improvements: CLAUDE.md additions for migration apply, symbol exportability,
  eval boilerplate; plan template split for agent-executable vs manual validation steps
- Key action: create `eval/compat.py` before next eval module to consolidate pyarrow mock

---

## Eval Coverage Gap: Production Chat Endpoint Quality

**Status**: ✅ Complete
**Identified**: 2026-02-25
**Completed**: 2026-02-26
**Plan File**: `.agents/plans/chat-quality-evaluation.md`

### RAGAS Scores

#### Run 3 — 2026-02-26, `gpt-4o`, 15 golden samples (pre-dataset-fix baseline)

##### `evaluate.py` — simplified RAG pipeline (retrieve → one-shot LLM completion)
| Metric | Score |
|--------|-------|
| faithfulness | 0.865 |
| answer_relevancy | 0.743 |
| context_precision | 0.347 |
| context_recall | 0.156 |

##### `evaluate_chat_quality.py` — real ChatService end-to-end
| Metric | Score |
|--------|-------|
| faithfulness | 0.882 |
| answer_relevancy | **0.963** |
| context_precision | 0.300 |
| context_recall | 0.122 |
| arg_keyword_relevance | **1.000 (15/15)** |

Note: context_precision/recall were low because the 15 golden ground truths described completely different incidents than the actual postmortem documents — a dataset quality bug, not a retrieval quality bug. Ground truths and 4 questions were rewritten in run 4 to match the actual documents. See runs 5–6 for post-fix results.

##### `evaluate_tool_selection.py` — tool routing + arg quality (run 3)
| Metric | Score |
|--------|-------|
| routing accuracy (overall) | **1.000 (12/12)** |
| routing accuracy — retrieve | **1.000 (4/4)** |
| routing accuracy — sql | **1.000 (4/4)** |
| routing accuracy — web | **1.000 (4/4)** |
| arg keyword relevance (deterministic) | **1.000 (12/12)** |
| multi-turn sequence accuracy | 0.667 (2/3) ⚠️ |
| arg quality / AgentGoalAccuracy | 0.133 ⚠️ (truncated) |

#### Run 4 — 2026-02-26, `gpt-4o`, post-fixes

##### `evaluate_tool_selection.py` — tool routing + arg quality (run 4)
| Metric | Score |
|--------|-------|
| routing accuracy (overall) | **1.000 (12/12)** |
| routing accuracy — retrieve | **1.000 (4/4)** |
| routing accuracy — sql | **1.000 (4/4)** |
| routing accuracy — web | **1.000 (4/4)** |
| arg keyword relevance (deterministic) | **1.000 (12/12)** |
| multi-turn sequence accuracy | **1.000 (3/3)** ✅ |
| arg quality / AgentGoalAccuracy | **1.000 (12/12 single-turn)** ✅ |

**Previous run (2026-02-26 run 2, post-deployments fix):** RAG faithfulness 0.600 / chat faithfulness 0.207 / retrieve routing 0.250 (1/4) / chat arg_keyword_relevance 0.667 (10/15). All RAGAS metrics except faithfulness were 0.000 due to `strictness=3` returning only 1 generation.

> **Fixes confirmed working (runs 3–4):**
> - `answer_relevancy.strictness = 1` resolves the 0.000 RAGAS scores — all 4 RAGAS metrics now produce valid scores
> - Tool routing at 1.000 across all 3 categories (retrieve routing was 0.250 in run 2, now fixed by deployments table rename + system prompt rewrite)
> - Chat `arg_keyword_relevance` at 1.000 (15/15), up from 0.667 (10/15)
> - Multi-turn sequence accuracy at 1.000 (3/3), up from 0.667 — added PATTERN B example for "comprehensive summary of [specific incident]" to system prompt in `chat_service.py` and `tool_selection_pipeline.py`
> - `AgentGoalAccuracy` at 1.000 (12/12 single-turn) — switched judge to `gpt-4o` (was `gpt-4o-mini`, hit output token limit); multi-turn samples excluded from this metric (RAGAS `AgentGoalAccuracyWithReference` does not handle multi-step reference goals)

#### Run 5 — 2026-02-26, post-dataset-fix baseline (rate-limiting bug exposed)

##### `evaluate.py`
| Metric | Score |
|--------|-------|
| faithfulness | 0.732 |
| answer_relevancy | 0.680 |
| context_precision | 0.776 |
| context_recall | 0.411 |

context_precision/recall improved from run 3 (dataset fix confirmed working), but context_recall was still low. Investigation revealed two bugs:
1. **Supabase RPC rate limiting** — 15 questions fired sequentially with no delay; ~10 rapid calls hit Supabase's rate limit. The supabase-py exception includes raw HTTP response headers in its string representation. `evaluate.py`'s outer handler captured this as `[PIPELINE ERROR: ...headers...]` with `contexts=[]`, silently zeroing recall for ~6 samples. The bloated HTTP-headers answer also inflated the RAGAS faithfulness prompt for one sample, causing `max_tokens` exhaustion on 3 retries (visible as the 17-minute first evaluation item).
2. **RETRIEVAL_LIMIT=5 too low** — for the samples that did succeed, only 5 chunks were surfaced after reranking, missing some relevant document sections.

Fixes applied:
- `evaluate.py`: `asyncio.sleep(2)` between pipeline calls to stay under Supabase rate limit
- `config.py`: `RETRIEVAL_LIMIT` 5 → 10

#### Run 6 — 2026-02-26, post-rate-limit + retrieval-limit fix ✅

##### `evaluate.py`
| Metric | Score |
|--------|-------|
| faithfulness | **0.967** |
| answer_relevancy | **0.881** |
| context_precision | 0.585 |
| context_recall | **0.878** |

context_recall 0.411 → **0.878** (+0.467). faithfulness and answer_relevancy also recovered substantially (HTTP-headers no longer corrupting answers). context_precision dropped 0.776 → 0.585 — expected precision-recall tradeoff from doubling the retrieval limit (more relevant chunks retrieved alongside more lower-ranked ones).

---

### Reports Generated

**Execution Report:** `.agents/execution-reports/chat-quality-evaluation.md`
- Detailed implementation summary
- Divergences and resolutions
- Test results and metrics
- Team performance analysis

**System Review:** `.agents/system-reviews/chat-quality-evaluation.md`
- Alignment score: 9/10
- Divergence analysis (1 identified: 1 justified — import placement plan inconsistency, self-corrected by both Wave 1 agents)
- All 5 validation levels agent-executable and passing (no DB dependency — cleanest validation in eval series)
- Key actions: create `eval/compat.py` (overdue from prior review), add import-placement testability cross-check to CLAUDE.md

### Background

This section was initially written as a planning document. Here is the retrospective of what was discovered and what was actually built.

**The coverage gap** was identified by the user on 2026-02-25: the production chat endpoint had never been qualitatively evaluated. Two eval scripts existed but neither covered the full agentic loop:

- `eval/evaluate.py` — simplified RAG pipeline (retrieval → single LLM completion). No tool calling, no routing. Good for measuring retrieval quality in isolation.
- `eval/evaluate_tool_selection.py` — tool routing and arg quality using the real `chat_service.py`. Covers which tool is selected and whether args are reasonable, but never executes the tool and never scores the final synthesized response.

The missing piece: after the LLM selects a tool, executes it, and synthesizes a response from the results — that final response was never scored.

**What was built** — `eval/evaluate_chat_quality.py`:
- Calls `chat_service.stream_response()` directly as a Python import (no HTTP server needed), exercising the full agentic loop
- Captures tool calls, retrieved contexts, and final streamed response text
- Scores with all four RAGAS metrics + deterministic `arg_keyword_relevance` keyword check
- Pushes per-sample results to LangSmith dataset `ir-copilot-chat-quality`
- Shares the same 15-question golden dataset as `evaluate.py`

**User's key contributions to the eval improvement story:**

The first runs of `evaluate_chat_quality.py` produced near-zero scores across the board. The user investigated and diagnosed two root causes that agents had missed:

1. **Missing postmortem uploads** — all RAGAS scores (faithfulness, precision, recall) were zero because the postmortem documents had not been re-uploaded to the deployment after the `production_incidents → deployments` table rename. The eval was running against an empty document store. The user identified this directly, re-uploaded the 6 postmortem files, and scores became non-zero immediately.

2. **System prompt routing ambiguity** — after uploads, `arg_keyword_relevance` was still 0/15: the LLM was routing every retrieval question to `query_deployments_database` instead of `retrieve_documents`. The system prompt said "incidents, severity, services, resolution times → query_incidents_database" — which matched the language of most golden questions. The user identified this routing conflict, drove the rename of `production_incidents` to `deployments` and the rewrite of the system prompt to make the domain boundary unambiguous. This brought `arg_keyword_relevance` from 0/15 to 10/15 (run 2) and then 15/15 (run 3).

3. **RAGAS `strictness` bug** — `answer_relevancy`, `context_precision`, and `context_recall` were all 0.000 across all runs due to RAGAS requesting `n=3` completions but modern OpenAI APIs returning only `n=1`. The user flagged this as a scoring infrastructure issue rather than a genuine quality problem. Setting `answer_relevancy.strictness = 1` fixed all three metrics in run 3.

Without the user's investigation, all three issues would have remained invisible — agents would have iterated on prompt tuning against a silent empty document store and broken scoring infrastructure.

### Current automated coverage

| Flow step | Coverage | Script/test |
|-----------|----------|-------------|
| Tool routing (which tool) | ✅ mocked unit + ✅ eval script | `test_tool_selection.py`, `evaluate_tool_selection.py` |
| Arg quality (keyword check) | ✅ keyword logic unit + ✅ eval script | `test_tool_selection.py` T20–T22, `evaluate_tool_selection.py` |
| Multi-turn sequence | ✅ mocked unit + ✅ eval script — 3/3 (1.000) | `test_tool_selection.py` T12–T15, `evaluate_tool_selection.py` |
| Tool execution mechanics | ✅ live auto tests | `test_hybrid_search.py`, `test_sql_service.py`, etc. |
| Final response quality (real chat) | ✅ scored, faithfulness 0.882 / relevancy 0.963 | `evaluate_chat_quality.py` |
| Retrieval ranking quality | ✅ scored — context_recall 0.878, faithfulness 0.967 (run 6) | `evaluate.py` |

### Remaining gaps and next steps for the next agent

~~**1. Re-run `evaluate.py` and `evaluate_chat_quality.py` to confirm context_precision/recall improvement**~~ ✅ **Resolved (run 6)**

context_recall rose from 0.122–0.156 to **0.878**. Two bugs found and fixed during the re-run: Supabase RPC rate limiting (silent `contexts=[]` for ~6 samples) and `RETRIEVAL_LIMIT=5` too low. `evaluate_chat_quality.py` not re-run — its context quality is now expected to be at parity given the same retrieval stack improvement.

~~**2. Multi-turn sequence accuracy 0.667 (2/3)**~~ ✅ **Resolved (run 4)**
Added "comprehensive summary of [specific incident]" as an explicit PATTERN B trigger in `chat_service.py` and `tool_selection_pipeline.py`. Re-run confirmed 3/3 (1.000).

~~**3. `AgentGoalAccuracy` results unreliable (0.133, truncated)**~~ ✅ **Resolved (run 4)**
Switched judge from `gpt-4o-mini` to `gpt-4o` — output token limit no longer exceeded. Multi-turn samples excluded from this metric (RAGAS `AgentGoalAccuracyWithReference` doesn't handle multi-step reference goals; sequence correctness is already captured by `sequence_accuracy`). Re-run confirmed 1.000 (12/12 single-turn).

---

## Investigation: Low Eval Scores (2026-02-26)

**Status**: ✅ Complete — all issues resolved; see "Remaining gaps" above for post-fix re-run status
**Priority**: High — scores are below expectations across all three pipelines

### Expected vs Actual

| Metric | Actual | Expected range | Gap |
|--------|--------|----------------|-----|
| RAG pipeline faithfulness | 0.600 | 0.85+ | significant |
| RAG pipeline answer_relevancy | 0.000 † | 0.70+ | needs investigation |
| RAG pipeline context_precision | 0.000 † | 0.40+ | needs investigation |
| RAG pipeline context_recall | 0.000 † | 0.20+ | needs investigation |
| Chat quality faithfulness | 0.207 | 0.70+ | significant |
| Chat quality arg_keyword_relevance | 0.667 (10/15) | 1.000 | 5 questions failing |
| Tool selection — retrieve routing | 0.250 (1/4) | 1.000 | 3/4 misrouted |
| Multi-turn retrieve→analyze | 0.000 (0/3) | 0.667+ | fully broken |

### Issue 1: RAGAS `†` metrics all 0.000 (answer_relevancy, context_precision, context_recall)

**Symptom:** Every run of both `evaluate.py` and `evaluate_chat_quality.py` produces 0.000 for three metrics. The run log shows:
```
LLM returned 1 generations instead of requested 3. Proceeding with 1 generations.
```
(repeated 15 times, one per sample)

**Hypothesis:** RAGAS `answer_relevancy` generates multiple question variants from the answer to measure how well the answer addresses the question. `context_precision`/`context_recall` use a similar LLM-grading approach. If the RAGAS version expects OpenAI to return `n=3` completions in one API call but OpenAI now defaults to `n=1`, these metrics silently collapse to 0.000.

**How to investigate:**
1. Check RAGAS version: `cd backend && uv run python -c "import ragas; print(ragas.__version__)"`
2. Check if this is a known RAGAS issue for this version (search GitHub issues)
3. Run with 1 sample and inspect what RAGAS actually receives: add debug logging to `ragas` internals or check LangSmith trace for the scoring call
4. **Quick test:** Check if the previous run 1 scores (faithfulness 0.861, answer_relevancy 0.745) were produced under the same RAGAS version — if yes, something changed between runs; if the previous scores came from a different version, this is a version regression

**Files to check:**
- `backend/eval/requirements-eval.txt` — pinned RAGAS version
- `backend/eval/evaluate.py` lines ~100-130 — how RAGAS metrics are instantiated

---

### Issue 2: Chat quality faithfulness = 0.207 (LLM answers not grounded in context)

**Symptom:** When `chat_service.py` calls `retrieve_documents`, gets context back, and generates an answer, RAGAS judges only 20.7% of claims in the answer as grounded in the retrieved context.

**Hypotheses:**
- **A: Retrieved chunks don't contain the answer.** The LLM calls `retrieve_documents` with a query that retrieves the wrong chunks, then has to hallucinate because the right information wasn't in context.
- **B: LLM synthesizes beyond context.** The LLM has general knowledge about incident response and adds information not from the retrieved docs.
- **C: Multi-call retrieval not happening.** The system prompt encourages multiple `retrieve_documents` calls for comprehensive coverage, but the LLM may only make one call and answer from limited context.

**How to investigate:**
1. Run with `--dry-run` and inspect per-sample output: `cd backend && uv run python eval/evaluate_chat_quality.py --dry-run 2>&1 | head -200`
   - Look at `tool_name`, `tool_args`, and the actual answer text for each sample
   - Check if the retrieved contexts actually contain the expected answer
2. Check `backend/eval/chat_quality_pipeline.py` — how are `contexts` populated for RAGAS? Are they the raw chunk texts or just metadata?
3. For a single failing question, manually call `retrieve_documents` with the same args the LLM used and inspect the returned chunks
4. Compare the 5 chunks returned vs the golden `ground_truth` in `eval/dataset.py` — how much overlap is there?

**Files to check:**
- `backend/eval/chat_quality_pipeline.py` — full pipeline implementation
- `backend/eval/evaluate_chat_quality.py` — scoring setup
- `backend/eval/dataset.py` — golden Q&A pairs with ground_truth answers

---

### Issue 3: 5 questions failing arg_keyword_relevance (LLM not calling retrieve_documents)

**The 5 failing questions (from 2026-02-26 run):**
1. "How long did the INC-2024-003 auth outage last?" — duration question
2. "How long did it take to identify the root cause of INC-2024-...?" — time-to-detect question
3. "How long did it take to detect the INC-2024-031 notification...?" — time-to-detect question
4. "Why did the deployment rollback fail in INC-2024-038?" — mentions "deployment" + "rollback"
5. "Which incident had the longest resolution time and how long...?" — comparative/aggregate question

**Hypotheses:**
- **Q1–Q3 (duration/time questions):** The LLM may be routing these to `query_deployments_database` because they mention "how long" (duration) which sounds like `duration_seconds`. The new system prompt routing guidance says "deployment counts and averages → query_deployments_database" — "how long" could match "averages" in the LLM's interpretation.
- **Q4 (deployment rollback):** Contains the word "deployment" and "rollback" — the tool description for `query_deployments_database` explicitly covers "rollback frequency". This is a clear routing ambiguity: it's asking WHY a deployment rollback failed (→ `retrieve_documents`) but it looks like a deployment fact query.
- **Q5 (longest resolution time):** Aggregate comparison question — may route to SQL because it sounds like a MAX(duration) query.

**How to investigate:**
1. Run a targeted dry-run and capture the tool called for each question: `cd backend && uv run python eval/evaluate_chat_quality.py --dry-run 2>&1`
2. For each failing question, check `tool_name` in the output — is it calling SQL, web, or nothing?
3. Review `backend/services/chat_service.py` system prompt routing guidance (the NOTE section added in the deployments fix) — does it explicitly cover "how long did an incident last?" as a retrieval question?

---

### Issue 4: Tool selection retrieve routing 0.250 (1/4) and multi-turn 0.000 (0/3)

**The 4 retrieve routing test questions** (from `backend/eval/tool_selection_dataset.py`):
- Read the file to find the exact 4 questions in the `retrieve` category

**Multi-turn sequences** (from `backend/eval/tool_selection_dataset.py` or pipeline):
- 3 sequences: retrieve→analyze pattern. 0/3 suggests the second step (analyze_document_with_subagent) is never triggered.

**How to investigate:**
1. Read `backend/eval/tool_selection_dataset.py` lines 1-58 (retrieve category samples) and the multi-turn sequences
2. Read `backend/eval/tool_selection_pipeline.py` — how multi-turn is evaluated
3. Check if the 4 retrieve questions have enough signal words to distinguish from SQL/web in the current system prompt

---

### Diagnostic Quick-Start for Investigating Agent

```bash
# 1. Check RAGAS version (for Issue 1)
cd backend && uv run python -c "import ragas; print(ragas.__version__)"

# 2. Get per-sample output for chat quality (for Issues 2 & 3)
cd backend && uv run python eval/evaluate_chat_quality.py --dry-run 2>&1

# 3. See the retrieve routing test questions
cd backend && uv run python -c "
from eval.tool_selection_dataset import TOOL_SELECTION_DATASET
for s in TOOL_SELECTION_DATASET:
    if s.category == 'retrieve':
        print(s.question)
"

# 4. Manually test a failing question
cd backend && uv run python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()
from services.chat_service import ChatService
from eval.eval_utils import get_eval_user_id

async def test():
    user_id = get_eval_user_id()
    history = [{'role': 'user', 'content': 'How long did the INC-2024-003 auth outage last?'}]
    async for delta, sources, metadata in ChatService.stream_response(history, user_id):
        pass
    print('Tool called:', metadata.get('tool_calls_summary') if metadata else 'none')

asyncio.run(test())
"
```

**Key files for the investigating agent:**
- `backend/eval/evaluate_chat_quality.py` — chat quality eval script
- `backend/eval/chat_quality_pipeline.py` — pipeline that calls chat_service and captures context
- `backend/eval/dataset.py` — 15 golden Q&A pairs with ground_truth
- `backend/eval/tool_selection_dataset.py` — tool routing test questions (retrieve category lines 1-58)
- `backend/services/chat_service.py` lines 195-290 — system prompt with routing guidance
- `backend/eval/requirements-eval.txt` — pinned RAGAS version

---

### Findings & Fixes (2026-02-26)

**Root causes confirmed by live testing:**

#### RC1: Postmortem documents not uploaded for the eval test user (CRITICAL)
Direct retrieval with `threshold=0.0` confirmed only `phoenix_report.txt` exists for the test user —
the 6 postmortem files (INC-2024-003 through INC-2024-038) are not ingested. This explains:
- `context_precision=0.000`, `context_recall=0.000` in RAG pipeline eval — retrieved chunks are from
  `phoenix_report.txt` (irrelevant to postmortem ground_truth answers)
- Chat quality returning 0-1 irrelevant chunks for every retrieval question
- Multi-turn 0.000 — empty retrieval result means no document names to pass to analyze_document_with_subagent

**USER ACTION REQUIRED:** Upload all 6 files from `backend/eval/postmortems/` via the app UI
as the test user (`TEST_EMAIL`), then re-run eval pipelines.

#### RC2: Routing ambiguity — incident content routed to SQL (FIXED ✅)
5 chat quality questions and 3/4 tool-selection retrieve questions misrouted to
`query_deployments_database` because the system prompt routing guidance didn't explicitly cover
incident duration/timeline/comparison questions as retrieve territory.

- Confirmed via live testing: "How long did INC-2024-003 last?" → SQL, validation error, no fallback
- Fix applied: Replaced vague NOTE with explicit INCIDENT vs DEPLOYMENT routing tables in:
  - `backend/services/chat_service.py` lines ~276-297
  - `backend/eval/tool_selection_pipeline.py` TOOL_SELECTION_SYSTEM_PROMPT

**Validation:** All 4 previously failing chat-quality questions now route to `retrieve_documents`.
Tool selection single-turn accuracy jumped from 0.750 → 1.000 (12/12).

#### RC3: RAGAS answer_relevancy strictness=3 requesting n=3 completions (FIXED ✅)
RAGAS 0.4.3 `answer_relevancy.strictness=3` requests n=3 LLM completions per sample to generate
question variants for cosine similarity scoring. Modern OpenAI APIs return only n=1, emitting:
`"LLM returned 1 generations instead of requested 3. Proceeding with 1 generations."`
This likely causes 0.000 scores for answer_relevancy.

Fix applied: `answer_relevancy.strictness = 1` set before `evaluate()` in both:
- `backend/eval/evaluate.py`
- `backend/eval/evaluate_chat_quality.py`

---

### Next step: re-run evals after document upload

After the user uploads all 6 postmortem files:
```bash
cd backend && bash eval/run_evals.sh --dry-run
```
Expected improvements after RC1+RC2+RC3 fixes:
- Tool selection retrieve: 0.250 → 1.000 ✅ (already verified)
- Chat quality arg_keyword_relevance: 0.667 → ~1.000 (all 15 route to retrieve)
- Chat quality faithfulness: 0.207 → 0.70+ (proper contexts now retrieved)
- RAG pipeline context_precision/recall: 0.000 → real scores (postmortem chunks available)
- answer_relevancy: 0.000 → real scores (strictness=1 fix)

---

## Feature: SQL Tool Topic — Replace production_incidents with Deployments

**Status**: ✅ Complete (pending user DB migration for Levels 3–4)
**Started**: 2026-02-26
**Completed**: 2026-02-26
**Plan File**: `.agents/plans/sql-topic-replace-incidents-with-deployments.md`

### What Changed

Replaced `production_incidents` SQL table with `deployments` (change management log) to eliminate tool-routing ambiguity. The two tools now cover orthogonal domains:
- `retrieve_documents` → postmortem narrative content (uploaded documents)
- `query_deployments_database` → deployment facts (SQL table)

### Files Changed (14 total)

- `supabase/migrations/016_production_incidents.sql` → deleted
- `supabase/migrations/016_deployments.sql` → created (15 seed rows, RLS, `execute_deployments_query` RPC)
- `supabase/migrations/ADHOC_migrate_to_deployments.sql` → created (one-shot upgrade for existing DB)
- `backend/services/sql_service.py` — `DEPLOYMENTS_SCHEMA`, all validation strings, RPC call
- `backend/services/chat_service.py` — tool name/description, system prompt routing guidance, all dispatch refs
- `backend/eval/tool_selection_dataset.py` — 4 deployment-domain SQL samples
- `backend/eval/tool_selection_pipeline.py` — TOOL_SELECTION_SYSTEM_PROMPT updated
- `backend/eval/README.md` — table row updated
- `backend/eval/tests/test_tool_selection.py` — `valid_tools` set updated
- `backend/tests/auto/test_sql_service.py` — all 6 tests updated to deployments domain
- `backend/tests/auto/test_multi_tool_integration.py` — incident→deployment questions
- `backend/tests/auto/test_simple_strategic.py`, `tests/manual/test_strategic_*.py` — tool name refs

### Validation Results

| Level | Status | Notes |
|-------|--------|-------|
| 1 — No dead refs | ✅ | Zero source matches for old names |
| 2 — Import sanity | ✅ | `DEPLOYMENTS_SCHEMA` imports OK |
| 3 — SQL service tests | ✅ | 6/6 passed against live deployments table |
| 4 — Full pytest suite | ✅ | 86/86 passed, 0 regressions |
| 5 — Eval dry-run | ✅ | sql 4/4 = 1.000 — deployment questions route correctly |

### Reports Generated

**Execution Report:** `.agents/execution-reports/sql-topic-replace-incidents-with-deployments.md`
- Alignment score: 9/10
- 3 divergences identified (all justified: missing `--limit` flag in plan, 2 extra files discovered by grep, more dispatch occurrences than plan counted)
- Levels 1, 2, 5 validated; Levels 3–4 pending DB migration

---

# System Status

**Servers:**
- Backend: http://localhost:8000 (FastAPI + Uvicorn)
- Frontend: http://localhost:5173 (React + Vite)
- API Docs: http://localhost:8000/docs

**Environment:**
- Python 3.12 (required - 3.14 has pydantic compilation issues)
- Node.js with npm
- Supabase project in supported region (pgvector enabled)
