# Feature: Module 4 - Metadata Extraction

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution (console.log, print, etc.) that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes - no git operations

**IMPORTANT:** Validate documentation and codebase patterns before implementing. Pay attention to existing naming conventions, imports, and RLS patterns. Module 3 (Record Manager) is already implemented - duplicate detection is in place.

## Feature Description

Add LLM-powered document-level metadata extraction to enhance retrieval quality. When documents are uploaded, the system extracts a structured summary using OpenAI-compatible LLMs with JSON schema validation. This metadata provides additional context during retrieval, improving search relevance and enabling future metadata-based filtering.

**User Value:** Better search results through semantic understanding of document content. Extracted summaries help users quickly understand what documents contain without reading full text.

## User Story

As a RAG application user
I want documents to be automatically summarized during ingestion
So that I can find more relevant information when searching, and quickly understand document content at a glance

## Problem Statement

Current retrieval relies solely on vector similarity between query and chunks. This misses higher-level document context:
- No document-level understanding - only chunk-level matching
- Queries like "show me technical reports" can't leverage document type metadata
- Users can't quickly preview what a document contains
- Future filtering by metadata (category, topic, type) not possible without extraction infrastructure

## Solution Statement

Implement document-level metadata extraction using LLM structured outputs (Pydantic + OpenAI JSON schema):
1. After parsing document text (in `process_document()`), call LLM to extract structured metadata
2. Store metadata in documents table (new columns: summary, document_type, key_topics)
3. Track extraction status separately from ingestion status
4. Backend-only feature (no UI changes in Module 4)
5. Foundation for future metadata-enhanced retrieval and filtering

## Feature Metadata

**Feature Type**: Enhancement (New Capability)
**Estimated Complexity**: Medium
**Primary Systems Affected**: Ingestion pipeline, provider service, database schema, document models
**Dependencies**: OpenAI SDK (existing), Pydantic (existing), Module 3 completed (duplicate detection)
**Breaking Changes**: No (new columns nullable, extraction optional via flag)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: READ THESE BEFORE IMPLEMENTING!

**Ingestion Pipeline:**
- `backend/routers/ingestion.py` (lines 16-108) - `process_document()` background task where metadata extraction will be added after parsing
- `backend/routers/ingestion.py` (lines 111-223) - `upload_document()` endpoint to add metadata extraction parameters

**Provider Service Pattern:**
- `backend/services/provider_service.py` (lines 50-216) - Provider abstraction, client creation pattern to mirror for structured output method
- `backend/services/provider_service.py` (lines 175-216) - `_get_client()` pattern for provider detection

**Service Layer Pattern:**
- `backend/services/embedding_service.py` (lines 9-135) - Service class structure to mirror for metadata service

**Models:**
- `backend/models/document.py` (lines 34-44) - DocumentResponse model to extend with metadata fields

**Database:**
- `supabase/migrations/006_documents_and_chunks.sql` - Documents table schema
- `supabase/migrations/010_variable_dimensions_no_ivfflat.sql` - Recent migration pattern to follow

**Testing:**
- `backend/test_ingestion.py` - Test patterns for ingestion, authentication, background processing

### New Files to Create

- `supabase/migrations/012_metadata_extraction.sql` - Add metadata columns to documents table
- `backend/models/metadata.py` - Pydantic schemas for LLM structured output
- `backend/services/metadata_service.py` - Metadata extraction business logic
- `backend/test_metadata_extraction.py` - Comprehensive test suite

### Patterns to Follow

