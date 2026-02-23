# Project Summary: Remaining Tasks & Lessons Learned

---

## Module 1: App Shell + Observability ✅

**Remaining tasks:**
- ✅ **RESOLVED** Full auth/chat suite validation (10 pre-existing test failures) — resolved by the New Project Setup Walkthrough (2026-02-21). Final state: 86 collected, 0 skipped, 0 errors.
- ✅ **RESOLVED** TypeScript error resolution — `tsc --noEmit` exits 0 with no output. No type errors.

**Lessons learned:** None documented.

---

## Module 2: BYO Retrieval + Memory ✅

**Remaining tasks:**
- ✅ **RESOLVED** E2E chat with custom providers — Playwright test added (`optional-e2e-validation.spec.ts`: "Module 2 Extension: E2E Chat with OpenRouter Provider"). Switches chat to OpenRouter (`openai/gpt-4o` via `openrouter.ai/api/v1`), sends "What is the capital of France?", verifies "Paris" response. Requires `OPENROUTER_API_KEY` in backend `.env`.
- ✅ **RESOLVED** Document ingestion with custom embeddings — Playwright test added (`optional-e2e-validation.spec.ts`: "Module 2 Extension: Embedding Model Change"). Full E2E validated: switched to `text-embedding-3-large` (3072 dims), uploaded a document, queried it, and confirmed retrieval worked. Both branches tested: (1) no chunks → model change allowed, ingestion and retrieval verified; (2) chunks exist → safety lock active, selects disabled, warning displayed. Cleanup: document deleted + page reload resets in-memory model config to defaults.
- ❌ **CANNOT AUTOMATE** Cross-browser compatibility — Playwright config is Chromium-only; adding Firefox/WebKit would require modifying playwright.config.ts (out of scope).
- ✅ **RESOLVED (with finding)** Settings persistence across browser restarts — Playwright test confirmed: settings do NOT persist across browser sessions. Root cause: `useModelConfig` uses React `useState` only. `confirmChanges()` updates in-memory state — nothing is saved to the backend DB or localStorage. Settings reset to OpenAI defaults on every new session. Documented as known limitation in README.md Known Limitations #2.

**Lessons learned:** None documented.

---

## Module 3: Record Manager ✅

**Remaining tasks:** None.

**Lessons learned:** None documented.

---

## Module 4: Metadata Extraction ✅

**Remaining tasks:**
- ❌ **STILL OUTSTANDING** Metadata-enhanced retrieval — confirmed not implemented in Modules 5–8 or any enhancement. The retrieval pipeline uses vector/hybrid search only; stored metadata (summary, document_type, key_topics) is never used to filter or boost results. Documented in README.md Known Limitations #1. Requires code changes to implement.

**Lessons learned:** None documented.

---

## Module 5: Multi-Format Support ✅

**Remaining tasks:**
- ✅ **RESOLVED** PPTX upload and processing — automated Playwright test added (`optional-e2e-validation.spec.ts`). python-pptx is installed in the venv. PPTX fixture created, uploaded, and processed successfully.

**Lessons learned:**
- `SUPPORTED_FILE_TYPES` in `.env` overrides `config.py` defaults — users must manually update `.env` when config changes.

---

## Module 6: Hybrid Search & Reranking ✅

**Remaining tasks:**
- ✅ **RESOLVED** Hybrid search retrieval quality — automated Playwright test added (`optional-e2e-validation.spec.ts`). Uploaded a document with unique fictional content, queried for it, and verified the response contained the correct unique value. Search quality confirmed.

**Lessons learned:**
- PyTorch version conflicts (2.2.2 vs sentence-transformers requirement) can arise mid-project; have a fallback provider (Cohere) ready.

---

## Enhancement: Multi-File Upload ✅

**Remaining tasks:** None (minor timing flake noted, non-blocking).

**Lessons learned:** None documented.

---

## Module 7: Additional Tools ✅

**Remaining tasks:**
- ✅ **RESOLVED** E2E browser tests — both automated via Playwright (`optional-e2e-validation.spec.ts`):
  - "What books were written by George Orwell?" → 1984 and Animal Farm returned via SQL tool ✅
  - "What are the latest AI news headlines today?" → live results returned via Tavily web search ✅

**Lessons learned:** None documented.

---

## Module 8: Sub-Agents ✅

**Remaining tasks:**
- ✅ **RESOLVED** Sub-agent E2E test — automated via Playwright (`optional-e2e-validation.spec.ts`). Document uploaded, sub-agent spawned by asking "analyze document [filename] and extract the quarterly revenue breakdown", quarterly revenue data extracted and returned correctly.

**Lessons learned:**
- When stream_response() signature changes (2-tuple → 3-tuple), all unpacking sites (routers, tests) must be updated — treat as a breaking change.

---

## Enhancement: LangSmith Tool Tracing ✅

**Remaining tasks:** None.

**Lessons learned (most detailed in codebase):**

1. **Always use `finally` blocks for async generator cleanup.** Trace closure (and any resource cleanup) in a `try` block is not guaranteed if the generator is interrupted. `finally` is the only safe pattern.

2. **Validate trace lifecycle, not just creation.** Plans should explicitly test: normal completion closes trace, error scenario closes trace, stream interruption closes trace. Missing this led to a non-closing trace bug discovered only in production.

3. **Check dependency compatibility before implementation.** `sentence-transformers` installation conflicted with existing PyTorch version. Workaround: switched to Cohere reranking. Should have tested in isolated venv first and included a rollback plan.

