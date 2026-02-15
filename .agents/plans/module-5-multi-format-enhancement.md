# Feature: Module 5 - Multi-Format Support Enhancement

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution (console.log, print, etc.) that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes - no git operations

Validate documentation and codebase patterns before implementing. Pay attention to naming of existing utils, types, and models. Import from correct files.

## Feature Description

Enhance the RAG document ingestion system with two improvements:
1. **Fix redundant cascade delete** - Remove manual chunk deletion that's already handled by database constraints
2. **Expand file format support** - Add PPTX, CSV, JSON, XML, RTF to existing PDF/DOCX/HTML/MD/TXT support

**User Value:** Support more document types (presentations, structured data, configuration files) with cleaner, faster code.

## User Story

As a RAG application user
I want to upload more document types including presentations and structured data files
So that I can retrieve information from all my important documents, not just PDFs and Word files

## Problem Statement

**Current Limitations:**

1. **Redundant Code:** The delete endpoint manually deletes chunks (lines 417-420 in `ingestion.py`) even though the database has `ON DELETE CASCADE` configured (migration 006, line 19). This means:
   - Two database queries instead of one
   - Slower deletions
   - More code to maintain
   - No tests validating cascade behavior

2. **Limited Formats:** Only 5 formats supported (PDF, DOCX, HTML, MD, TXT) despite Docling 0.4.0 supporting 15+ formats natively:
   - No presentations (PPTX)
   - No structured data (CSV, JSON)
   - No markup/config files (XML, RTF)
   - Format lists hardcoded separately in frontend and backend (risk of drift)

## Solution Statement

**Part 1: Cascade Delete Fix (4 lines removed)**
- Remove lines 417-420 in `backend/routers/ingestion.py`
- Update comment to clarify reliance on database cascade
- Add test to validate cascade behavior

**Part 2: Format Expansion (5 new formats)**

Add support for:
- **PPTX** (PowerPoint) - via Docling (extracts slide text and speaker notes)
- **CSV** (data files) - via Docling (converts to markdown tables)
- **JSON** (structured data) - direct read as text (LLM understands JSON natively)
- **XML** (markup) - via Docling (handles USPTO, JATS, generic schemas)
- **RTF** (rich text) - direct read as text (RTF tags visible but readable)

**Approach:**
- Simple formats (JSON, RTF) read directly like TXT/MD/HTML
- Complex formats (PPTX, CSV, XML) route through Docling like PDF/DOCX
- Use standard character-based chunking for all formats
- Update both frontend and backend configuration

## Feature Metadata

**Feature Type**: Enhancement (Code cleanup + New capability)
**Complexity**: Low
**Primary Systems Affected**: Ingestion pipeline, file validation, testing
**Dependencies**: Docling 0.4.0 (existing), no new dependencies
**Breaking Changes**: No (additive only)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ BEFORE IMPLEMENTING

**Deletion Logic:**
- `backend/routers/ingestion.py` (lines 388-440) - Delete endpoint with manual chunk deletion to remove
- `supabase/migrations/006_documents_and_chunks.sql` (line 19) - ON DELETE CASCADE configuration

**File Format Support:**
- `backend/services/embedding_service.py` (lines 12-52) - Parsing logic, two-tier approach (simple vs Docling)
- `backend/config.py` (line 41) - SUPPORTED_FILE_TYPES configuration string
- `frontend/src/components/Ingestion/DocumentUpload.tsx` (lines 9-16) - Frontend validation arrays
- `backend/requirements.txt` (line 13) - Docling version: 0.4.0

**Testing Patterns:**
- `backend/test_ingestion.py` - Existing tests (markdown, unsupported type, oversized file)
- `backend/test_utils.py` (line 41) - Cleanup utility that relies on cascade
- `backend/test_record_manager.py` - Patterns for upload-wait-verify-cleanup flow

### New Files to Create

- None (all changes to existing files)

### Patterns to Follow

**Two-Tier Parsing Pattern** (embedding_service.py):
```python
# Simple formats - read directly
if file_ext in ['.txt', '.md', '.html']:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Complex formats - use Docling
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert(file_path)
text_content = result.document.export_to_markdown()
return text_content
```

**Test Pattern** (test_ingestion.py):
```python
def test_upload_FORMAT_file():
    token = get_auth_token()
    timestamp = int(time.time() * 1000)
    filename = f"test_FORMAT_{timestamp}.ext"

    content = b"..."  # Format-specific content

    files = {"file": (filename, BytesIO(content), "mime/type")}
    response = client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    print(f"\n[TEST PASSED] Successfully uploaded FORMAT file: {filename}")
```

