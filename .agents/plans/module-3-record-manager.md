# Feature: Module 3 - Record Manager (Content Hashing & Deduplication)

**IMPORTANT:** Validate documentation and codebase patterns before implementing. Pay attention to existing naming conventions, imports, and RLS patterns.

## Feature Description

Add intelligent content-based deduplication to the RAG application's document ingestion pipeline. Currently, uploading the same file multiple times creates duplicate document records, chunks, and embeddings—wasting tokens, storage, and processing time. Module 3 introduces SHA-256 content hashing to detect duplicates at both file and text levels, skipping redundant processing while maintaining user visibility into duplicate uploads.

## User Story

As a RAG application user
I want the system to automatically detect when I upload duplicate content
So that I don't waste API tokens and storage on redundant processing, while still tracking all upload attempts

## Problem Statement

The current ingestion pipeline naively processes every upload:
- Same file uploaded twice → 2 document records, 2x chunks, 2x embedding API calls
- Same content in different formats (PDF vs DOCX) → duplicate chunks and embeddings
- No change detection → re-uploading modified files doesn't distinguish from duplicates
- Cost impact: Unnecessary OpenAI embedding API calls (~$0.13 per 1M tokens)
- Storage impact: Duplicate chunks in pgvector table

## Solution Statement

Implement two-level content hashing:
1. **File Content Hash** (SHA-256 of raw bytes) - Detects identical files
2. **Text Content Hash** (SHA-256 of parsed text) - Detects semantic duplicates across formats

After upload but before chunking/embedding, check if user already has document with same text hash. If duplicate found, mark new document as `status='duplicate'` with reference to original, skip processing, return original chunks for retrieval.

## Feature Metadata

**Feature Type**: Enhancement (New Capability)
**Estimated Complexity**: Medium
**Primary Systems Affected**: Ingestion pipeline, database schema, document models
**Dependencies**: hashlib (Python stdlib), existing ingestion flow from Module 2
**Breaking Changes**: No (new columns nullable, new status value backward-compatible)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: READ THESE BEFORE IMPLEMENTING!

- `backend/routers/ingestion.py` (lines 16-108) - Background `process_document()` function where duplicate detection logic will be added after parsing
- `backend/routers/ingestion.py` (lines 111-223) - `upload_document()` endpoint where file hash computation will be added after storage upload
- `backend/services/embedding_service.py` (lines 13-96) - Document parsing and chunking logic; will add hash computation methods here
- `backend/models/document.py` (lines 34-44) - `DocumentResponse` model needing `duplicate_of` field addition
- `backend/config.py` - Application settings (no changes needed, but review for patterns)
- `supabase/migrations/006_documents_and_chunks.sql` - Current schema (documents and chunks tables)
- `supabase/migrations/010_variable_dimensions_no_ivfflat.sql` - Recent schema changes showing migration pattern
- `backend/test_utils.py` - Test utilities and cleanup functions to follow for new tests
- `backend/test_ingestion.py` - Existing ingestion tests showing patterns to follow

### New Files to Create

- `supabase/migrations/011_content_hashing.sql` - Database migration adding hash columns, duplicate status, indexes
- `backend/test_record_manager.py` - Comprehensive test suite for deduplication scenarios

### Patterns to Follow

**Hash Computation Pattern** (use Python stdlib):
```python
import hashlib

# File hash (raw bytes)
sha256_hash = hashlib.sha256()
with open(file_path, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
        sha256_hash.update(byte_block)
file_hash = sha256_hash.hexdigest()  # Returns 64-char hex string

# Text hash (string content)
text_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
```

**Database Query Pattern** (from existing code):
```python
# Check for existing document with same hash
result = supabase.table("documents")\
    .select("id, filename, created_at, chunk_count")\
    .eq("user_id", current_user["id"])\
    .eq("text_content_hash", computed_hash)\
    .eq("status", "completed")\
    .execute()

if result.data:
    # Duplicate found
    original_doc = result.data[0]
```

**RLS Pattern** (all queries must scope by user_id):
```python
# ALWAYS include user_id in queries for RLS enforcement
.eq("user_id", current_user["id"])
```

