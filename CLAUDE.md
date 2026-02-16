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

### Supabase Query Patterns

**`.single()` Exception Handling:**

The `.single()` method throws an exception when no rows are found, rather than returning `null`. This affects error handling in API endpoints.

```python
# ❌ Bad - will never reach the if statement
result = supabase.table("documents").select("*").eq("id", doc_id).single().execute()
if not result.data:  # Never reached if no rows
    raise HTTPException(status_code=404)

# ✅ Good - catch exception and check error message
try:
    result = supabase.table("documents").select("*").eq("id", doc_id).single().execute()
    # Process result.data
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    error_msg = str(e).lower()
    if "no rows" in error_msg or "not found" in error_msg or "single" in error_msg:
        raise HTTPException(status_code=404, detail="Document not found")
    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

**When to use `.single()` vs `.execute()`:**
- Use `.single()` when expecting exactly one result (e.g., fetch by ID)
- Use `.execute()` when expecting zero or more results (e.g., list queries)
- Always wrap `.single()` in try/except for proper error handling

## Configuration Management

### Pydantic Settings Environment Variables

This project uses `pydantic-settings` for configuration. **Environment variables override code defaults.**

**Priority:** `.env` file > `config.py` default values

**Implications:**
- Adding/changing `Settings` class fields in `config.py` may not take effect if `.env` overrides them
- `.env` files are not tracked in git - can't be read during planning phase
- User must manually update `.env` for configuration changes to take effect

**Best Practice:**
- Use `config.py` for sensible defaults that work for most users
- Document user-configurable settings in README or setup guide
- When modifying `Settings` class, check if `.env` might override your changes
- If changing shared config (like `SUPPORTED_FILE_TYPES`), note potential `.env` dependency

**Example:**
```python
# In config.py
class Settings(BaseSettings):
    SUPPORTED_FILE_TYPES: str = "pdf,docx,pptx,html,md,txt,csv,json,xml,rtf"  # Default
```

```bash
# In .env (if present, this OVERRIDES config.py default)
SUPPORTED_FILE_TYPES="pdf,docx,html,md,txt"  # User's custom value
```

**When updating configuration:**
1. Update `config.py` default value
2. Check if `.env` has override: `grep "SETTING_NAME" backend/.env`
3. If override exists, document that user needs to update `.env` manually
4. For shared configs, consider adding sync comments between files

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

## Streaming Response Patterns

### Extending Stream Metadata

When adding new metadata to streaming responses (e.g., sources, subagent_metadata):

1. **Use tuple expansion:** Extend existing tuple pattern rather than creating new channels
   - Example: `(delta, sources)` → `(delta, sources, metadata)`
2. **Update all unpacking sites:** Search for all locations that unpack the stream yield
   - Router unpacking: `async for delta, sources, metadata in stream_response(...)`
   - Test unpacking: Update all test assertions that consume streams
3. **Document as breaking change:** Note in plan that signature change affects dependent code
4. **Consider alternatives for frequent expansion:** If stream yields grow beyond 3-4 values, migrate to:
   - Named tuple: `StreamChunk(delta="...", sources=[], metadata=None)`
   - Dataclass: `@dataclass class StreamChunk: delta: str; sources: List; metadata: Optional[Dict]`

**Why tuples work for 2-3 values:**
- Simple and performant
- Easy to unpack inline
- Clear contract for consumers

**When to use named types:**
- More than 3 values in tuple
- Frequent additions expected
- Complex nested metadata structures

## Pre-Execution Test Audit

Before implementing features, verify test suite health to avoid discovering broken tests mid-execution.

**Process:**

1. **Run full test suite before starting implementation:**
   ```bash
   # Backend
   cd backend && venv/Scripts/python -m pytest

   # Frontend
   cd frontend && npm test
   ```

2. **Document test status in plan:**
   - Which tests are passing (baseline)
   - Which tests are broken (pre-existing)
   - Which tests are skipped (intentional)

3. **Decide on broken tests:**
   - Fix before implementation (if blocking)
   - Fix during implementation (if related to feature)
   - Document as known issue (if unrelated)

**Benefits:**
- Clear baseline of what works before changes
- Prevents confusion about what broke during implementation
- Allows proactive fixing of related broken tests
- Enables accurate regression detection

**Example plan section:**
```markdown
## Pre-Implementation Test Status

**Backend Tests:** 15/17 passing
- ✅ test_provider_service.py (9/9)
- ✅ test_subagent_service.py (3/3)
- ❌ test_rag_tool_calling.py (0/2) - BROKEN: outdated imports from Module 2
- ⚠️ test_auth.py (3/3) - SKIPPED: requires manual browser

**Frontend Tests:** 12/12 passing

**Decision:** Fix test_rag_tool_calling.py during implementation (related to tool calling)
```

## Team-Based Execution Best Practices

When using parallel agents for feature implementation:

### Wave-Based Dependency Management

1. **Define clear interface contracts between waves:**
   - What outputs Wave N provides
   - What inputs Wave N+1 requires
   - Example: "Task 1.2 provides `read_full_document(doc_id, user_id) -> str`"

2. **Use WAVE annotations in task descriptions:**
   - Mark each task with its wave number: `WAVE: 1`, `WAVE: 2`
   - Enables parallel execution within waves, sequential between waves

3. **Prefer named parameters over positional tuples for cross-agent APIs:**
   - Better: `StreamChunk(delta=..., sources=[], metadata=None)`
   - Worse: `(delta, sources, metadata)` (brittle when expanding)

### Migration Coordination

4. **Reserve migration number ranges for parallel modules:**
   - When multiple features in development simultaneously
   - Example: Module 7 uses 014-019, Module 8 uses 020-025
   - Prevents renumbering after merge conflicts

### Performance Metrics

5. **Expected efficiency gains from parallelization:**
   - 2-agent wave: ~2x speedup vs sequential
   - 3-agent wave: ~3x speedup vs sequential
   - Coordination overhead: typically <10% time cost
   - Net gain: 30-50% total time reduction for 4+ wave projects

## Progress
Check PROGRESS.md for current module status. Update it as you complete requests.