**Structured Output:** Use `response_format={"type": "json_schema", ...}` with Pydantic models
**RLS:** Always filter by `eq("user_id", user_id)`
**Service Layer:** Static methods, module-level instance (like embedding_service.py)
**Error Handling:** Log but don't fail ingestion if metadata extraction fails
**Logging:** `print(f"[METADATA_EXTRACTION] Provider: {provider} | Model: {model}")`

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌──────────────────────────────────────────────────────┐
│ WAVE 1: Database & Models (Parallel)                 │
├──────────────────────────────────────────────────────┤
│ Task 1.1: Migration  │ Task 1.2: Pydantic Models    │
│ Agent: db-specialist │ Agent: backend-dev           │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ WAVE 2: Service Layer (Parallel - After Wave 1)     │
├──────────────────────────────────────────────────────┤
│ Task 2.1: Provider   │ Task 2.2: Metadata Service   │
│ Agent: backend-dev   │ Agent: backend-dev           │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ WAVE 3: Integration (Sequential - After Wave 2)     │
├──────────────────────────────────────────────────────┤
│ Task 3.1: Ingestion Pipeline Integration            │
│ Task 3.2: Document Model Update                      │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ WAVE 4: Testing (Parallel - After Wave 3)           │
├──────────────────────────────────────────────────────┤
│ Task 4.1: Unit Tests │ Task 4.2: Integration Tests │
│ Agent: test-writer   │ Agent: test-writer          │
└──────────────────────────────────────────────────────┘
```

### Parallelization Summary

- **Wave 1 (2 parallel):** Database schema + Pydantic models - independent
- **Wave 2 (2 parallel):** Provider method + Metadata service - both need Wave 1 models
- **Wave 3 (2 sequential):** Pipeline integration requires both Wave 2 services
- **Wave 4 (2 parallel):** Unit + integration tests can run concurrently

**Max Speedup:** 2x with 2 parallel agents (4 waves, 8 tasks, 50% parallel)

### Interface Contracts

**Contract 1:** Task 1.2 provides `DocumentMetadata` Pydantic model → Tasks 2.1, 2.2 consume
**Contract 2:** Task 2.1 provides `create_structured_completion()` method → Task 2.2 consumes
**Contract 3:** Task 2.2 provides `extract_metadata()` + `update_document_metadata()` → Task 3.1 consumes

### Synchronization Checkpoints

**After Wave 1:** Verify migration applied, models importable
**After Wave 2:** Test provider method with mock schema, test metadata service in isolation
**After Wave 3:** End-to-end test: upload document, verify metadata extracted
**After Wave 4:** Full test suite passes

---

## IMPLEMENTATION PLAN

### Phase 1: Database Schema (Wave 1)

Add metadata columns to documents table, track extraction status separately from ingestion status.

### Phase 2: Pydantic Models (Wave 1)

Define structured output schema for LLM extraction using Pydantic with Field descriptions.

### Phase 3: Provider Service Extension (Wave 2)

Add structured completion method to provider service supporting JSON schema validation.

### Phase 4: Metadata Service (Wave 2)

Create service layer for metadata extraction business logic, error handling, database updates.

### Phase 5: Ingestion Integration (Wave 3)

Integrate metadata extraction into existing process_document() pipeline after parsing.

### Phase 6: Testing & Validation (Wave 4)

Comprehensive automated test coverage for extraction, storage, error handling, RLS.

---

## STEP-BY-STEP TASKS

### WAVE 1: Foundation

#### Task 1.1: CREATE migration 012_metadata_extraction.sql

- **WAVE**: 1
- **AGENT_ROLE**: db-specialist
- **DEPENDS_ON**: []
- **BLOCKS**: [3.1, 3.2]
- **PROVIDES**: Database schema with metadata columns
- **IMPLEMENT**:
  ```sql
  -- Add metadata columns to documents table
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type TEXT;
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS key_topics TEXT[] DEFAULT ARRAY[]::TEXT[];
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMP WITH TIME ZONE;
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata_status TEXT DEFAULT 'pending'
    CHECK (metadata_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

  -- Create indexes for future filtering
  CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type)
    WHERE document_type IS NOT NULL;
  CREATE INDEX IF NOT EXISTS idx_documents_key_topics ON documents USING GIN(key_topics)
    WHERE key_topics IS NOT NULL AND array_length(key_topics, 1) > 0;
  CREATE INDEX IF NOT EXISTS idx_documents_metadata_status ON documents(metadata_status);

  -- Comments
  COMMENT ON COLUMN documents.summary IS 'LLM-extracted 2-3 sentence summary';
  COMMENT ON COLUMN documents.document_type IS 'Document type (article, report, guide, etc.)';
  COMMENT ON COLUMN documents.key_topics IS 'Array of main topics/themes (3-5 items)';
  COMMENT ON COLUMN documents.metadata_status IS 'Metadata extraction status - independent from document status';
  ```
- **PATTERN**: Follow migration 010 structure (ALTER TABLE, CREATE INDEX, COMMENT)
- **VALIDATE**: Apply migration via Supabase SQL Editor
  ```sql
  -- Verify columns exist
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name = 'documents'
  AND column_name IN ('summary', 'document_type', 'key_topics', 'metadata_status', 'extracted_at');
  -- Expected: 5 rows

  -- Verify indexes
  SELECT indexname FROM pg_indexes WHERE tablename = 'documents' AND indexname LIKE '%metadata%';
  -- Expected: idx_documents_metadata_status, idx_documents_document_type, idx_documents_key_topics
  ```

---

#### Task 1.2: CREATE backend/models/metadata.py

- **WAVE**: 1
- **AGENT_ROLE**: backend-dev
- **DEPENDS_ON**: []
- **BLOCKS**: [2.1, 2.2]
- **PROVIDES**: `DocumentMetadata` Pydantic schema for LLM structured output
- **IMPLEMENT**: Create `backend/models/metadata.py` with Pydantic schema:
  - `summary: str` - Field(description="2-3 sentence summary", min_length=50, max_length=500)
  - `document_type: str` - Field(description="article|research_paper|technical_guide|report|tutorial|...", pattern="^(...)")
  - `key_topics: List[str]` - Field(description="3-5 main topics", min_items=1, max_items=5)
  - Add `Config.json_schema_extra` with example
- **PATTERN**: Follow models/document.py - BaseModel, Field with descriptions
- **GOTCHA**: Use `...` for required fields
- **VALIDATE**: `python -c "from backend.models.metadata import DocumentMetadata; print('✓ OK')"`

**Wave 1 Checkpoint:**
```bash
# Verify migration applied
psql -h [supabase-host] -d postgres -c "SELECT column_name FROM information_schema.columns WHERE table_name='documents' AND column_name='summary';"
# Expected: summary