**Error Handling Pattern** (from ingestion.py lines 96-108):
```python
except Exception as e:
    error_message = f"Error during processing: {str(e)}"
    logger.error(error_message)
    supabase.table("documents").update({
        "status": "failed",
        "error_message": error_message,
        "updated_at": "now()"
    }).eq("id", document_id).execute()
```

**Testing Pattern** (from test_ingestion.py):
```python
from test_utils import TEST_EMAIL, TEST_PASSWORD

def get_auth_token():
    response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    return response.json()["access_token"]

def test_example():
    token = get_auth_token()
    # Test upload
    files = {"file": ("test.md", BytesIO(b"content"), "text/markdown")}
    response = client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Schema Changes

Add hash columns and duplicate tracking to documents table via migration.

**Tasks:**
- Create migration 011 with `file_content_hash`, `text_content_hash`, `duplicate_of` columns
- Add 'duplicate' to status CHECK constraint
- Create partial indexes for fast hash lookups (user_id + hash WHERE hash IS NOT NULL)
- Apply migration via Supabase Dashboard SQL Editor

**Validation:**
```sql
-- Verify columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
AND column_name IN ('file_content_hash', 'text_content_hash', 'duplicate_of');

-- Verify indexes created
SELECT indexname FROM pg_indexes WHERE tablename = 'documents' AND indexname LIKE '%hash%';
```

---

### Phase 2: Hash Computation Service

Add hash generation methods to embedding service.

**Tasks:**
- Add `compute_file_hash(file_path: str) -> str` static method to EmbeddingService
- Add `compute_text_hash(text: str) -> str` static method to EmbeddingService
- Use hashlib.sha256() with chunked reading for files (4096 byte blocks)
- Return lowercase hex digest (64 characters)

**Validation:**
```python
# Test in Python REPL
from backend.services.embedding_service import EmbeddingService
hash1 = EmbeddingService.compute_text_hash("test content")
hash2 = EmbeddingService.compute_text_hash("test content")
assert hash1 == hash2  # Same input = same hash
assert len(hash1) == 64  # SHA-256 = 64 hex chars
```

---

### Phase 3: Upload Endpoint Modification

Compute file hash after storage upload, before background processing.

**Tasks:**
- In `upload_document()` after line 169 (storage upload), download temp file to compute file hash
- Add `file_content_hash` to document INSERT (line 173)
- Pass file_content_hash to background task via temp file path

**Validation:**
```bash
# Upload a file and check database
curl -X POST http://localhost:8000/ingestion/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.md"

# Query database to verify file_content_hash populated
# SELECT file_content_hash FROM documents ORDER BY created_at DESC LIMIT 1;
```

---

### Phase 4: Duplicate Detection Logic

Add duplicate check in background processing task after text parsing.

**Tasks:**
- In `process_document()` after line 40 (parse_document call), compute text_content_hash
- Query for existing document: `user_id = current_user AND text_content_hash = hash AND status = 'completed'`
- If duplicate found:
  - Update current document: `status='duplicate'`, `duplicate_of=original_id`, `text_content_hash=hash`
  - Skip chunking/embedding (return early from function)
  - Log duplicate detection with original filename and date
- If not duplicate:
  - Update document with `text_content_hash=hash`
  - Proceed with chunking → embedding → chunk insertion (existing flow)

**Validation:**
```python
# Test: Upload same file twice
# First upload: status should be 'completed'
# Second upload: status should be 'duplicate', duplicate_of should point to first
```

---

### Phase 5: Model Updates

Add duplicate_of field to API response models.

**Tasks:**
- Update `DocumentResponse` class in models/document.py
- Add `duplicate_of: Optional[str] = None` field (line 42)
- Update `Document` class if needed for internal use

**Validation:**
```bash
# GET /ingestion/documents should include duplicate_of in response
curl -X GET http://localhost:8000/ingestion/documents \
  -H "Authorization: Bearer $TOKEN" | jq '.[].duplicate_of'