**RLS Pattern** (always scope by user_id):
```python
.eq("user_id", current_user["id"])
```

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌─────────────────────────────────────────────┐
│ WAVE 1: Code Changes (Parallel)             │
├─────────────────────────────────────────────┤
│ Task 1.1: Fix Cascade Delete                │
│ Task 1.2: Add JSON/RTF to Simple Formats    │
│ Task 1.3: Update Backend Config             │
│ Task 1.4: Update Frontend Config            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ WAVE 2: Testing (After Wave 1)              │
├─────────────────────────────────────────────┤
│ Task 2.1: Add Format Tests                  │
│ Task 2.2: Add Cascade Delete Test           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ WAVE 3: Validation (Sequential)             │
├─────────────────────────────────────────────┤
│ Task 3.1: Run All Tests                     │
│ Task 3.2: Manual Format Testing             │
└─────────────────────────────────────────────┘
```

### Parallelization Summary

**Wave 1 - Fully Parallel:** Tasks 1.1-1.4 can all execute simultaneously (different files, no dependencies)
**Wave 2 - Parallel after Wave 1:** Tasks 2.1-2.2 need Wave 1 code but can run together
**Wave 3 - Sequential:** Validation must run after all changes complete

### Synchronization Checkpoints

**After Wave 1:** Verify all config files updated, cascade delete code removed
**After Wave 2:** Run `python test_ingestion.py` - all tests pass
**Final:** Manual upload test for each new format

---

## STEP-BY-STEP TASKS

### WAVE 1: Code Changes (All Parallel)

#### Task 1.1: Fix Cascade Delete

- **WAVE**: 1
- **AGENT_ROLE**: backend-cleanup
- **DEPENDS_ON**: []
- **BLOCKS**: [Task 2.2]
- **PROVIDES**: Clean delete endpoint relying on database cascade
- **IMPLEMENT**:
  1. Open `backend/routers/ingestion.py`
  2. Remove lines 417-420 (manual chunk deletion with try/except)
  3. Update comment on line 415 from "Delete chunks (will cascade due to foreign key)" to "Chunks cascade deleted automatically via ON DELETE CASCADE constraint (migration 006, line 19)"
  4. Verify storage cleanup (lines 433-438) still happens
- **PATTERN**: See `backend/test_utils.py` line 41 - comment shows cascade pattern
- **VALIDATE**: Code compiles, no syntax errors
- **RATIONALE**: Database handles cascade automatically - simpler, faster, fewer failure points

#### Task 1.2: Add JSON/RTF to Simple Formats

- **WAVE**: 1
- **AGENT_ROLE**: backend-parsing
- **DEPENDS_ON**: []
- **BLOCKS**: [Task 2.1]
- **PROVIDES**: JSON and RTF files read as plain text
- **IMPLEMENT**:
  1. Open `backend/services/embedding_service.py`
  2. Update line 33 condition from `if file_ext in ['.txt', '.md', '.html']:` to `if file_ext in ['.txt', '.md', '.html', '.json', '.rtf']:`
  3. No other changes needed - Docling already handles PPTX, CSV, XML
- **PATTERN**: Follows existing two-tier parsing approach (lines 32-49)
- **VALIDATE**: Code compiles, imports work
- **RATIONALE**: JSON and RTF are text-based, simpler to read directly

#### Task 1.3: Update Backend Config

- **WAVE**: 1
- **AGENT_ROLE**: backend-config
- **DEPENDS_ON**: []
- **BLOCKS**: [Task 2.1]
- **PROVIDES**: Backend accepts new file formats
- **IMPLEMENT**:
  1. Open `backend/config.py`
  2. Update line 41 from `SUPPORTED_FILE_TYPES: str = "pdf,docx,html,md,txt"` to `SUPPORTED_FILE_TYPES: str = "pdf,docx,pptx,html,md,txt,csv,json,xml,rtf"`
  3. Add comment above line 41: `# IMPORTANT: Keep in sync with frontend/src/components/Ingestion/DocumentUpload.tsx SUPPORTED_TYPES`
- **PATTERN**: Comma-separated string without dots (parsed dynamically in ingestion.py lines 149-163)
- **VALIDATE**: String format correct (no dots, commas separate)
- **RATIONALE**: Centralized configuration, parsed at runtime

#### Task 1.4: Update Frontend Config

