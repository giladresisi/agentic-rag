# Feature: ir-copilot-theme-change

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution that were NOT explicitly requested
- Keep pre-existing debug logs already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes — no git operations

Validate documentation and codebase patterns before implementing. Pay attention to naming of existing constants, validators, and RPC function names. Import from correct files.

## Feature Description

Replace the placeholder `books` table and associated fiction-themed sample data with a `production_incidents` table containing 15 realistic incident records. Update the SQL tool, all references in services, tests, and documentation to use the new domain. Rename the project to "IR-Copilot" (Incident Response Copilot) across all user-facing text. Create 6 postmortem markdown documents in `backend/eval/postmortems/` that serve as both manual test fixtures and the corpus for the upcoming RAGAS evaluation pipeline.

## User Story

As a hiring manager reviewing a portfolio project,
I want to see a demo that uses real-world operational data (production incidents + postmortems),
So that I can immediately recognize the system's practical value for an engineering organisation.

## Problem Statement

The current `books` table and "Agentic RAG Application" branding are generic and do not signal domain awareness. A production incidents theme is immediately recognizable to engineering employers, demonstrates understanding of SRE workflows, and creates a coherent demo where SQL (structured queries) and RAG (semantic postmortem retrieval) complement each other.

## Solution Statement

New Supabase migration (016) replaces `books` with `production_incidents` and renames the RPC function. SQL service constants, validation logic, and chat service tool definition are updated. All tests and documentation are updated in one coordinated sweep. Six postmortem markdown documents are authored and placed in `backend/eval/postmortems/` for ingestion.

## Feature Metadata

**Feature Type**: Enhancement / Theme Change
**Complexity**: Medium
**Primary Systems Affected**: sql_service, chat_service, supabase migrations, tests, docs
**Dependencies**: None (self-contained)
**Breaking Changes**: No — same API surface, renamed internals only

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `supabase/migrations/013_sql_tool.sql` (lines 1–96) — existing books table DDL, RPC function, permission grants; mirror structure for migration 016
- `backend/services/sql_service.py` (lines 1–25) — `BOOKS_SCHEMA` constant to replace; (lines 40–90) `_validate_query` FROM-clause check; (lines 100–190) `natural_language_to_sql` system prompt and RPC call name
- `backend/services/chat_service.py` (lines 51–65) — `TEXT_TO_SQL_TOOL` definition, tool name and description; (lines 200–210, 277) system prompt references to books; (lines 442–515) `elif tool_name == "query_books_database"` dispatch block — all occurrences of the string must be renamed
- `backend/tests/auto/test_sql_service.py` (lines 1–247) — full rewrite; preserve test structure (6 tests + main runner), replace book-domain queries with incident-domain equivalents
- `backend/tests/auto/test_multi_tool_integration.py` — find and replace books turn (query "List some fantasy genre books") with incidents turn
- `backend/tests/auto/test_simple_strategic.py` (lines 1, 44–50) — file docstring and queries reference books; update to incidents
- `backend/tests/auto/test_debug_stream.py` (line 39) — single query "What books by George Orwell are in the database?"
- `frontend/tests/optional-e2e-validation.spec.ts` (lines 190–210) — Module 7 section header, query, assertion, and console.log

### New Files to Create

- `supabase/migrations/016_production_incidents.sql` — drops books, creates production_incidents, seeds 15 rows, re-grants permissions, creates execute_incidents_query RPC
- `backend/eval/postmortems/INC-2024-003-auth-outage.md`
- `backend/eval/postmortems/INC-2024-011-payment-db-corruption.md`
- `backend/eval/postmortems/INC-2024-019-pipeline-memory-leak.md`
- `backend/eval/postmortems/INC-2024-027-gateway-timeout.md`
- `backend/eval/postmortems/INC-2024-031-notif-queue-backup.md`
- `backend/eval/postmortems/INC-2024-038-deploy-rollback.md`

### Patterns to Follow