```

---

### Phase 6: Testing Implementation

Create comprehensive test suite for all deduplication scenarios.

**Tasks:**
- Create `test_record_manager.py` with tests:
  - `test_hash_generation_consistency()` - Same content = same hash
  - `test_duplicate_same_file()` - Upload identical file twice
  - `test_duplicate_different_format()` - Same text, different format (MD vs TXT)
  - `test_modified_content_reprocesses()` - Changed content = new processing
  - `test_duplicate_references_original()` - Verify duplicate_of FK works
  - `test_duplicate_no_chunks_created()` - Duplicates don't create chunks
  - `test_original_chunks_retrievable()` - Can query chunks via duplicate_of
- Use existing test patterns from test_utils.py and test_ingestion.py
- Include database cleanup in each test

**Validation:**
```bash
cd backend
python test_record_manager.py
# All tests should pass
```

---

## STEP-BY-STEP TASKS

### Task 1: CREATE migration 011_content_hashing.sql

**Purpose:** Add database schema support for content hashing and duplicate tracking

- **IMPLEMENT**:
  ```sql
  -- Add hash columns to documents table
  ALTER TABLE documents
    ADD COLUMN file_content_hash TEXT,
    ADD COLUMN text_content_hash TEXT,
    ADD COLUMN duplicate_of UUID REFERENCES documents(id) ON DELETE SET NULL;

  -- Update status constraint to include 'duplicate'
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_status_check;
  ALTER TABLE documents ADD CONSTRAINT documents_status_check
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'duplicate'));

  -- Create partial indexes for fast hash lookups
  CREATE INDEX idx_documents_text_hash ON documents(user_id, text_content_hash)
    WHERE text_content_hash IS NOT NULL;

  CREATE INDEX idx_documents_file_hash ON documents(user_id, file_content_hash)
    WHERE file_content_hash IS NOT NULL;

  -- Add helpful comments
  COMMENT ON COLUMN documents.file_content_hash IS 'SHA-256 hash of raw file bytes';
  COMMENT ON COLUMN documents.text_content_hash IS 'SHA-256 hash of extracted text content';
  COMMENT ON COLUMN documents.duplicate_of IS 'References original document if duplicate detected';
  ```
- **PATTERN**: Follow migration 010 structure (ALTER TABLE, CREATE INDEX, COMMENT)
- **GOTCHA**: Use partial indexes (`WHERE hash IS NOT NULL`) to avoid indexing NULL values
- **VALIDATE**:
  ```sql
  -- Run in Supabase SQL Editor
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'documents' AND column_name LIKE '%hash%';
  -- Should return: file_content_hash, text_content_hash

  SELECT indexname FROM pg_indexes WHERE tablename = 'documents';
  -- Should include: idx_documents_text_hash, idx_documents_file_hash
  ```

---

### Task 2: UPDATE backend/services/embedding_service.py - Add hash methods

**Purpose:** Implement SHA-256 hash computation for files and text

- **IMPLEMENT**: Add these static methods to EmbeddingService class after line 96:
  ```python
  @staticmethod
  def compute_file_hash(file_path: str) -> str:
      """Compute SHA-256 hash of file contents.

      Args:
          file_path: Path to file to hash

      Returns:
          64-character lowercase hex string (SHA-256 digest)
      """
      import hashlib
      sha256_hash = hashlib.sha256()
      with open(file_path, "rb") as f:
          # Read in 4KB chunks to handle large files efficiently
          for byte_block in iter(lambda: f.read(4096), b""):
              sha256_hash.update(byte_block)
      return sha256_hash.hexdigest()

  @staticmethod
  def compute_text_hash(text: str) -> str:
      """Compute SHA-256 hash of text content.

      Args:
          text: String content to hash

      Returns:
          64-character lowercase hex string (SHA-256 digest)
      """
      import hashlib
      return hashlib.sha256(text.encode('utf-8')).hexdigest()
  ```
- **IMPORTS**: hashlib is Python stdlib, no new dependency needed
- **PATTERN**: Static methods like existing parse_document (line 13)
- **VALIDATE**:
  ```python
  # Test in Python REPL
  from backend.services.embedding_service import EmbeddingService
  hash1 = EmbeddingService.compute_text_hash("hello world")
  hash2 = EmbeddingService.compute_text_hash("hello world")
  assert hash1 == hash2
  assert len(hash1) == 64
  print(f"✓ Hash methods working: {hash1[:16]}...")
  ```

---

### Task 3: UPDATE backend/routers/ingestion.py - Add file hash to upload

**Purpose:** Compute and store file content hash during upload

- **IMPLEMENT**: Modify `upload_document()` function after line 169 (after storage upload):
  ```python
  # After: storage_client.upload(...)

  # Compute file content hash
  # Download from storage temporarily to compute hash
  try:
      storage_download = storage_client.download(storage_path)
      temp_hash_path = temp_file_path + "_hash"
      with open(temp_hash_path, "wb") as f:
          f.write(storage_download)
      file_content_hash = embedding_service.compute_file_hash(temp_hash_path)
      os.unlink(temp_hash_path)  # Clean up temp file
  except Exception as e:
      logger.warning(f"Failed to compute file hash: {e}")
      file_content_hash = None
  ```
- **UPDATE**: Modify document INSERT at line 173 to include file_content_hash:
  ```python
  doc_response = supabase.table("documents").insert({
      "user_id": current_user["id"],
      "filename": file.filename,
      "content_type": file.content_type or "application/octet-stream",
      "file_size_bytes": file_size,
      "storage_path": storage_path,
      "status": "processing",
      "chunk_count": 0,
      "file_content_hash": file_content_hash  # NEW
  }).execute()
  ```
- **GOTCHA**: Storage download requires admin client, may need error handling
- **VALIDATE**:
  ```bash
  # Upload file
  curl -X POST http://localhost:8000/ingestion/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test.md"

  # Check database for hash (via Supabase dashboard or query)
  # SELECT filename, file_content_hash FROM documents ORDER BY created_at DESC LIMIT 1;
  ```

---

### Task 4: UPDATE backend/routers/ingestion.py - Add duplicate detection

**Purpose:** Detect duplicates after parsing, before expensive chunking/embedding

- **IMPLEMENT**: Modify `process_document()` function after line 40 (after parse):
  ```python
  # After: text_content = embedding_service.parse_document(temp_file_path)

  # Compute text content hash
  text_content_hash = embedding_service.compute_text_hash(text_content)

  # Check for existing document with same text hash
  duplicate_check = supabase.table("documents")\
      .select("id, filename, created_at, chunk_count")\
      .eq("user_id", user_id)\
      .eq("text_content_hash", text_content_hash)\
      .eq("status", "completed")\
      .execute()

  if duplicate_check.data:
      # Duplicate found - skip processing
      original_doc = duplicate_check.data[0]
      logger.info(f"Duplicate detected: {filename} matches {original_doc['filename']} from {original_doc['created_at']}")

      # Update current document as duplicate
      supabase.table("documents").update({
          "status": "duplicate",
          "duplicate_of": original_doc["id"],
          "text_content_hash": text_content_hash,
          "chunk_count": original_doc["chunk_count"],
          "updated_at": "now()"
      }).eq("id", document_id).execute()

      # Clean up temp file and exit early
      if os.path.exists(temp_file_path):
          os.unlink(temp_file_path)
      return

  # Not a duplicate - update hash and continue processing
  supabase.table("documents").update({
      "text_content_hash": text_content_hash
  }).eq("id", document_id).execute()

  # Continue with existing chunking/embedding flow (line 44+)
  ```
- **PATTERN**: Follow existing error handling pattern (lines 96-108)
- **GOTCHA**: Must return early after marking duplicate to skip chunking/embedding
- **VALIDATE**:
  ```python
  # Upload test.md twice
  # First: status='completed'
  # Second: status='duplicate', duplicate_of points to first
  ```

---

### Task 5: UPDATE backend/models/document.py - Add duplicate_of field

**Purpose:** Expose duplicate relationship in API responses

- **IMPLEMENT**: Add field to DocumentResponse class at line 42:
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
      duplicate_of: Optional[str] = None  # NEW - references original if duplicate
      created_at: str
      updated_at: str
  ```