- **WAVE**: 1
- **AGENT_ROLE**: frontend-validation
- **DEPENDS_ON**: []
- **BLOCKS**: [Task 2.1]
- **PROVIDES**: Frontend accepts and validates new file formats
- **IMPLEMENT**:
  1. Open `frontend/src/components/Ingestion/DocumentUpload.tsx`
  2. Update line 9 from `const SUPPORTED_TYPES = ['.pdf', '.docx', '.txt', '.html', '.md'];` to:
     ```typescript
     // IMPORTANT: Keep in sync with backend/config.py SUPPORTED_FILE_TYPES
     const SUPPORTED_TYPES = ['.pdf', '.docx', '.pptx', '.txt', '.html', '.md', '.csv', '.json', '.xml', '.rtf'];
     ```
  3. Update lines 10-16 SUPPORTED_MIME_TYPES array to add:
     ```typescript
     'application/vnd.openxmlformats-officedocument.presentationml.presentation',  // PPTX
     'text/csv',
     'application/json',
     'application/xml',
     'text/xml',
     'application/rtf',
     'text/rtf'
     ```
- **PATTERN**: Follows existing validation pattern (lines 29-48)
- **VALIDATE**: TypeScript compiles, no syntax errors
- **RATIONALE**: Client-side validation provides immediate user feedback

**Wave 1 Checkpoint:** All config files updated, cascade delete removed, parsing logic enhanced

---

### WAVE 2: Testing (Parallel after Wave 1)

#### Task 2.1: Add Format Tests

- **WAVE**: 2
- **AGENT_ROLE**: test-writer
- **DEPENDS_ON**: [Task 1.2, 1.3, 1.4]
- **BLOCKS**: [Task 3.1]
- **PROVIDES**: Test coverage for all new formats
- **IMPLEMENT**: Add 5 test functions to `backend/test_ingestion.py`:

Add 5 test functions following the pattern from `test_upload_markdown_file()`:

