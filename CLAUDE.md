# CLAUDE.md

RAG app with chat (default) and document ingestion interfaces. Config via env vars, no admin UI.

## Stack
- Frontend: React + Vite + Tailwind + shadcn/ui
- Backend: Python + FastAPI
- Database: Supabase (Postgres, pgvector, Auth, Storage, Realtime)
- LLM: OpenAI (Module 1), OpenRouter (Module 2+)
- Observability: LangSmith

## Rules
- Python backend must use a `venv` virtual environment
- No LangChain, no LangGraph - raw SDK calls only
- Use Pydantic for structured LLM outputs
- All tables need Row-Level Security - users only see their own data
- Stream chat responses via SSE
- Use Supabase Realtime for ingestion status updates
- Module 2+ uses stateless completions - store and send chat history yourself
- Ingestion is manual file upload only - no connectors or automated pipelines

## Planning
- Save all plans to `.agents/plans/` folder
- Naming convention: `{sequence}.{plan-name}.md` (e.g., `1.auth-setup.md`, `2.document-ingestion.md`)
- Plans should be detailed enough to execute without ambiguity
- Each task in the plan must include at least one validation test to verify it works
- Assess complexity and single-pass feasibility - can an agent realistically complete this in one go?
- Include a complexity indicator at the top of each plan:
  - ✅ **Simple** - Single-pass executable, low risk
  - ⚠️ **Medium** - May need iteration, some complexity
  - 🔴 **Complex** - Break into sub-plans before executing

## Development Flow
1. **Plan** - Create a detailed plan and save it to `.agents/plans/`
2. **Build** - Execute the plan to implement the feature
3. **Validate** - Test and verify the implementation works correctly. Use browser testing where applicable via an appropriate MCP
4. **Iterate** - Fix any issues found during validation

This account is pre-created in Supabase for validation and testing purposes.

## Backend Logging Standards

**Production Code Logging Rules:**
- ❌ **Never use `print()` statements** in production code (backend routers, services, models)
- ✅ **Errors in database fields:** Capture error messages in `error_message` columns for debugging
- ✅ **Critical failures only:** Use logging framework (not print) if stderr logging needed
- ✅ **Test files exception:** Debug output allowed in test files (test_*.py)

**Rationale:**
- Production logs should be silent by default (noise-free monitoring)
- Errors traceable via database queries (SELECT * FROM documents WHERE status = 'failed')
- Debug output only during development/testing

**Examples:**
```python
# ❌ Bad - verbose production logging
print(f"Processing document {doc_id}")
print(f"Generated {len(chunks)} chunks")

# ✅ Good - silent production, error capture
try:
    process_document(doc_id)
except Exception as e:
    db.update({"status": "failed", "error_message": str(e)})

# ✅ Good - test debug output is fine
def test_feature():
    print(f"Testing scenario: {scenario_name}")
```

**Validation:**
- Before finalizing: `grep -r "print(" backend/routers backend/services backend/models`
- Should return zero results (excluding test files)

## Infrastructure Behavior Notes

### Supabase Storage
- **Path Uniqueness:** Storage paths must be unique. Uploading to existing path returns 400 "Duplicate" error
- **Workaround for tests:** Use different filenames or cleanup before re-upload
- **Pattern:** `storage_path = f"{user_id}/{unique_filename}"`

### Supabase Realtime
- **Status updates:** Use for ingestion status changes (processing → completed/failed/duplicate)
- **Subscription pattern:** Subscribe to table changes filtered by user_id for RLS compliance

### pgvector
- **No IVFFlat index:** Variable dimensions support (Module 2) - index deferred for flexibility
- **Cosine similarity:** Default distance metric for document retrieval

## Cross-Platform Compatibility

### Character Encoding (Test Output)
- **Windows limitation:** Terminal uses 'charmap' codec (limited Unicode support)
- **Rule:** Use ASCII characters in test output, avoid Unicode symbols
- **Examples:**
  - ✅ Good: `+` for success, `-` for failure, `!` for warning
  - ❌ Bad: `✓`, `✗`, `⚠️` (fail on Windows)

### Path Separators
- **Rule:** Use `os.path.join()` or `pathlib.Path` for cross-platform paths
- ❌ Bad: `f"uploads/{user_id}/{filename}"` (hardcoded slashes)
- ✅ Good: `Path("uploads") / user_id / filename`

### Target Platforms
- Primary: Windows (development), Linux (production)
- Testing: Ensure tests pass on Windows with MINGW64/Git Bash

## Progress
Check PROGRESS.md for current module status. Update it as you complete requests.