**Migration pattern**: `013_sql_tool.sql` — DROP → CREATE TABLE → INSERT seed data → GRANT/REVOKE → CREATE FUNCTION → GRANT EXECUTE → COMMENT
**RPC function pattern**: `execute_books_query` in `013_sql_tool.sql` lines 53–92 — mirror exactly, changing table name and validation strings
**Schema constant pattern**: `BOOKS_SCHEMA` in `sql_service.py` lines 15–23 — plain multiline string, column-per-line format
**Tool definition pattern**: `TEXT_TO_SQL_TOOL` in `chat_service.py` lines 51–65 — JSON schema object with name, description, parameters

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌──────────────────────────────────────────────────────────────┐
│ WAVE 1: Migration + Service Layer (Parallel)                 │
├──────────────────┬───────────────────────────────────────────┤
│ Task 1.1         │ Task 1.2          │ Task 1.3              │
│ Migration 016    │ sql_service.py    │ chat_service.py       │
│ (DB layer)       │ (schema+validate) │ (tool rename+prompt)  │
└──────────────────┴───────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ WAVE 2: Tests + Docs + Postmortems (Parallel, after Wave 1)  │
├──────────────────┬───────────────────────────────────────────┤
│ Task 2.1         │ Task 2.2          │ Task 2.3              │
│ Backend tests    │ Frontend E2E test │ Postmortem docs       │
│ (4 files)        │ (1 file)          │ (6 markdown files)    │
└──────────────────┴───────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│ WAVE 3: Documentation (Sequential, after Wave 2)             │
├──────────────────────────────────────────────────────────────┤
│ Task 3.1: README + SETUP.md + PROGRESS.md + CONTRIBUTING.md  │
└──────────────────────────────────────────────────────────────┘
```

**Wave 1 — Fully Parallel:** Tasks 1.1, 1.2, 1.3 — no dependencies
**Wave 2 — Parallel after Wave 1:** Tasks 2.1, 2.2, 2.3 — need new tool name from 1.2/1.3
**Wave 3 — Sequential:** Task 3.1 — needs everything complete for accurate docs

**Interface Contracts:**
- Task 1.2 provides: tool name string `query_incidents_database`, RPC name `execute_incidents_query`
- Task 1.3 consumes: same strings (must match exactly for dispatch to work)
- Task 2.1 consumes: new tool name from 1.3 for assertion strings in tests

---

## IMPLEMENTATION PLAN

### Phase 1: Database + Service Layer

#### Task 1.1: CREATE `supabase/migrations/016_production_incidents.sql`

**WAVE**: 1 | **AGENT_ROLE**: db-specialist | **DEPENDS_ON**: [] | **BLOCKS**: [2.1]

**Implement:**

Part 1 — Drop old artifacts:
```sql
DROP TABLE IF EXISTS books CASCADE;
DROP FUNCTION IF EXISTS execute_books_query(TEXT);
```

Part 2 — Create table:
```sql
CREATE TABLE IF NOT EXISTS production_incidents (
    id SERIAL PRIMARY KEY,
    incident_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('P1','P2','P3','P4')),
    service_affected TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'resolved' CHECK (status IN ('resolved','open','monitoring')),
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    duration_minutes INTEGER,
    root_cause_category TEXT CHECK (root_cause_category IN ('database','deployment','network','third-party','configuration')),
    description TEXT,
    postmortem_written BOOLEAN DEFAULT FALSE
);
```

Part 3 — Seed 15 incidents. Requirements for seed data:
- Severity spread: 3× P1, 4× P2, 5× P3, 3× P4
- Services: auth-service (3), payment-api (4), data-pipeline (3), api-gateway (3), notification-service (2)
- Status: 12 resolved, 2 monitoring, 1 open
- Root causes: cover all 5 categories (database×4, deployment×3, network×3, third-party×3, configuration×2)
- postmortem_written=TRUE for exactly 6 incidents (INC-2024-003, -011, -019, -027, -031, -038)
- Timestamps: 2024 dates, realistic durations (P1: 15–120 min, P2: 30–240 min, P3/P4: 60–480 min)

Part 4 — Permissions:
```sql
GRANT SELECT ON production_incidents TO sql_query_role;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON production_incidents FROM sql_query_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM sql_query_role;
```

Part 5 — RPC function (mirror `execute_books_query` structure from `013_sql_tool.sql:54-92`):
- Function name: `execute_incidents_query(query_text TEXT) RETURNS JSONB`
- Validation line 71 equivalent: `FROM PRODUCTION_INCIDENTS` and `FROM "PRODUCTION_INCIDENTS"`
- Error messages: reference `production_incidents` not `books`
- GRANT EXECUTE to authenticated, anon, service_role
- Add COMMENT ON TABLE and COMMENT ON FUNCTION

**VALIDATE:**
```sql
-- Run in Supabase SQL Editor after applying migration:
SELECT COUNT(*) FROM production_incidents;  -- expect 15
SELECT severity, COUNT(*) FROM production_incidents GROUP BY severity ORDER BY severity;
SELECT execute_incidents_query('SELECT incident_id, severity FROM production_incidents WHERE severity = ''P1'' LIMIT 10');
```

---

#### Task 1.2: UPDATE `backend/services/sql_service.py`

**WAVE**: 1 | **AGENT_ROLE**: backend-specialist | **DEPENDS_ON**: [] | **BLOCKS**: [2.1]
**PROVIDES**: Confirmed strings `query_incidents_database`, `execute_incidents_query`, `PRODUCTION_INCIDENTS`

**Changes (read file fully before editing):**

1. Rename constant `BOOKS_SCHEMA` → `INCIDENTS_SCHEMA` (line 15), update content:
```python
INCIDENTS_SCHEMA = """production_incidents table columns:
- id (INTEGER PRIMARY KEY)
- incident_id (TEXT) - human-readable ID e.g. INC-2024-031
- title (TEXT)
- severity (TEXT) - P1, P2, P3, P4
- service_affected (TEXT)
- status (TEXT) - resolved, open, monitoring
- started_at (TIMESTAMPTZ)
- resolved_at (TIMESTAMPTZ, nullable)
- duration_minutes (INTEGER, nullable)
- root_cause_category (TEXT) - database, deployment, network, third-party, configuration
- description (TEXT)
- postmortem_written (BOOLEAN)"""
```

2. `_validate_query` — FROM clause check: `"BOOKS"` → `"PRODUCTION_INCIDENTS"` (both unquoted and quoted variants); update error message to reference `production_incidents`

3. `_validate_query` — JOIN check: `"BOOKS"` → `"PRODUCTION_INCIDENTS"`

4. `_get_sql_query_client` docstring: "books table" → "production_incidents table"

5. `natural_language_to_sql` system prompt: replace schema reference (`{BOOKS_SCHEMA}` → `{INCIDENTS_SCHEMA}`), update "ONLY query the 'books' table" → "ONLY query the 'production_incidents' table", update all mention of "books" in rules

6. RPC call: `'execute_books_query'` → `'execute_incidents_query'`

**VALIDATE:**
```bash
cd backend
grep -n "books\|BOOKS\|query_books" services/sql_service.py
# expect: 0 results
```

---

#### Task 1.3: UPDATE `backend/services/chat_service.py`

**WAVE**: 1 | **AGENT_ROLE**: backend-specialist | **DEPENDS_ON**: [] | **BLOCKS**: [2.1]

**Changes (this file is 754 lines — search precisely):**

1. `TEXT_TO_SQL_TOOL` name (line 54): `"query_books_database"` → `"query_incidents_database"`

2. `TEXT_TO_SQL_TOOL` description (line 55-60): replace with:
   `"Query a database of production incidents using natural language. Use for questions about incidents, severity, affected services, resolution times, root causes. Examples: 'Show all P1 incidents', 'Which service had the most outages?', 'Average resolution time for database issues'"`

3. Tool parameter description: `"Natural language query about books"` → `"Natural language query about production incidents"`

4. System prompt line 203: `"2. query_books_database: Query a books database..."` → `"2. query_incidents_database: Query a production incidents database..."`

5. System prompt line 277: `"Questions about books/authors/genres → query_books_database"` → `"Questions about incidents/severity/services → query_incidents_database"`

6. All dispatch occurrences (lines 442, 451, 464, 475, 489, 505): `"query_books_database"` → `"query_incidents_database"` (use replace_all=true)

**VALIDATE:**
```bash
cd backend
grep -n "books\|Books\|query_books" services/chat_service.py
# expect: 0 results
```

---

### Phase 2: Tests + Documents

#### Task 2.1: REWRITE backend tests (4 files)

**WAVE**: 2 | **AGENT_ROLE**: test-specialist | **DEPENDS_ON**: [1.2, 1.3] | **BLOCKS**: []

**File 1: `backend/tests/auto/test_sql_service.py`** — full rewrite, preserve 6-test structure:

| Old test | New test | Query | Assertion |
|---|---|---|---|
| `test_count_query` | keep | "How many incidents are in the database?" | count ≥ 15 |
| `test_author_filter` | `test_severity_filter` | "Show all P1 incidents" | results have severity=P1 |
| `test_genre_filter` | `test_service_filter` | "Incidents affecting auth-service" | results have service_affected matching auth |
| `test_sql_injection` | keep | update to incident context | same logic |
| `test_table_access_control` | keep | update error check for `production_incidents` | any error acceptable |
| `test_write_prevention` | keep | "Insert a new incident called Test..." | same logic |

**File 2: `backend/tests/auto/test_multi_tool_integration.py`** — find `test_books_query` function and the "books" turn in multi-turn test:
- Replace "List some fantasy genre books from the database." → "Show me all P1 incidents in the database."
- Replace assertions: `"book"`, `"fantasy"`, `"author"`, `"title"` → `"incident"`, `"P1"`, `"severity"`, `"service"`
- Replace `results["books"]` key → `results["incidents"]`
- Replace `"query_books_database"` → `"query_incidents_database"` in assertions

**File 3: `backend/tests/auto/test_simple_strategic.py`** — update:
- Line 1 docstring: "books database only" → "incidents database only"
- Lines 44–50: replace both book-domain queries with incident queries:
  - "What fantasy books with ratings above 4.0 are available?" → "What P1 and P2 incidents affected the auth-service?"
  - "What books did George Orwell write?" → "Which incidents had a root cause of database?"

**File 4: `backend/tests/auto/test_debug_stream.py`** — line 39:
- `"What books by George Orwell are in the database?"` → `"What P1 incidents are in the database?"`

**VALIDATE:**
```bash
cd backend
venv/Scripts/python -m pytest tests/auto/test_sql_service.py tests/auto/test_multi_tool_integration.py tests/auto/test_simple_strategic.py tests/auto/test_debug_stream.py -v 2>&1 | tail -20
```

---

#### Task 2.2: UPDATE `frontend/tests/optional-e2e-validation.spec.ts`

**WAVE**: 2 | **AGENT_ROLE**: frontend-specialist | **DEPENDS_ON**: [1.3] | **BLOCKS**: []

Lines ~190–210 (Module 7 section):
1. Comment: `// ── Module 7: Text-to-SQL (books)` → `// ── Module 7: Text-to-SQL (incidents)`
2. `describe` or comment text: `'Text-to-SQL tool (books database)'` → `'Text-to-SQL tool (incidents database)'`
3. Query: `'What books were written by George Orwell?'` → `'Show me all P1 incidents in the database'`
4. Assertion keywords: replace `"book"`, `"orwell"`, `"animal farm"` with `"incident"`, `"P1"`, `"severity"`
5. `console.log`: update text to reference incidents