- **PATTERN**: Follow Optional[str] pattern from error_message (line 42)
- **VALIDATE**:
  ```bash
  # GET documents endpoint should return duplicate_of field
  curl http://localhost:8000/ingestion/documents \
    -H "Authorization: Bearer $TOKEN" | jq '.[0].duplicate_of'
  ```

---

### Task 6: CREATE backend/test_record_manager.py

**Purpose:** Comprehensive automated test coverage for deduplication logic

- **IMPLEMENT**: Create test file with 6 test functions (automates all scenarios):
  1. `test_hash_generation_consistency()` - Same input = same hash, verify 64-char length
  2. `test_duplicate_same_file()` - Upload same file twice via API, assert second has status='duplicate', duplicate_of=first_id
  3. `test_modified_content_reprocesses()` - Upload v1, upload v2 with different content via API, both status='completed', different hashes
  4. `test_duplicate_no_chunks_created()` - Original creates chunks, duplicate creates zero chunks (database query)
  5. `test_duplicate_different_filename_same_content()` - Upload same content with different filenames, verify duplicate detection
  6. `test_database_constraints()` - Verify FK relationship, indexes exist, status check constraint includes 'duplicate'
- **PATTERN**: Use TestClient for API calls, direct database queries for verification, TEST_EMAIL/TEST_PASSWORD from test_utils, cleanup_test_documents_and_storage before each test
- **KEY CODE**:
  ```python
  from fastapi.testclient import TestClient
  from main import app
  from test_utils import TEST_EMAIL, TEST_PASSWORD, cleanup_test_documents_and_storage
  from services.supabase_service import get_supabase_admin
  from services.embedding_service import EmbeddingService
  from io import BytesIO
  import time

  client = TestClient(app)

  def get_auth_token():
      response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
      return response.json()["access_token"]

  # Upload pattern: files = {"file": ("name.md", BytesIO(b"content"), "text/markdown")}
  # API call: client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})
  # Wait pattern: time.sleep(3) after upload for background processing
  # Database verification: supabase.table("documents").select("*").eq("id", doc_id).execute()
  # Assert duplicate: status == "duplicate" and duplicate_of == original_id
  # Assert no chunks: supabase.table("chunks").select("id").eq("document_id", duplicate_id).execute() returns []
  ```
