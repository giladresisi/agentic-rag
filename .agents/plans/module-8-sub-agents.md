# Feature: Module 8 - Sub-Agents with Isolated Context

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution (console.log, print, etc.) that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes - no git operations

Validate documentation and codebase patterns before implementing. Pay attention to naming of existing utils, types, and models. Import from correct files.

## Feature Description

Implement hierarchical agent delegation where the main chat agent can spawn isolated sub-agents for complex document analysis tasks. Sub-agents operate with their own tool sets and context windows, preventing main conversation pollution while handling specialized work like full-document summarization or deep analysis.

## User Story

As a user analyzing documents in my RAG system
I want the chat agent to delegate complex document tasks to specialized sub-agents
So that I can get detailed analysis without overwhelming the main conversation context

## Problem Statement

Current RAG implementation uses chunked retrieval, which is excellent for semantic search but has limitations:
- Full document context not available to LLM (only 5 chunks at a time)
- Complex document analysis tasks pollute main conversation history
- No visibility into intermediate reasoning steps
- Cannot perform hierarchical task decomposition

## Solution Statement

Introduce sub-agent architecture where:
1. Main agent detects full-document scenarios via pattern recognition
2. Main agent calls `analyze_document_with_subagent` tool with task and document
3. Backend spawns isolated sub-agent with:
   - Own conversation context (prevents main thread pollution)
   - Specialized tools (`read_full_document`)
   - Recursion depth tracking (prevent infinite nesting)
4. Sub-agent performs analysis, streams reasoning
5. Final result returned to main agent and user
6. UI displays sub-agent work in expandable sections

## Feature Metadata

**Feature Type**: New Capability
**Complexity**: High
**Primary Systems Affected**: Backend chat service, frontend message display, database schema
**Dependencies**: OpenAI SDK (existing), Supabase (existing)
**Breaking Changes**: No - additive changes only

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ BEFORE IMPLEMENTING

- `backend/services/chat_service.py` (lines 26-261) - Tool calling pattern
- `backend/routers/chat.py` (lines 212-329) - SSE streaming, message persistence
- `backend/services/embedding_service.py` (lines 13-52) - Document parsing logic
- `backend/models/message.py` (lines 32-40) - MessageResponse model to extend
- `frontend/src/components/Chat/MessageList.tsx` (lines 44-61) - Sources display pattern
- `frontend/src/types/chat.ts` (lines 18-25) - Message interface to extend

### New Files to Create

- `backend/services/subagent_service.py`, `backend/services/document_service.py`, `backend/models/subagent.py`
- `frontend/src/components/Chat/SubAgentSection.tsx`, `frontend/src/types/subagent.ts`
- `backend/test_subagent_service.py`, `backend/test_subagent_integration.py`
- `supabase/migrations/014_subagent_support.sql`

### Patterns to Follow