**VALIDATE:**
```bash
cd frontend
npx playwright test optional-e2e-validation --grep "Text-to-SQL" --reporter=list 2>&1 | tail -10
```

---

#### Task 2.3: CREATE 6 postmortem markdown documents

**WAVE**: 2 | **AGENT_ROLE**: content-specialist | **DEPENDS_ON**: [] | **BLOCKS**: []

Create `backend/eval/postmortems/` directory. Write 6 files, 350–450 words each.

**Template for each file:**
```markdown
# [INC-YYYY-NNN] — [Title]

**Severity:** P1 | **Service:** [service] | **Duration:** [X] min | **Status:** resolved
**Date:** [YYYY-MM-DD] | **Root Cause Category:** [category]

## Summary
[2–3 sentence overview of what happened and impact]

## Timeline
- **HH:MM** — [event]
- **HH:MM** — [alert fired / detection]
- ...
- **HH:MM** — [resolution]

## Root Cause
[Specific technical root cause — 3–5 sentences with realistic details]

## Contributing Factors
- [Factor 1]
- [Factor 2]
- [Factor 3]

## Detection Gap
[What monitoring was missing or slow to fire — 2–3 sentences]

## Follow-up Actions
1. [Concrete action item with owner team]
2. [Concrete action item]
3. [Concrete action item]
```

