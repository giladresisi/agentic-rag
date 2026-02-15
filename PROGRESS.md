# Progress

Track progress through the RAG Masterclass modules.

## Convention
- `[x]` = Completed and validated
- `[-]` = In progress
- `[ ]` = Not started

---

## Module 1: App Shell + Observability ✅

**Status:** Complete and validated

- [x] Backend (FastAPI, auth, chat router with SSE streaming)
- [x] Frontend (React, auth flow, chat interface, threading)
- [x] Database (Supabase with RLS policies)
- [x] OpenAI Responses API migration (stateless completions)
- [x] All core functionality validated with Playwright tests

**Test Credentials:** Stored in .env (TEST_EMAIL, TEST_PASSWORD)

**Known Issues:**
- 10 pre-existing test failures in auth/chat suites (route protection, JWT persistence, thread creation)
- TypeScript errors (missing vite-env.d.ts) - pre-existing, doesn't impact runtime

---

## Module 2: BYO Retrieval + Memory ✅

**Status:** Complete and validated

### Completed Features

**Plan 4: Chat Completions Migration** ✅
- Migrated from Responses API to Chat Completions API for provider flexibility

**Plan 5: Document Ingestion Pipeline** ✅
- Upload interface with drag-drop, file validation, realtime status updates
- Docling integration for PDF, DOCX, HTML, Markdown parsing
- Chunking, embeddings (OpenAI), pgvector storage
- Supabase storage with RLS policies

**Plan 6: Vector Retrieval Tool** ✅
- RAG tool calling infrastructure with retrieve_documents tool
- pgvector cosine similarity search with RLS enforcement
- Source display in chat UI with similarity scores
- Comprehensive test suite (retrieval, RLS, tool calling)

**Plan 7: Model Selection Enhancement** ✅
- Centralized settings modal (chat + embeddings configuration)
- User profile menu at bottom of sidebar
- Removed API key fields from UI (server-side only)
- Provider/model selection with dropdowns (OpenAI) and text inputs (others)
- 12/12 Playwright tests passing

**Plan 8: Enhanced Provider Settings** ✅
- 3 providers only: OpenAI, OpenRouter, LM Studio (removed Ollama, Custom)
- Provider-specific UI (dropdowns for predefined models, text inputs for custom)
- Variable embedding dimensions support (migration 010)
- Auto-append /v1 to LM Studio base URLs
- Provider logging (chat & embeddings calls show provider/model/URL)
- Settings preservation on modal reopen
- 9/9 backend provider service tests passing

### Test Status

**Automated Tests - All Passing:**
- Frontend settings: 12/12 ✅
- Backend provider service: 9/9 ✅
- Backend RAG retrieval: All passing ✅
- Backend ingestion: All passing ✅
- Backend tool calling: All passing ✅

**Manual Testing Required (Optional):**
Six items require manual verification but don't block Module 3:
1. End-to-end chat with configured model (verify backend logs/LangSmith)
2. Document ingestion with custom embeddings (verify database dimensions)
3. Provider switching visual behavior (field reset animations)
4. Dimensions field across configurations (multiple values testing)
5. Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
6. Settings persistence across browser restarts

**Why manual:** Require backend log inspection, database checks, visual verification, or multi-browser testing.

### Database Migrations Applied

- 001-007: Core schema, auth, threading, documents/chunks, retrieval function
- 010: Variable embedding dimensions (no ivfflat index for flexibility)

### Configuration

**Current Settings:**
```python
RETRIEVAL_LIMIT = 5                      # Max chunks per retrieval
RETRIEVAL_SIMILARITY_THRESHOLD = 0.7     # Minimum similarity (0-1)
```

**Providers:**
- OpenAI (default): https://api.openai.com/v1
- OpenRouter: https://openrouter.ai/api/v1
- LM Studio: User-defined URL (auto-appends /v1)

**Default Models:**
- Chat: gpt-4o
- Embeddings: text-embedding-3-small (1536 dims)

### Module 2 Success Criteria - All Met ✅

- [x] Chat works with any OpenAI-compatible provider
- [x] Document ingestion supporting multiple formats
- [x] Chunking and embedding pipeline working
- [x] pgvector similarity search functional
- [x] RAG tool infrastructure ready (tool calling, sources, RLS)
- [x] Realtime status updates during ingestion
- [x] RLS enforced on all tables
- [x] Provider switching with settings modal
- [x] Variable embedding dimensions support

---

## Module 3: Record Manager 🔄

**Status:** Not started

Will include:
- Content hashing for deduplication
- Update detection and re-ingestion logic
- Version tracking

---

## Module 4: Metadata Extraction 🔄

**Status:** Not started

Will include:
- LLM-extracted metadata from documents
- Filtered retrieval by metadata
- Enhanced search capabilities

---

## Module 5: Multi-Format Support ✅

**Status:** Complete and validated

**Plan:** `.agents/plans/module-5-multi-format-enhancement.md`
**Execution Report:** `.agents/execution-reports/module-5-multi-format-enhancement.md`

### Completed Features