4. **Incremental testing saves time.** Adding one tool at a time and verifying trace hierarchy would have caught the cleanup bug earlier. With the improved process: ~50% time saved (105 min → ~55 min).

---

## Bug Fix: Duplicate Upload Requests ✅

**Remaining tasks:** None.

**Lessons learned:**

1. **Stale closures in React async callbacks.** `useCallback` with state dependencies recreates the function reference; `setTimeout` captures the new function but reads stale state. Fix: use refs (`useRef`) for values read in async callbacks, remove state from `useCallback` deps.

2. **AbortController for deduplication.** Handles React Strict Mode's double-invocation pattern and guards against duplicate HTTP requests from any source.

3. **Evidence-gathering before fixing.** 4 guard-based approaches failed before console logging (unique call IDs, timestamps, stack traces) revealed the root cause. Start with instrumentation.

---

## Bug Fix: PDF Upload Pipeline ✅

**Remaining tasks:** None.

**Lessons learned:**

1. **Pin `docling>=2.0.0`, not a specific old version.** `docling==0.4.0` expected a `.pt` layout file; current HuggingFace model repo switched to ONNX.

2. **Pre-download scripts must run a real conversion.** Calling `DocumentConverter()` alone only initializes; layout models are lazy-loaded on first actual PDF. Run a minimal real conversion to force full cache population.

3. **Non-ASCII filenames cause Supabase Storage `InvalidKey` errors.** Fix: use `user_id/uuid.ext` paths and preserve the original filename only in the DB record. Also eliminates duplicate-path collisions.

4. **Supabase Realtime requires `REPLICA IDENTITY FULL` on RLS-enabled tables.** Without it, UPDATE events are silently dropped (Realtime can't verify user access against the old row state). The table being in the `supabase_realtime` publication is not enough.

5. **RapidOCR logging can't be suppressed with `setLevel`.** Its `Logger.__init__` resets the log level at import time. Use a `logging.Filter` instead, applied after all router imports in `main.py`.

6. **Use explicit venv paths (`venv/Scripts/uvicorn`), not PATH activation.** PATH activation is unreliable on Windows; the bare `uvicorn` command may pick up the system Python instead.

---

## New Project Setup Walkthrough ✅

**Remaining tasks:** None.

**Lessons learned:**

1. **`pytest-asyncio` must be explicitly installed and configured.** Without `asyncio_mode = auto` in `pytest.ini`, async tests are silently skipped (not failed).

2. **Separate `auto/` and `manual/` test directories** prevent live-server tests from polluting the automated pytest suite.

3. **`SUPPORTED_FILE_TYPES` in `backend/.env` silently restricts accepted formats.** New project setups will silently reject formats not in that list regardless of `config.py` defaults.

---

## Enhancement: LangSmith Trace Automated Tests ✅

**Remaining tasks:** None.

**Lessons learned:**

- LangSmith REST API quirk: `GET /api/v1/runs?session_name=...` returns 405. Correct pattern: `GET /api/v1/sessions?name=<project>` to get UUID, then `POST /api/v1/runs/query` with `{"session": [uuid]}`.
- LangSmith has 10–30s propagation delay; tests must poll (every 4s, up to 40s) rather than assert immediately.

---

## Bug Fix: PDF Parsing Failure on Real-World Documents ✅

**Remaining tasks:** None.

**Lessons learned:**

1. **Docling's layout model requires PyTorch ≥ 2.4.** Simple test PDFs (single text block) bypass the layout pipeline and succeed even with broken model setup. Always test with a real complex document (tables, images, multi-column).

2. **Use explicit venv binary paths everywhere** (`venv/Scripts/uvicorn`). Activation alone is unreliable on Windows.

3. **Windows HuggingFace symlinks require Developer Mode or admin rights.** Document this in SETUP.md prerequisites.

---

## Render Deployment Fixes ✅

**Remaining tasks:** None.

**Lessons learned:**

1. **Render's Python version file must be named `.python-version`** (not `runtime.txt`) and contain only the version number (e.g., `3.12.0`, not `python-3.12.0`). Wrong filename defaults to Python 3.14, breaking pydantic-core compilation.

2. **`huggingface_hub` extra changed from `hf_xet` (underscore) to `hf-xet` (hyphen)** in 1.x. Use `huggingface_hub[hf-xet]>=0.27`.

3. **Hardcode the port** (`--port 8000`) rather than relying on `$PORT` — Render auto-detects the bound port.

---

## Cloud Run Migration ✅

**Status:** Complete (2026-02-23)

**Service URL:** `https://agentic-rag-94676406483.me-west1.run.app`

**Lessons learned:**

1. **Apply env vars before first push.** Without them, Pydantic `Settings()` crashes the app at startup before it can bind any port.
2. **Never hardcode port in Cloud Run CMD.** Use `${PORT:-8000}` — Cloud Run injects `PORT=8080` and health-checks on that port.
3. **Set memory to 2 GiB minimum** for torch+docling. Default 512 MiB is insufficient even for startup warmup.
4. **Avoid `--no-traffic` on a service with a pinned revision.** Future deploys sit at 0% traffic. Follow up with `update-traffic --to-latest`.
5. **Cloud Run has two URL formats:** `{name}-{project-number}.{region}.run.app` (GCP console) and `{name}-{hash}.a.run.app` (API). Both work.

---

## Repository Maintenance: Secret Removal ✅

**Remaining tasks:** None.

**Lessons learned:** None documented.