# Verify models importable
python -c "from backend.models.metadata import DocumentMetadata; print('✓ Models OK')"
```

---

### WAVE 2: Service Layer

#### Task 2.1: UPDATE backend/services/provider_service.py - Add structured completion method

- **WAVE**: 2
- **AGENT_ROLE**: backend-dev
- **DEPENDS_ON**: [1.2]
- **BLOCKS**: [2.2]
- **PROVIDES**: `create_structured_completion()` method for JSON schema validation
- **USES_FROM_WAVE_1**: Task 1.2 provides DocumentMetadata schema
- **IMPLEMENT**: Add `create_structured_completion()` method after line 216:
  - Takes: provider, model, messages, response_schema (Pydantic BaseModel class), base_url
  - Get client via `_get_client(provider, base_url)`
  - Build `response_format = {"type": "json_schema", "json_schema": {"name": response_schema.__name__, "schema": response_schema.model_json_schema(), "strict": True}}`
  - Call `client.chat.completions.create()` with response_format
  - Parse JSON, validate with `response_schema(**parsed_json)`
  - Return validated instance
  - Error handling: JSONDecodeError, ValidationError, generic Exception → RuntimeError
  - Add imports: `from pydantic import BaseModel, ValidationError`
- **PATTERN**: Follow stream_chat_completion() method (lines 50-174)
- **GOTCHA**: Only gpt-4o, gpt-4o-mini support structured outputs
- **VALIDATE**: Test call with DocumentMetadata schema, verify returns instance

---

#### Task 2.2: CREATE backend/services/metadata_service.py

- **WAVE**: 2
- **AGENT_ROLE**: backend-dev
- **DEPENDS_ON**: [1.2, 2.1]
- **BLOCKS**: [3.1]
- **PROVIDES**: `extract_metadata()` and `update_document_metadata()` business logic
- **IMPLEMENT**:
  - **extract_metadata()**: Takes text_content, document_id, user_id, provider, model, base_url → returns DocumentMetadata
    - Default model: gpt-4o-mini
    - Truncate text if > 100k chars (~25k tokens)
    - System prompt: "You are a document analysis expert. Extract structured metadata..."
    - User prompt: "Extract metadata from this document: {text_content}"
    - Call provider_service.create_structured_completion() with DocumentMetadata schema
    - Log: `[METADATA] Extracting for doc=..., provider=...`
    - Return DocumentMetadata instance
  - **update_document_metadata()**: Takes document_id, metadata, supabase, user_id → updates DB
    - Build update_data: summary, document_type, key_topics, extracted_at, metadata_status="completed"
    - Query: `supabase.table("documents").update(...).eq("id", document_id).eq("user_id", user_id)`
    - Log: `[METADATA] ✓ Updated document {doc_id[:8]}`
  - Instantiate at module level: `metadata_service = MetadataService()`
- **PATTERN**: Mirror embedding_service.py - static methods, module instance
- **GOTCHA**: Always RLS filter with user_id
- **VALIDATE**: Test extraction with sample text, verify returns DocumentMetadata

**Wave 2 Checkpoint:**
```bash
# Test provider method with mock schema
python -c "from backend.services.provider_service import provider_service; print('✓ Provider service OK')"