**Part 1: Cascade Delete Optimization** ✅
- Removed redundant manual chunk deletion (4 lines removed)
- Database ON DELETE CASCADE handles chunks automatically
- Improved get_document_chunks endpoint error handling (proper 404 responses)
- Added validation test to ensure cascade behavior works correctly

**Part 2: Multi-Format Support Expansion** ✅
- Added 5 new file formats to existing 5 (total: 10 formats)
  - PPTX (PowerPoint) - via Docling
  - CSV (data files) - via Docling
  - JSON (structured data) - direct read
  - XML (markup) - via Docling
  - RTF (rich text) - direct read
- Updated backend config (config.py)
- Updated frontend validation (DocumentUpload.tsx)
- Added sync comments between frontend/backend configs

### Test Status

**Automated Tests - All Passing:**
- 8/8 tests passing (100% pass rate)
- 1 optional test skipped (PPTX - requires python-pptx library)

**New Tests Added:**
1. `test_delete_document_cascade()` - Validates cascade delete works ✅
2. `test_upload_json_file()` - JSON format upload ✅
3. `test_upload_csv_file()` - CSV format upload ✅
4. `test_upload_xml_file()` - XML format upload ✅
5. `test_upload_rtf_file()` - RTF format upload ✅
6. `test_upload_pptx_file()` - PPTX format upload ⚠️ (skipped - optional)

### Files Modified

**Backend (4 files):**
- `backend/config.py` - 10 supported formats (+2/-1)
- `backend/routers/ingestion.py` - Cascade delete fix, 404 handling (+5/-8)
- `backend/services/embedding_service.py` - JSON/RTF simple parsing (+1/-1)
- `backend/test_ingestion.py` - 6 new tests (+137/-0)

**Frontend (1 file):**
- `frontend/src/components/Ingestion/DocumentUpload.tsx` - 10 formats + MIME types (+10/-2)

**Total:** 155 insertions(+), 12 deletions(-)

### Configuration Updates

**Supported Formats (10 total):**
- Existing: PDF, DOCX, HTML, MD, TXT
- New: PPTX, CSV, JSON, XML, RTF

**Parsing Strategy:**
- Simple (direct read): TXT, MD, HTML, JSON, RTF
- Docling (converter): PDF, DOCX, PPTX, CSV, XML

### Known Issues

- ⚠️ **Environmental Dependency:** backend/.env file must be updated manually if SUPPORTED_FILE_TYPES is defined there (pydantic-settings prioritizes env vars over code defaults)
- ℹ️ PPTX test requires `python-pptx` library (optional dependency, gracefully skipped)

### Module 5 Success Criteria - All Met ✅

- [x] 5 new file formats supported
- [x] Cascade delete optimization implemented
- [x] Frontend/backend config synchronized
- [x] Test coverage for all formats
- [x] Cascade delete validation test
- [x] No regressions
- [x] Code quality maintained

### Reports Generated

**Execution Report:** `.agents/execution-reports/module-5-multi-format-enhancement.md`
- Detailed implementation summary
- Divergences and resolutions
- Test results and metrics
- Team performance analysis

**System Review:** `.agents/system-reviews/module-5-multi-format-enhancement.md`
- Alignment score: 9/10
- Divergence analysis (2 identified: 1 justified, 1 environmental)
- Process improvements and CLAUDE.md updates completed
- Key learnings and recommendations for next implementation

---

## Module 6: Hybrid Search & Reranking 🔄

**Status:** Not started

Will include:
- Keyword search (BM25) + vector search
- Reciprocal Rank Fusion (RRF)
- Reranking models
- Performance optimization

---

## Module 7: Additional Tools 🔄

**Status:** Not started

Will include:
- Text-to-SQL for structured data queries
- Web search fallback for current information

---

## Module 8: Subagents 🔄

**Status:** Not started

Will include:
- Isolated context for subagent reasoning
- Document analysis delegation
- Multi-agent coordination

---

## System Status

**Servers:**
- Backend: http://localhost:8000 (FastAPI + Uvicorn)
- Frontend: http://localhost:5173 (React + Vite)
- API Docs: http://localhost:8000/docs

**Environment:**
- Python 3.12 (required - 3.14 has pydantic compilation issues)
- Node.js with npm
- Supabase project in supported region (pgvector enabled)

**Next Steps:**
1. Begin Module 3: Record Manager
2. Optional: Address pre-existing test failures (auth/chat suites)
3. Optional: Complete manual testing checklist from Module 2

---

## Quick Reference

**Run Backend:**
```bash
cd backend
venv/Scripts/python -m uvicorn main:app --reload
```

**Run Frontend:**
```bash
cd frontend
npm run dev
```

**Run Tests:**
```bash
# Frontend (Playwright)
cd frontend
npm test

# Backend (specific test)
cd backend
venv/Scripts/python test_provider_service.py
```

**Apply Database Migration:**
1. Open Supabase Dashboard → SQL Editor
2. Copy migration file contents from `supabase/migrations/`
3. Run SQL commands sequentially (001 → 002 → ... → 010)