**Format Test Template:**
```python
def test_upload_FORMAT_file():
    token = get_auth_token()
    timestamp = int(time.time() * 1000)
    content = b"FORMAT_SPECIFIC_CONTENT"  # See examples below
    files = {"file": (f"test_{timestamp}.ext", BytesIO(content), "mime/type")}
    response = client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

**Test Content Examples:**
- **PPTX**: `create_minimal_pptx_bytes()` helper or use python-pptx library
- **CSV**: `b"name,age\nAlice,30\nBob,25"`
- **JSON**: `b'{"service":"api","version":"1.0.0"}'`
- **XML**: `b'<?xml version="1.0"?><doc><title>Test</title></doc>'`
- **RTF**: `b'{\\rtf1\\ansi{\\b Bold} text.}'`

- **VALIDATE**: `cd backend && python test_ingestion.py` - all 5 new tests pass

#### Task 2.2: Add Cascade Delete Test

- **WAVE**: 2
- **AGENT_ROLE**: test-writer
- **DEPENDS_ON**: [Task 1.1]
- **BLOCKS**: [Task 3.1]
- **PROVIDES**: Validation that cascade delete works correctly
- **IMPLEMENT**: Add test function to `backend/test_ingestion.py`:

```python
def test_delete_document_cascade():
    """Test that deleting a document cascades to delete chunks automatically."""
    token = get_auth_token()
    timestamp = int(time.time() * 1000)

    # Upload document with content to create chunks
    md_content = b"# Test\n\n" + b"Lorem ipsum. " * 200  # Enough for multiple chunks
    files = {"file": (f"test_{timestamp}.md", BytesIO(md_content), "text/markdown")}
    response = client.post("/ingestion/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    doc_id = response.json()["id"]

    time.sleep(3)  # Wait for processing

    # Verify chunks exist
    chunks = client.get(f"/ingestion/documents/{doc_id}/chunks", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(chunks) > 0, "Should have chunks before deletion"

    # Delete document
    client.delete(f"/ingestion/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})

    # Verify chunks cascade deleted
    chunks_after = client.get(f"/ingestion/documents/{doc_id}/chunks", headers={"Authorization": f"Bearer {token}"})
    assert chunks_after.status_code == 404, "Chunks should cascade delete"
```

- **PATTERN**: Follow upload-wait-verify pattern from `test_record_manager.py` (lines 63-117)
- **VALIDATE**: `cd backend && python test_ingestion.py` - cascade test passes
- **INTEGRATION_TEST**: Verifies database constraint works as expected

**Wave 2 Checkpoint:** Run `cd backend && python test_ingestion.py` - all tests pass including new format tests and cascade test

---

### WAVE 3: Validation (Sequential)

#### Task 3.1: Run All Tests

- **WAVE**: 3
- **AGENT_ROLE**: validation
- **DEPENDS_ON**: [Task 2.1, 2.2]
- **BLOCKS**: []
- **PROVIDES**: Confidence all changes work correctly
- **IMPLEMENT**:
  1. Run backend tests: `cd backend && python test_ingestion.py`
  2. Verify all tests pass (existing + new format tests + cascade test)
  3. Run other backend tests if they exist (test_record_manager.py, etc.)
- **VALIDATE**: All tests pass with no errors
- **EXPECTED**: 8+ tests passing (3 existing + 5 new formats + 1 cascade)

#### Task 3.2: Manual Format Testing (Optional)

- **WAVE**: 3
- **AGENT_ROLE**: validation
- **DEPENDS_ON**: [Task 3.1]
- **BLOCKS**: []
- **PROVIDES**: Real-world validation of parsing quality
- **IMPLEMENT**:
  1. Start backend: `cd backend && venv/Scripts/python -m uvicorn main:app --reload`
  2. Start frontend: `cd frontend && npm run dev`
  3. Login to app
  4. Navigate to ingestion page
  5. Upload one file of each new format (PPTX, CSV, JSON, XML, RTF)
  6. Verify each file processes to "completed" status
  7. Click on document to view chunks
  8. Verify chunks contain readable text from the document
- **VALIDATE**: All formats parse successfully, chunks are readable
- **NOTE**: This is optional - automated tests provide sufficient coverage

**Final Checkpoint:** All validation complete, ready for user review

---

## TESTING STRATEGY

**⚠️ CRITICAL: Plan for MAXIMUM test automation**

### Test Automation Requirements

**Total Tests:** 9 tests
- ✅ **Automated:** 9 (100%)
  - Existing: 3 (markdown upload, unsupported type, oversized file)
  - New formats: 5 (PPTX, CSV, JSON, XML, RTF)
  - Cascade delete: 1

### Unit Tests

**Automation:** ✅ Fully Automated
**Tool:** Python unittest with FastAPI TestClient
**Location:** `backend/test_ingestion.py`
**Execution:** `cd backend && python test_ingestion.py`

Tests to add:
- `test_upload_pptx_file()` - Upload PPTX, verify 200 response
- `test_upload_csv_file()` - Upload CSV, verify 200 response
- `test_upload_json_file()` - Upload JSON, verify 200 response
- `test_upload_xml_file()` - Upload XML, verify 200 response
- `test_upload_rtf_file()` - Upload RTF, verify 200 response
- `test_delete_document_cascade()` - Delete doc, verify chunks cascade deleted

### Integration Tests

**Automation:** ✅ Fully Automated
**Tool:** FastAPI TestClient with Supabase database queries
**Location:** `backend/test_ingestion.py` (cascade test)
**Execution:** `cd backend && python test_ingestion.py`

The cascade delete test validates:
- Document upload creates chunks
- Document deletion removes document record
- Chunks are automatically deleted (cascade)
- GET chunks endpoint returns 404 after deletion

### End-to-End Tests

**Automation:** ⚠️ Manual - browser testing not automated in current setup
**Why Manual:** No browser automation MCP configured for this project
**Frequency:** Optional, run if automated tests insufficient
**Steps:**
1. Start servers (backend + frontend)
2. Upload each new format via UI
3. Verify parsing produces readable chunks
4. Delete a document
5. Verify chunks removed

**Time:** ~10 minutes for manual E2E testing of all 5 formats

### Test Automation Summary

**Total Tests:** 9
- ✅ **Automated:** 9 (100%)
  - Format uploads: 6 via Python unittest
  - Cascade delete: 1 via Python unittest
  - Existing tests: 3 maintained
- ⚠️ **Manual:** 0 (0%) - E2E testing optional only

**Goal:** 100% automated coverage ✅ Achieved

**Execution Agent Instructions:**
- CREATE all 6 new test functions during implementation
- RUN automated tests after each wave: `python test_ingestion.py`
- VERIFY all tests pass before marking tasks complete
- DOCUMENT test results in execution summary

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% correctness.

### Level 1: Backend Tests

```bash
cd backend
python test_ingestion.py
```

**Expected:** All tests pass (9+ total: 3 existing + 5 new formats + 1 cascade)
**If Failed:** Review errors, fix implementation, re-run

### Level 2: Format Configuration Sync

```bash
# Verify backend config
cd backend
grep "SUPPORTED_FILE_TYPES" config.py

# Verify frontend config
cd ../frontend
grep "SUPPORTED_TYPES" src/components/Ingestion/DocumentUpload.tsx
```

**Expected:** Both show 10 formats: pdf, docx, pptx, html, md, txt, csv, json, xml, rtf
**If Failed:** Update missing file to match

### Level 3: Code Review

```bash
# Verify cascade delete fix
cd backend
grep -A5 "Delete chunks" routers/ingestion.py
```

**Expected:** Should see comment about cascade, NO manual chunk deletion code
**If Failed:** Remove manual deletion code (lines 417-420)

### Level 4: Manual Upload Test (Optional)

```bash
# Start backend
cd backend
venv/Scripts/python -m uvicorn main:app --reload

# In new terminal, start frontend
cd frontend
npm run dev
```

**Steps:**
1. Open http://localhost:5173
2. Login with test credentials
3. Navigate to ingestion page
4. Upload test file for each new format
5. Verify "completed" status
6. View chunks - verify readable text

**Expected:** All formats process successfully
**If Failed:** Check backend logs for parsing errors

---

## ACCEPTANCE CRITERIA

- [ ] **Code Changes:**
  - [ ] Manual chunk deletion removed (lines 417-420 deleted)
  - [ ] Comment updated to reference cascade behavior
  - [ ] JSON and RTF added to simple formats list
  - [ ] Backend config updated with 10 formats
  - [ ] Frontend config updated with 10 formats + MIME types
  - [ ] Sync comments added to both config files
- [ ] **Testing:**
  - [ ] 5 new format tests added (PPTX, CSV, JSON, XML, RTF)
  - [ ] Cascade delete test added
  - [ ] All 9+ tests passing
- [ ] **Validation:**
  - [ ] Backend tests pass: `python test_ingestion.py`
  - [ ] Config files in sync (10 formats both places)
  - [ ] No manual chunk deletion in delete endpoint
  - [ ] Optional: Manual upload test successful
- [ ] **Code Quality:**
  - [ ] No regressions (existing tests still pass)
  - [ ] Code follows project conventions
  - [ ] No print statements added (logging rules followed)
  - [ ] Comments clear and accurate

---

## COMPLETION CHECKLIST

- [ ] All Wave 1 tasks completed (4 code changes)
- [ ] All Wave 2 tasks completed (6 tests added)
- [ ] All Wave 3 validation passed
- [ ] Level 1-3 validation commands executed and passed
- [ ] Test suite passes (9+ tests, 100% pass rate)
- [ ] No linting/import errors
- [ ] Config files synchronized (10 formats)
- [ ] Manual cascade delete code removed
- [ ] Storage cleanup preserved in delete endpoint
- [ ] **⚠️ Debug logs added during execution REMOVED (keep pre-existing logs only)**
- [ ] **⚠️ CRITICAL: Changes left UNSTAGED (NOT committed) for user review**

---

## NOTES

**Format Support:**
- Simple (direct read): TXT, MD, HTML, JSON, RTF
- Docling (DocumentConverter): PDF, DOCX, PPTX, CSV, XML
- Docling 0.4.0 extracts all to Markdown via `export_to_markdown()`

**Key Decisions:**
- Remove manual chunk deletion → Database cascade handles it (migration 006:19)
- 5 new formats → PPTX (presentations), CSV (data), JSON/XML (structured), RTF (rich text)
- Keep frontend/backend configs separate → MIME types vs extensions, add sync comments
- Standard chunking for all → Format-specific chunking deferred to future

**Performance:**
- Deletion: 2 queries → 1 query (~50% faster)
- Parsing: JSON/RTF fastest (direct read), PPTX/CSV/XML moderate (Docling)

**Security:**
- Extension + MIME validation maintained
- No executable formats
- RLS enforced, cascade only affects user's own data
- 10MB file size limit unchanged

**Module 4 Compatibility:**
Module 5 is **fully compatible** with Module 4 (Metadata Extraction) - no conflicts or extra changes needed after merge:
- Module 4 modifies `process_document()` for metadata extraction
- Module 5 modifies `delete_document()` for cascade fix
- Different functions, zero overlap
- Module 4's migration 012 doesn't conflict with Module 5 (no migrations)
- **Bonus:** After both merge, metadata extraction will automatically work on Module 5's new formats (PPTX, CSV, JSON, XML, RTF) without any code changes - validates metadata extraction works across all formats