# Test metadata service imports
python -c "from backend.services.metadata_service import metadata_service; print('✓ Metadata service OK')"
```

---

### WAVE 3: Integration

#### Task 3.1: UPDATE backend/routers/ingestion.py - Integrate metadata extraction

- **WAVE**: 3
- **AGENT_ROLE**: integration-specialist
- **DEPENDS_ON**: [2.2]
- **BLOCKS**: []
- **PROVIDES**: End-to-end metadata extraction during ingestion
- **USES_FROM_WAVE_2**: Task 2.2 provides extract_metadata() and update_document_metadata()
- **IMPLEMENT**:
  1. Add import: `from services.metadata_service import metadata_service`
  2. Update `process_document()` signature (line 16): Add params `extract_metadata=True`, `metadata_provider=None`, `metadata_model=None`
  3. Add metadata extraction after line 41 (after parse_document):
     - If extract_metadata: mark metadata_status="processing", call metadata_service.extract_metadata(), update document
     - If extraction fails: mark metadata_status="failed", log error, continue ingestion
     - If not extract_metadata: mark metadata_status="skipped"
  4. Update `upload_document()` signature (line 111): Add Form params `extract_metadata=True`, `metadata_provider=None`, `metadata_model=None`
  5. Update background_tasks.add_task() call (line 202): Pass new metadata params
- **PATTERN**: Log errors, don't fail ingestion if metadata fails
- **GOTCHA**: Metadata runs AFTER Module 3 duplicate detection
- **VALIDATE**: Upload test doc with extract_metadata=true, check metadata_status="completed"

---

#### Task 3.2: UPDATE backend/models/document.py - Add metadata fields to response

- **WAVE**: 3
- **AGENT_ROLE**: backend-dev
- **DEPENDS_ON**: [1.1, 3.1]
- **BLOCKS**: []
- **PROVIDES**: API responses include metadata fields
- **IMPLEMENT**: Update DocumentResponse class (lines 34-44):
  ```python
  class DocumentResponse(BaseModel):
      """Document response model."""
      id: str
      filename: str
      content_type: str
      file_size_bytes: int
      chunk_count: int
      status: str
      error_message: Optional[str] = None
      duplicate_of: Optional[str] = None  # Module 3
      created_at: str
      updated_at: str

      # NEW - Module 4 Metadata Fields
      summary: Optional[str] = None
      document_type: Optional[str] = None
      key_topics: Optional[list[str]] = None
      extracted_at: Optional[str] = None
      metadata_status: Optional[str] = None
  ```
- **PATTERN**: Follow Optional[type] = None pattern from existing fields
- **VALIDATE**:
  ```bash
  # GET documents endpoint should return metadata fields
  curl http://localhost:8000/ingestion/documents \
    -H "Authorization: Bearer $TOKEN" | jq '.[0] | {summary, document_type, key_topics, metadata_status}'
  # Expected: Fields present (may be null if not extracted yet)
  ```

**Wave 3 Checkpoint:**
```bash
# End-to-end test
# 1. Upload document
# 2. Wait 5 seconds
# 3. Query document - verify metadata_status = 'completed' and summary populated
```

---

### WAVE 4: Testing

#### Task 4.1: CREATE backend/test_metadata_extraction.py - Unit tests

- **WAVE**: 4
- **AGENT_ROLE**: test-writer
- **DEPENDS_ON**: [3.1, 3.2]
- **BLOCKS**: []
- **PROVIDES**: Unit test coverage
- **IMPLEMENT**: Create 3 unit tests:
  1. `test_document_metadata_schema_validation()` - Pydantic schema validation (valid/invalid cases)
  2. `test_metadata_extraction_service()` - Real LLM call with test text, verify structure
  3. `test_metadata_truncation_for_long_documents()` - 150k char doc truncation
- **PATTERN**: Follow test_ingestion.py - TestClient, auth helper, async tests
- **VALIDATE**: `cd backend && python test_metadata_extraction.py`

---

#### Task 4.2: CREATE backend/test_metadata_integration.py - Integration tests

- **WAVE**: 4
- **AGENT_ROLE**: test-writer
- **DEPENDS_ON**: [3.1, 3.2]
- **BLOCKS**: []
- **PROVIDES**: E2E test coverage
- **IMPLEMENT**: Create 3 integration tests:
  1. `test_end_to_end_metadata_extraction()` - Upload doc, wait 5s, verify metadata_status="completed", summary/topics populated
  2. `test_metadata_extraction_disabled()` - Upload with extract_metadata=false, verify metadata_status="skipped"
  3. `test_metadata_failure_does_not_block_ingestion()` - Tiny doc (may fail extraction), verify ingestion still works
- **PATTERN**: Use cleanup_test_documents_and_storage, TestClient, wait 3-5s for background processing
- **VALIDATE**: `cd backend && python test_metadata_integration.py`

**Wave 4 Checkpoint:**
```bash
# Run all tests
cd backend
python test_metadata_extraction.py
python test_metadata_integration.py
# Expected: All tests pass
```

---

## TESTING STRATEGY

**Unit Tests (✅ Automated):** 3 tests in `test_metadata_extraction.py` - schema validation, LLM extraction, truncation
**Integration Tests (✅ Automated):** 3 tests in `test_metadata_integration.py` - E2E extraction, disabled flag, failure isolation
**Manual Tests (⚠️):** 2 tests - migration verification (Supabase Dashboard), provider compatibility (OpenRouter, LM Studio)

**Total:** 6 automated + 2 manual = 100% code coverage, manual for infrastructure

---

## VALIDATION COMMANDS

**Level 0 - Migration:** SQL queries to verify columns (summary, document_type, key_topics, metadata_status, extracted_at) and indexes
**Level 1 - Models:** `python -c "from models.metadata import DocumentMetadata; print('✓ OK')"`
**Level 2 - Unit Tests:** `cd backend && python test_metadata_extraction.py`
**Level 3 - Integration Tests:** `cd backend && python test_metadata_integration.py`
**Level 4 - API Test:** Upload doc with curl, wait 5s, query `/ingestion/documents`, verify metadata_status="completed"

---

## ACCEPTANCE CRITERIA

- [ ] Migration 012 applied successfully (5 columns + 3 indexes)
- [ ] DocumentMetadata Pydantic model validates correctly (summary, document_type, key_topics)
- [ ] ProviderService.create_structured_completion() method works with OpenAI JSON schema
- [ ] MetadataService.extract_metadata() returns valid DocumentMetadata
- [ ] MetadataService.update_document_metadata() stores metadata in database
- [ ] process_document() extracts metadata after parsing, before chunking
- [ ] upload_document() accepts extract_metadata, metadata_provider, metadata_model params
- [ ] DocumentResponse includes metadata fields (summary, document_type, key_topics, metadata_status, extracted_at)
- [ ] Metadata extraction failure doesn't block ingestion (status still 'completed')
- [ ] RLS enforced on metadata queries (user_id filtering)
- [ ] All automated tests pass (6/6)
- [ ] Manual validation confirms migration applied, indexes created
- [ ] No regressions in existing ingestion flow

---

## COMPLETION CHECKLIST

- [ ] All Wave 1 tasks completed (migration + models)
- [ ] All Wave 2 tasks completed (provider service + metadata service)
- [ ] All Wave 3 tasks completed (ingestion integration + model updates)
- [ ] All Wave 4 tasks completed (unit + integration tests)
- [ ] Migration 012 applied via Supabase SQL Editor
- [ ] Level 0 validation passed (migration columns + indexes)
- [ ] Level 1 validation passed (model imports)
- [ ] Level 2 validation passed (unit tests)
- [ ] Level 3 validation passed (integration tests)
- [ ] Level 4 validation passed (manual API testing)
- [ ] All acceptance criteria met
- [ ] Code follows project conventions (RLS, provider abstraction, async/await)
- [ ] No regressions (existing tests still pass)
- [ ] ⚠️ Debug logs added during execution REMOVED (keep pre-existing logs only)
- [ ] ⚠️ CRITICAL: Changes left UNSTAGED (NOT committed) for user review

---

## NOTES

**Design:** Document-level only (not chunk-level), backend-only (no UI), summary focus, extraction status separate from ingestion status
**Module 3 Integration:** Metadata extraction happens BEFORE duplicate detection, so duplicates get metadata extracted
**Cost:** ~$0.01-0.02/doc with gpt-4o-mini (~1-3k input + 200-400 output tokens)
**Future:** UI filtering, metadata display, chunk-level metadata, custom schemas, backfill script, retrieval enhancement