- **VALIDATE**: `cd backend && python test_record_manager.py` - all 6 tests pass

---

## TESTING STRATEGY

**All tests are fully automated. No manual testing required for Module 3.**

### Automated Unit Tests (Backend)

**Tool:** Python TestClient + pytest patterns (matches existing test_ingestion.py)
**File:** `backend/test_record_manager.py`
**Scope:** Hash computation functions, duplicate detection logic

**Tests:**
- `test_hash_generation_consistency()` - Verifies SHA-256 hash determinism and format
- `test_hash_uniqueness()` - Different inputs produce different hashes
- `test_hash_format()` - 64-character lowercase hex string validation

**Execution:** `cd backend && python test_record_manager.py`
**Validation:** All unit tests pass with [PASS] markers

---

### Automated Integration Tests (Backend API + Database)

**Tool:** FastAPI TestClient + Supabase direct queries (real database, not mocked)
**File:** `backend/test_record_manager.py`
**Scope:** End-to-end upload → processing → duplicate detection → database state verification

**Tests:**
1. `test_duplicate_same_file()` - Upload identical file twice via API, verify second document has status='duplicate', duplicate_of references first
2. `test_modified_content_reprocesses()` - Upload file, modify content, re-upload, verify both status='completed' with different hashes
3. `test_duplicate_different_filename()` - Same content, different filenames, verify duplicate detection works
4. `test_duplicate_no_chunks_created()` - Database query confirms duplicate documents create zero chunks
5. `test_original_chunks_retrievable()` - Verify chunks accessible via duplicate_of FK relationship
6. `test_database_constraints()` - Validate migration applied correctly: columns exist, indexes created, CHECK constraint includes 'duplicate' status

**Pattern:**
```python
# API upload via TestClient
files = {"file": ("test.md", BytesIO(b"content"), "text/markdown")}
response = client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})

# Wait for background processing
time.sleep(3)

# Database verification via direct query
supabase = get_supabase_admin()
doc = supabase.table("documents").select("*").eq("id", doc_id).execute()
assert doc.data[0]["status"] == "duplicate"
assert doc.data[0]["duplicate_of"] == original_id
```

**Execution:** `cd backend && python test_record_manager.py`
**Validation:** All 6 integration tests pass

---

### Automated Frontend Tests (Optional - Future Module)

**Tool:** Playwright MCP (already used in project for frontend testing)
**Scope:** UI display of duplicate status, user experience validation
**Status:** NOT REQUIRED for Module 3 (backend-only implementation)