**Files and scenarios:**

| File | Incident | Root cause detail |
|---|---|---|
| `INC-2024-003-auth-outage.md` | JWT validation timeout cascade → auth-service down 47 min | Redis TTL misconfiguration causing token cache misses, all requests hitting Postgres |
| `INC-2024-011-payment-db-corruption.md` | B-tree index corruption after unclean shutdown → payment writes failing 2 h | PostgreSQL 14.1 bug with partial page writes; missing fsync on replica |
| `INC-2024-019-pipeline-memory-leak.md` | Data pipeline OOM crash loop → 6 h batch delay | asyncio Task objects held in unbounded list; fix: weakref-based registry |
| `INC-2024-027-gateway-timeout.md` | Upstream TLS handshake failures → 504s on all API routes 38 min | Expired intermediate cert on load balancer not caught by cert rotation job |
| `INC-2024-031-notif-queue-backup.md` | RabbitMQ queue saturation → notification delivery delay 4 h | Consumer group scaled down during maintenance; queue depth alarm threshold too high |
| `INC-2024-038-deploy-rollback.md` | Nil pointer panic in new deployment → payment-api 503s 22 min | Missing nil check on optional config field; canary deployment not enabled |

**VALIDATE:**
```bash
ls backend/eval/postmortems/ | wc -l   # expect 6
wc -w backend/eval/postmortems/*.md    # expect ~350-450 words each
```