**Naming:** Services: `{domain}_service`, Models: Pydantic BaseModel, Types: PascalCase
**Error Handling:** HTTPException, graceful degradation, clear error messages
**Logging:** NO print() in production, errors in DB fields, LangSmith tracing
**Database RLS:** Filter by user_id, use `get_supabase_admin()` with app-level RLS

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌─────────────────────────────────────────────┐
│ WAVE 1: Foundation (Parallel)               │
├─────────────────────────────────────────────┤
│ Task 1.1: Database     │ Task 1.2: Backend  │
│ Schema (Migration)     │ Document Service   │
│ Agent: db-specialist   │ Agent: backend-dev │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ WAVE 2: Core Backend (After Wave 1)         │
├─────────────────────────────────────────────┤
│ Task 2.1: Sub-agent Service                 │
│ Agent: backend-dev                          │
│ Deps: 1.1, 1.2                              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ WAVE 3: Integration (After Wave 2)          │
├─────────────────────────────────────────────┤
│ Task 3.1: Chat Service │ Task 3.2: Frontend │
│ Tool Integration       │ UI Components      │
│ Agent: backend-dev     │ Agent: frontend    │
│ Deps: 2.1              │ Deps: None         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ WAVE 4: Final Integration (Sequential)      │
├─────────────────────────────────────────────┤
│ Task 4.1: Wire Backend + Frontend           │
│ Agent: full-stack                           │
│ Deps: 3.1, 3.2                              │
└─────────────────────────────────────────────┘
```

### Parallelization Summary

**Wave 1 - Fully Parallel:** Database schema (1.1) and Document service (1.2) have no dependencies
**Wave 2 - Sequential:** Sub-agent service needs both schema and document service
**Wave 3 - Parallel after Wave 2:** Backend tool integration and Frontend UI independent
**Wave 4 - Sequential:** Final wiring requires all pieces

### Interface Contracts

**Contract 1:** Task 1.1 (Database) provides → Task 2.1 (Sub-agent Service) consumes
- Schema: `messages.subagent_metadata JSONB` field
- Fields: `task_description`, `document_id`, `document_name`, `status`, `result`

**Contract 2:** Task 1.2 (Document Service) provides → Task 2.1 (Sub-agent Service) consumes
- Function: `read_full_document(document_id, user_id) -> str`
- Returns: Full document text content (parsed)

**Contract 3:** Task 2.1 (Sub-agent Service) provides → Task 3.1 (Chat Service) consumes
- Function: `execute_subagent(task, document_id, user_id) -> SubAgentResult`
- Returns: `{status, result, reasoning_steps, error}`

**Contract 4:** Task 3.1 (Backend) provides → Task 3.2 (Frontend) consumes
- SSE Event: `{"type": "subagent_update", "data": {...}}`
- Message field: `subagent_metadata` in MessageResponse

### Synchronization Checkpoints

**After Wave 1:** Verify database migration applied, document service reads storage correctly
```bash
# Database: SELECT column_name FROM information_schema.columns WHERE table_name='messages' AND column_name='subagent_metadata';
# Document service: python -c "from services.document_service import read_full_document; print('OK')"
```

**After Wave 2:** Verify sub-agent service executes without errors
```bash
cd backend && venv/Scripts/python -m pytest test_subagent_service.py -v
```

**After Wave 3:** Verify backend streams events, frontend renders UI
```bash
cd backend && venv/Scripts/python -m pytest test_subagent_integration.py -v
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation & Storage Access

**CRITICAL: Database and document reading must work before sub-agent logic**

#### Task 1.1: Database Schema for Sub-Agent Metadata

**Purpose:** Extend messages table to store sub-agent execution metadata
**Dependencies:** [] | **WAVE:** 1 | **AGENT_ROLE:** db-specialist

**Implementation:**
1. Create `014_subagent_support.sql`
2. Add `subagent_metadata JSONB` to messages table (nullable)
3. Schema: `{task_description, document_id, document_name, status, reasoning_steps[], result, error, depth}`
4. RLS already scoped by user_id

**Validation:** Apply in Supabase Dashboard, verify column exists with `SELECT column_name FROM information_schema.columns WHERE table_name='messages' AND column_name='subagent_metadata';`

---

#### Task 1.2: Document Service - Full Document Reading

**Purpose:** Read full document content from Supabase Storage
**Dependencies:** [] | **WAVE:** 1 | **AGENT_ROLE:** backend-dev

**Implementation:**
1. CREATE `backend/services/document_service.py`
2. Functions:
   - `get_document_by_id(document_id, user_id)` → dict or 404
   - `read_full_document(document_id, user_id)` → str
     - Download from Supabase Storage to temp
     - Use `embedding_service.parse_document()`
     - Clean up temp file
3. Error handling: 404, storage failure, parse error

**Pattern Reference:** `routers/ingestion.py:17-73`

**Validation:** Test with `python -c "from services.document_service import read_full_document; ..."`

**Wave 1 Checkpoint:** Migration applied + document service imports OK

---

### Phase 2: Sub-Agent Orchestration

#### Task 2.1: Sub-Agent Service - Core Logic

**Purpose:** Orchestrate sub-agent execution with isolated context, recursion prevention
**Dependencies:** 1.1, 1.2 | **WAVE:** 2 | **AGENT_ROLE:** backend-dev | **BLOCKS:** 3.1

**Implementation:**

1. CREATE `backend/models/subagent.py` with: `SubAgentRequest`, `ReasoningStep`, `SubAgentResult`

2. CREATE `backend/services/subagent_service.py`:
   - `execute_subagent(request, user_id) -> SubAgentResult`
     - Check recursion: `parent_depth >= 2` → fail
     - Read document via `document_service`
     - Build isolated conversation with system prompt + full doc text
     - Stream response via `provider_service.stream_chat_completion()`
     - Collect reasoning steps, return result
   - `READ_FULL_DOCUMENT_TOOL` (no-op, doc preloaded)
   - Config: `MAX_RECURSION_DEPTH = 2`, `SUBAGENT_MODEL = "gpt-4o-mini"`

**Error Scenarios:** 404, recursion limit, LLM error, storage error → SubAgentResult with error

**LangSmith:** Wrap execution in trace (pattern: `chat_service.py:104-126`)