**If frontend updated in future:**
- Duplicate status badge displayed in document list
- "Using existing chunks" message shown for duplicates
- Clicking duplicate shows link to original document

**Pattern (from existing frontend tests):**
```typescript
// frontend/tests/e2e/duplicate-display.spec.ts
test('shows duplicate status in document list', async ({ page }) => {
  await page.goto('http://localhost:5173');
  // ... upload duplicate, verify UI shows status
});
```

---

### Manual Validation: NONE REQUIRED

**All functional validation is automated.** The following are NOT needed for Module 3 acceptance:

- ❌ **UI visual verification** - Module 3 is backend-only, no frontend changes
- ❌ **Manual curl commands** - All upload scenarios automated via TestClient
- ❌ **Manual database queries** - All database checks automated in test suite
- ❌ **Performance profiling** - Not required for initial implementation (hash computation <20ms, acceptable without tuning)

---

## VALIDATION COMMANDS

### Level 1: Migration Applied

```sql
-- Run in Supabase SQL Editor
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
AND column_name IN ('file_content_hash', 'text_content_hash', 'duplicate_of');
-- Expected: 3 rows returned

SELECT constraint_name, check_clause
FROM information_schema.check_constraints
WHERE constraint_name = 'documents_status_check';
-- Should include 'duplicate' in check clause
```

### Level 2: Backend Tests Pass

```bash
cd backend
python test_record_manager.py
# Expected: All tests pass with [PASS] markers
```

### Level 3: Integration Tests (Automated)

```bash
cd backend
python test_record_manager.py
# Expected: All 6 automated tests pass
# - test_hash_generation_consistency
# - test_duplicate_same_file (includes API upload + database verification)
# - test_modified_content_reprocesses (includes API upload + database verification)
# - test_duplicate_no_chunks_created (includes database query verification)
# - test_duplicate_different_filename_same_content
# - test_database_constraints (validates schema changes)
```

---

## ACCEPTANCE CRITERIA

- [ ] Migration 011 applied successfully (3 columns added, indexes created)
- [ ] Hash computation methods implemented and tested (SHA-256, 64-char hex)
- [ ] File hash computed and stored during upload
- [ ] Text hash computed after parsing, before chunking
- [ ] Duplicate detection query works (user_id + text_content_hash lookup)
- [ ] Duplicate documents marked with status='duplicate', duplicate_of set
- [ ] Duplicate documents skip chunking/embedding (no chunks created)
- [ ] Modified files re-process correctly (different hash = new processing)
- [ ] DocumentResponse includes duplicate_of field
- [ ] All backend tests pass (test_record_manager.py)
- [ ] Manual upload test confirms duplicate detection works
- [ ] Database constraints enforce data integrity (FK, CHECK constraint)
- [ ] RLS policies work with new columns (user isolation maintained)
- [ ] No regressions in existing ingestion flow

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully (Levels 1-4)
- [ ] Backend test suite passes (test_record_manager.py)
- [ ] Manual testing confirms feature works end-to-end
- [ ] Database migration applied without errors
- [ ] No duplicate chunks created for duplicate documents
- [ ] Acceptance criteria all met
- [ ] Code follows project conventions (RLS patterns, error handling)

---

## NOTES

**Design Decisions:**
- Two-level hashing (file + text) catches both exact duplicates and semantic duplicates across formats
- SHA-256 chosen for collision resistance and stdlib availability
- Duplicate detection happens post-upload to ensure file is stored (user can download later)
- Duplicates skip chunking/embedding but retain document record (user visibility)
- **Embedding dimensions NOT considered in duplicate detection** - same text with different dimensions still marked as duplicate (user must delete old document to re-embed with different dimensions)
- Backward compatible: existing documents without hashes continue working (nullable columns)

**Trade-offs:**
- Storage: Adds ~128 bytes per document (two 64-char hashes)
- Compute: Adds ~10-20ms per upload (hash computation + duplicate query)
- Saves: Minutes of processing time + embedding API costs for duplicates

**Future Enhancements (Not in Module 3):**
- Backfill hashes for existing documents (optional script)
- Force re-upload parameter for edge cases
- Frontend UI showing duplicate status and original file link
- Delete duplicate files from storage to save space (currently kept for user download)