---

### Phase 3: Documentation

#### Task 3.1: UPDATE documentation files

**WAVE**: 3 | **AGENT_ROLE**: docs-specialist | **DEPENDS_ON**: [2.1, 2.2, 2.3] | **BLOCKS**: []

**`README.md`:**
- Title → `# IR-Copilot — Incident Response AI Assistant`
- Opening paragraph: replace "RAG application" framing with incident intelligence theme
- Text-to-SQL examples section: replace 3 book queries with:
  - `"Show all P1 incidents from the last 30 days"`
  - `"Which service had the most outages this year?"`
  - `"Average resolution time for database-related incidents"`
- Remove all remaining occurrences of "books" (check for false positives: "notebooks" is fine)

**`SETUP.md`:**
- Replace "Agentic RAG" → "IR-Copilot" in project name references
- Keep all technical setup instructions unchanged; only display names change

**`PROGRESS.md`:**
- Module 7 notes section: "books database" → "production_incidents database"
- Update the planning entries added at the bottom: set Status to "Complete" for this feature

**`CONTRIBUTING.md`:**
- Line 1 heading: "Contributing to Agentic RAG" → "Contributing to IR-Copilot"
- Line 9: update issues tracker URL text (keep URL unchanged)
- Line 46: "Agentic RAG" reference → "IR-Copilot"

**VALIDATE:**
```bash
grep -rn "books\|query_books\|Agentic RAG" README.md SETUP.md CONTRIBUTING.md backend/services/
# expect: 0 results (manually check for false positives like "notebooks")
```

---

## TESTING STRATEGY

### Unit / Integration Tests