**Validation:** `cd backend && python test_subagent_service.py`

---

### Phase 3: Integration with Chat Service & Frontend UI

**WAVE 3 - These tasks can run in parallel after Wave 2**

#### Task 3.1: Chat Service - Sub-Agent Tool Integration

**Purpose:** Add `analyze_document_with_subagent` tool to main chat
**Dependencies:** 2.1 | **WAVE:** 3 | **AGENT_ROLE:** backend-dev | **PROVIDES:** Sub-agent tool

**Implementation:**

1. UPDATE `backend/services/chat_service.py`:
   - Add `ANALYZE_DOCUMENT_TOOL` after line 46
   - Update `stream_response()` tools list: `[RETRIEVAL_TOOL, ANALYZE_DOCUMENT_TOOL]`
   - Add tool handler after line 172:
     - Parse args: `task_description`, `document_name`
     - Find document by name (query documents table)
     - Execute sub-agent: `subagent_service.execute_subagent()`
     - Build `subagent_metadata` dict
     - Add tool call + response to conversation

2. UPDATE `routers/chat.py` send_message (line 301-312):
   - Store `subagent_metadata` in message if exists

**Pattern Reference:** `services/chat_service.py:168-227`

**Validation:** `cd backend && python test_subagent_integration.py`

---

#### Task 3.2: Frontend - Sub-Agent UI Components

**Purpose:** Display sub-agent execution in expandable sections
**Dependencies:** None | **WAVE:** 3 | **AGENT_ROLE:** frontend-dev | **PROVIDES:** SubAgentSection component

**Implementation:**

1. CREATE `frontend/src/types/subagent.ts` with `ReasoningStep`, `SubAgentMetadata`

2. UPDATE `frontend/src/types/chat.ts`:
   - Add `subagent_metadata?: SubAgentMetadata` to Message interface

3. CREATE `frontend/src/components/Chat/SubAgentSection.tsx`:
   - Expandable card with header: task, status icon (processing/completed/failed)
   - Body: document name, reasoning steps, result, error
   - Use lucide-react icons: ChevronDown, Bot, CheckCircle, XCircle, Loader

4. UPDATE `frontend/src/components/Chat/MessageList.tsx` after line 61:
   - Render `<SubAgentSection metadata={message.subagent_metadata} />` if present

**Pattern Reference:** `MessageList.tsx:44-61`

**Validation:** Mock message in console, verify UI renders + interacts correctly

**Wave 3 Checkpoint:** Backend tool defined + Frontend compiles

---

### Phase 4: Final Integration & E2E Testing

**WAVE 4 - Sequential after Wave 3**

#### Task 4.1: Wire Backend + Frontend & E2E Tests

**Purpose:** Ensure full sub-agent flow works end-to-end
**Dependencies:** 3.1, 3.2 | **WAVE:** 4 | **AGENT_ROLE:** full-stack

**Implementation:**

1. CREATE `backend/test_subagent_service.py`:
   - Test: Basic execution, recursion limit, document not found
   - Pattern: async test functions with setup_test_document()

2. CREATE `backend/test_subagent_integration.py`:
   - Test: Sub-agent via chat tool call, metadata stored
   - Pattern: Stream chat with test document, verify response

3. Manual E2E (Browser):
   - Upload document, send "Analyze [doc] and summarize"
   - Verify: Tool call → sub-agent section → expandable UI → result displayed

**Validation:** `python test_subagent_service.py && python test_subagent_integration.py`

---

## TESTING STRATEGY

**⚠️ CRITICAL: Plan for MAXIMUM test automation**

### Test Automation Requirements

**Total Tests**: 8 tests
- ✅ **Automated**: 6 (75%)
  - Unit: 4 via pytest
  - Integration: 2 via pytest
- ⚠️ **Manual**: 2 (25%) - Browser E2E validation (complex multi-step flow, visual verification)

**Goal**: 75%+ automated coverage ✅ Met

### Unit Tests

**Automation**: ✅ Automated | **Tool**: pytest | **Location**: test_subagent_service.py
**Tests**: Basic execution, recursion limit, 404, document reading
**Execution**: `cd backend && python test_subagent_service.py`

### Integration Tests

**Automation**: ✅ Automated | **Tool**: pytest | **Location**: test_subagent_integration.py
**Tests**: Sub-agent via chat tool, metadata storage
**Execution**: `cd backend && python test_subagent_integration.py`

### End-to-End Tests

**Automation**: ⚠️ Manual
**Why**: Complex multi-step flow, visual verification, requires real environment