**Automation**: ✅ Fully Automated | **Tool**: pytest
**Location**: `backend/tests/auto/`
**Execution**: `cd backend && venv/Scripts/python -m pytest tests/auto/test_sql_service.py tests/auto/test_multi_tool_integration.py -v`

### E2E Test

**Automation**: ✅ Automated | **Tool**: Playwright
**Location**: `frontend/tests/optional-e2e-validation.spec.ts`
**Execution**: `cd frontend && npx playwright test optional-e2e-validation --grep "Text-to-SQL"`
**Note**: Requires live backend at localhost:8000 and migration 016 applied

### Manual: Apply Migration 016

**Why Manual**: Requires Supabase dashboard SQL editor access; migration is destructive (drops `books`)
**Steps**: Open Supabase SQL Editor → paste `016_production_incidents.sql` → run → verify count
**Expected**: 15 rows in production_incidents, execute_incidents_query RPC works

### Test Automation Summary

**Total tests**: 8 automated + 1 manual
- ✅ **Automated**: 8 (89%) — pytest + Playwright
- ⚠️ **Manual**: 1 (11%) — Supabase migration (requires dashboard access)
- **Goal**: 89% ✅ Met

---

## VALIDATION COMMANDS

### Level 1: No lingering "books" references
```bash
grep -rn "books\|BOOKS\|query_books\|execute_books" \
  backend/services/ backend/tests/ frontend/tests/ README.md SETUP.md CONTRIBUTING.md
# expect: 0 results
```

### Level 2: Backend tests
```bash
cd backend
venv/Scripts/python -m pytest tests/auto/test_sql_service.py \
  tests/auto/test_multi_tool_integration.py \
  tests/auto/test_simple_strategic.py \
  tests/auto/test_debug_stream.py -v
```

### Level 3: Full backend suite (regression check)
```bash
cd backend
venv/Scripts/python -m pytest tests/auto/ -v 2>&1 | tail -10
```

### Level 4: Postmortem docs
```bash
ls backend/eval/postmortems/ | wc -l      # expect 6
grep -l "Follow-up Actions" backend/eval/postmortems/*.md | wc -l  # expect 6
```

### Level 5: E2E (requires running server + migration applied)
```bash
cd frontend && npx playwright test optional-e2e-validation --grep "Text-to-SQL" --reporter=list
```

---

## ACCEPTANCE CRITERIA

- [ ] `production_incidents` table exists with 15 rows and correct schema
- [ ] `execute_incidents_query` RPC executes SELECT queries on the new table
- [ ] Zero occurrences of `books`, `query_books`, `execute_books` in services/tests/docs
- [ ] All 6 backend test files pass with incident-domain queries
- [ ] 6 postmortem markdown documents exist with all required sections
- [ ] README.md title reads "IR-Copilot"
- [ ] No regressions: full `pytest tests/auto/` suite still green

---

## COMPLETION CHECKLIST

- [ ] Migration 016 written and validated in Supabase
- [ ] `sql_service.py` — 0 books references
- [ ] `chat_service.py` — 0 books references, all dispatch branches updated
- [ ] 4 backend test files updated and passing
- [ ] Frontend E2E test updated
- [ ] 6 postmortem markdown files created in `backend/eval/postmortems/`
- [ ] README, SETUP.md, PROGRESS.md, CONTRIBUTING.md updated
- [ ] Full pytest suite passes with no regressions
- [ ] **⚠️ Changes left UNSTAGED for user review**

---

## NOTES

- The GitHub repo rename (`agentic-rag` → `ir-copilot`) is a manual step in GitHub Settings → General. Add a note in SETUP.md pointing users to do this step; do NOT attempt it programmatically.
- `backend/eval/postmortems/` is created here (by Task 2.3) so that the RAGAS plan (Plan 002) can immediately reference and ingest these files without any additional setup.
- The `sql_query_role` role and its password are unchanged — only its table permissions are updated.
- Do NOT rename the Cloud Run service or Vercel project — URL changes would require reconfiguring CORS and environment variables across multiple services.