**Manual E2E: Full Sub-Agent Flow (~5 min)**
1. Start servers, login, upload document
2. Send: "Analyze [doc] and summarize"
3. Verify: Tool call → sub-agent section → expand → result displayed

**Manual E2E: Error Handling (~2 min)**
1. Send: "Analyze nonexistent.pdf"
2. Verify: Error shown, no crash, sub-agent section shows error state

### Edge Cases (Automated via pytest)

1. Empty document → graceful handling
2. Large document (>100KB) → truncation/streaming
3. LLM API failure → error in SubAgentResult
4. Concurrent calls → isolation maintained

### Test Automation Summary

**Total**: 8 tests | **Automated**: 6 (75%) | **Manual**: 2 (25%) - Browser E2E
**Goal**: 75%+ ✅ Met

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% correctness.

### Level 0: Prerequisites
```bash
cd backend && venv/Scripts/python --version  # 3.12.x
# Verify DB migration in Supabase Dashboard
```

### Level 1: Syntax & Style
```bash
cd frontend && npm run lint && npm run build  # No errors
```

### Level 2: Unit Tests
```bash
cd backend && python test_subagent_service.py  # [ALL TESTS PASSED]
```

### Level 3: Integration Tests
```bash
cd backend && python test_subagent_integration.py  # [INTEGRATION TEST PASSED]
cd backend && python test_rag_tool_calling.py  # Regression check
```

### Level 4: Manual Validation
Start servers, upload document, send "Analyze [doc]", verify sub-agent UI

### Level 5: Additional
- LangSmith: Check nested sub-agent trace
- Database: Verify subagent_metadata in messages table

---

## ACCEPTANCE CRITERIA

- [ ] Database schema extended with `subagent_metadata` JSONB column
- [ ] Document service reads full document content from storage
- [ ] Sub-agent service executes with isolated context
- [ ] Recursion depth limit enforced (max depth = 2)
- [ ] Main agent can call `analyze_document_with_subagent` tool
- [ ] Sub-agent metadata stored in messages table
- [ ] Frontend displays sub-agent section (expandable)
- [ ] Unit tests pass (sub-agent service, document service)
- [ ] Integration tests pass (chat service with sub-agent)
- [ ] Manual E2E test completes successfully
- [ ] No console errors in frontend
- [ ] No regressions in existing RAG tests
- [ ] Code follows project conventions (no print statements, RLS enforced)
- [ ] LangSmith tracing captures sub-agent execution

---

## COMPLETION CHECKLIST

- [ ] **Phase 1 Complete:**
  - [ ] Migration 014 applied successfully
  - [ ] Document service reads from storage
  - [ ] Level 0 validation passes
- [ ] **Phase 2 Complete:**
  - [ ] Sub-agent service implemented
  - [ ] Unit tests created and passing
  - [ ] Level 2 validation passes
- [ ] **Phase 3 Complete:**
  - [ ] Chat service tool integrated
  - [ ] Frontend UI components created
  - [ ] Level 1 validation passes (linting, TypeScript)
- [ ] **Phase 4 Complete:**
  - [ ] Integration tests passing
  - [ ] E2E manual test successful
  - [ ] Level 3-5 validation passes
- [ ] All validation commands executed (Levels 0-5)
- [ ] Full test suite passes (unit + integration)
- [ ] Manual testing completed (E2E browser test)
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality:
  - [ ] No print() in production code (backend/services, backend/routers)
  - [ ] RLS enforced (user_id filtering)
  - [ ] Error handling graceful
  - [ ] LangSmith tracing working
- [ ] **⚠️ Debug logs added during execution REMOVED (keep pre-existing logs only)**
- [ ] **⚠️ CRITICAL: Changes left UNSTAGED (NOT committed) for user review**

---

## NOTES

### Design Decisions

**LLM-triggered:** Most flexible, aligns with RAG tool-calling principle
**Full document:** Simpler than chunking, higher token cost but clearer results
**Recursion limit = 2:** Prevents infinite loops, sufficient for delegation
**JSONB metadata:** Flexible schema, not performance-critical, simple frontend

### Trade-offs

**Full vs. Chunked:** Complete context (pro) vs. higher cost (con) → use for <50K char docs
**Expandable UI:** Clean chat (pro) vs. more clicks (con) → auto-expand on error
**Isolation:** Clean conversation (pro) vs. no prior context (con) → include context in task_description

### Future Enhancements (Out of Scope)

Parallel sub-agents, streaming reasoning, additional tools, cost estimation, result caching
