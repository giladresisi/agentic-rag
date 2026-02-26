# Feature: sql-topic-replace-incidents-with-deployments

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs added during execution (console.log, print, etc.) NOT explicitly requested
- Keep pre-existing debug logs already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review with `git diff` before committing

## Feature Description

Replace the `production_incidents` SQL table with a `deployments` (change management log) table.
This eliminates a tool-routing ambiguity where the LLM incorrectly routes postmortem questions
to the SQL tool instead of retrieval, because both the SQL table and the uploaded documents are
about "incidents." After this change the two tools cover orthogonal domains with zero overlap:

- **`retrieve_documents`** → postmortem narrative content (why it happened, detection gaps,
  remediation steps) — lives in user-uploaded documents
- **`query_deployments_database`** → deployment facts (who deployed what version, when, success/
  failure, rollback counts, deployment frequency) — lives in the SQL table

Routing becomes deterministic: "why did the outage happen?" → retrieval; "what deployment
preceded the auth outage?" → SQL.

## Feature Type

**Enhancement** | **Complexity**: Medium | **Breaking Changes**: Yes — table renamed,
RPC function renamed, tool function name renamed

---

## CONTEXT REFERENCES

### Critical Files — MUST READ BEFORE IMPLEMENTING

- `supabase/migrations/016_production_incidents.sql` (full) — template for new 016; replace entirely
- `backend/services/sql_service.py` (lines 14-27, 44-106, 139-191) — schema constant, validation,
  RPC call; all three sections need updating
- `backend/services/chat_service.py` (lines 51-67) — TEXT_TO_SQL_TOOL definition to rename/redescribe
- `backend/services/chat_service.py` (lines 200-205, 277 area) — system prompt tool list and routing
  guidance; two separate spots
- `backend/services/chat_service.py` (line 442) — `elif tool_name == "query_incidents_database":` routing
- `backend/eval/tool_selection_dataset.py` (lines 59-86) — 4 SQL samples to replace entirely
- `backend/eval/tool_selection_pipeline.py` (lines 69-157) — TOOL_SELECTION_SYSTEM_PROMPT with
  tool name and routing guidance at lines 72 and 146
- `backend/tests/auto/test_sql_service.py` (full, 237 lines) — update questions, column refs, strings

### New Files to Create

- `supabase/migrations/016_deployments.sql` — permanent replacement migration (rename+replace 016)
- `supabase/migrations/ADHOC_migrate_to_deployments.sql` — one-shot migration for user's existing DB

### Patterns to Follow

- Migration structure: `016_production_incidents.sql` — same section order (drop, create, seed,
  permissions, RLS, RPC function)
- RPC function security pattern: `SECURITY DEFINER`, `SET search_path = public`, same validation
  blocks as `execute_incidents_query` but checking `DEPLOYMENTS` table
- sql_service.py validation: same 7-check structure, only change table name strings

---

## TARGET STATE — Deployment Table Schema

```sql
CREATE TABLE IF NOT EXISTS deployments (
    id                 SERIAL PRIMARY KEY,
    deploy_id          TEXT UNIQUE NOT NULL,          -- 'DEP-2024-001'
    service            TEXT NOT NULL,                 -- 'auth-service', 'payment-api', etc.
    version            TEXT NOT NULL,                 -- 'v2.13.1'
    environment        TEXT NOT NULL CHECK (environment IN ('production','staging','canary')),
    deployed_by        TEXT NOT NULL,                 -- engineer name
    team               TEXT NOT NULL,                 -- 'platform', 'backend', 'data'
    deploy_type        TEXT NOT NULL CHECK (deploy_type IN ('feature','hotfix','rollback','config','migration')),
    status             TEXT NOT NULL CHECK (status IN ('success','failed','rolled_back')),
    started_at         TIMESTAMPTZ NOT NULL,
    completed_at       TIMESTAMPTZ,
    duration_seconds   INTEGER,
    triggered_incident BOOLEAN DEFAULT FALSE,         -- did this deployment cause an incident?
    rollback_of        TEXT,                          -- deploy_id being reversed, if rollback
    notes              TEXT
);
```

**15 seed rows** (same services as postmortem docs; some rows correlate with postmortem incidents
to enable interesting cross-tool queries):

| deploy_id    | service               | version | deploy_type | status      | triggered_incident | notes (abbreviated)                        |
|--------------|-----------------------|---------|-------------|-------------|--------------------|--------------------------------------------|
| DEP-2024-001 | auth-service          | v2.13.0 | feature     | success     | FALSE              | SSO improvements                           |
| DEP-2024-002 | auth-service          | v2.13.1 | config      | success     | TRUE               | Redis TTL config change → INC-2024-003     |
| DEP-2024-003 | auth-service          | v2.13.0 | rollback    | success     | FALSE              | Emergency rollback after INC-2024-003      |
| DEP-2024-004 | payment-api           | v4.1.5  | feature     | success     | FALSE              | Apple Pay support                          |
| DEP-2024-005 | payment-api           | v4.1.6  | migration   | failed      | TRUE               | Schema migration → INC-2024-011 corruption |
| DEP-2024-006 | payment-api           | v4.1.5  | rollback    | success     | FALSE              | DB rollback after INC-2024-011             |
| DEP-2024-007 | data-pipeline         | v2.3.0  | feature     | success     | FALSE              | PDF ingestion support                      |
| DEP-2024-008 | data-pipeline         | v2.3.1  | hotfix      | success     | FALSE              | Memory leak fix                            |
| DEP-2024-009 | api-gateway           | v1.9.0  | feature     | success     | FALSE              | Rate limiting enhancements                 |
| DEP-2024-010 | api-gateway           | v1.9.1  | config      | failed      | TRUE               | TLS cert rotation → INC-2024-027           |
| DEP-2024-011 | api-gateway           | v1.9.0  | rollback    | success     | FALSE              | TLS rollback after INC-2024-027            |
| DEP-2024-012 | notification-service  | v3.0.0  | feature     | success     | FALSE              | Email template engine upgrade              |
| DEP-2024-013 | payment-api           | v4.2.0  | feature     | success     | TRUE               | PDF receipts — nil pointer → INC-2024-038  |
| DEP-2024-014 | payment-api           | v4.1.9  | rollback    | rolled_back | FALSE              | Rollback failed — DB migration incompatible|
| DEP-2024-015 | payment-api           | v4.2.1  | hotfix      | success     | FALSE              | Forward-fix: made DB column optional       |

**RPC function name:** `execute_deployments_query(query_text TEXT)`
**Tool function name:** `query_deployments_database`

---

## PARALLEL EXECUTION STRATEGY

```
┌────────────────────────────────────────────────────────────────────┐
│ WAVE 1: Migrations + Backend Core (all parallel, no dependencies)  │
├──────────────────────┬─────────────────────┬───────────────────────┤
│ Task 1.1             │ Task 1.2             │ Task 1.3              │
│ 016_deployments.sql  │ ADHOC migration      │ sql_service.py        │
└──────────────────────┴─────────────────────┴───────────────────────┘
                                 ↓
┌────────────────────────────────────────────────────────────────────┐
│ WAVE 2: Application Layer + Datasets (all parallel)                │
├──────────────────────┬─────────────────────┬───────────────────────┤
│ Task 2.1             │ Task 2.2             │ Task 2.3              │
│ chat_service.py      │ tool_selection_      │ test_sql_service.py   │
│ (tool name + prompt) │ dataset.py +         │                       │
│                      │ pipeline.py          │                       │
└──────────────────────┴─────────────────────┴───────────────────────┘
                                 ↓
┌────────────────────────────────────────────────────────────────────┐
│ WAVE 3: Integration Tests (sequential — depends on chat_service)   │
├────────────────────────────────────────────────────────────────────┤
│ Task 3.1: Update integration test files with SQL queries           │
└────────────────────────────────────────────────────────────────────┘
```

**Wave 1 Checkpoint:** All three files created/updated independently — no sync needed.
**Wave 2 Checkpoint:** `cd backend && uv run python -c "from services.sql_service import sql_service; from services.chat_service import ChatService; print('imports OK')"` must pass.
**Wave 3 Checkpoint:** `cd backend && uv run pytest tests/auto/test_sql_service.py tests/auto/test_multi_tool_integration.py -v` must pass.

---

## IMPLEMENTATION PLAN

### WAVE 1 — Migrations + sql_service.py

#### Task 1.1: REPLACE supabase/migrations/016_production_incidents.sql → 016_deployments.sql

- **WAVE**: 1
- **AGENT_ROLE**: database-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: [2.3]
- **IMPLEMENT**:
  1. Rename the file: `016_production_incidents.sql` → `016_deployments.sql`
  2. Replace the entire content with:
     - **Part 1:** `DROP TABLE IF EXISTS books CASCADE` (keep for historical compat), then
       `DROP TABLE IF EXISTS production_incidents CASCADE`,
       `DROP FUNCTION IF EXISTS execute_books_query(TEXT)`,
       `DROP FUNCTION IF EXISTS execute_incidents_query(TEXT)`
     - **Part 2:** `CREATE TABLE IF NOT EXISTS deployments (...)` using the schema above
     - **Part 3:** 15 INSERT rows from the seed table above (full TIMESTAMPTZ values below)
     - **Part 4:** `GRANT SELECT ON deployments TO sql_query_role; REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON deployments FROM sql_query_role`
     - **Part 5:** `ALTER TABLE deployments ENABLE ROW LEVEL SECURITY` + two policies:
       `"authenticated_read_deployments"` and `"sql_query_role_read_deployments"` (same pattern as 016)
     - **Part 6:** `CREATE OR REPLACE FUNCTION execute_deployments_query(query_text TEXT) RETURNS JSONB` —
       same SECURITY DEFINER pattern, same 5 validation blocks, but check `LIKE '%FROM DEPLOYMENTS%'`
       and `LIKE '%FROM "DEPLOYMENTS"%'` instead of production_incidents
     - `GRANT EXECUTE ON FUNCTION execute_deployments_query TO authenticated`
     - `GRANT EXECUTE ON FUNCTION execute_deployments_query TO service_role`
  3. Full timestamp values for the 15 seed rows:
     - DEP-2024-001: started `2024-01-14 10:00:00+00`, completed `2024-01-14 10:14:00+00`, duration 840
     - DEP-2024-002: started `2024-01-15 02:00:00+00`, completed `2024-01-15 02:08:00+00`, duration 480
     - DEP-2024-003: started `2024-01-15 03:05:00+00`, completed `2024-01-15 03:12:00+00`, duration 420, rollback_of 'DEP-2024-002'
     - DEP-2024-004: started `2024-02-05 08:00:00+00`, completed `2024-02-05 08:22:00+00`, duration 1320
     - DEP-2024-005: started `2024-02-08 09:00:00+00`, completed `2024-02-08 09:18:00+00`, duration 1080
     - DEP-2024-006: started `2024-02-08 11:40:00+00`, completed `2024-02-08 11:52:00+00`, duration 720, rollback_of 'DEP-2024-005'
     - DEP-2024-007: started `2024-03-20 14:00:00+00`, completed `2024-03-20 14:30:00+00`, duration 1800
     - DEP-2024-008: started `2024-03-22 08:00:00+00`, completed `2024-03-22 08:25:00+00`, duration 1500
     - DEP-2024-009: started `2024-05-01 09:00:00+00`, completed `2024-05-01 09:20:00+00`, duration 1200
     - DEP-2024-010: started `2024-05-03 13:58:00+00`, completed `2024-05-03 14:02:00+00`, duration 240
     - DEP-2024-011: started `2024-05-03 14:45:00+00`, completed `2024-05-03 14:52:00+00`, duration 420, rollback_of 'DEP-2024-010'
     - DEP-2024-012: started `2024-06-09 11:00:00+00`, completed `2024-06-09 11:35:00+00`, duration 2100
     - DEP-2024-013: started `2024-07-02 11:00:00+00`, completed `2024-07-02 11:15:00+00`, duration 900
     - DEP-2024-014: started `2024-07-02 11:20:00+00`, completed `2024-07-02 11:30:00+00`, duration 600, rollback_of 'DEP-2024-013'
     - DEP-2024-015: started `2024-07-02 11:35:00+00`, completed `2024-07-02 11:45:00+00`, duration 600
- **VALIDATE**: File is valid SQL — confirm syntactically with `grep -c "INSERT INTO" supabase/migrations/016_deployments.sql` returns 1 (single multi-row INSERT) or 15 (individual INSERTs)

---

#### Task 1.2: CREATE supabase/migrations/ADHOC_migrate_to_deployments.sql

- **WAVE**: 1
- **AGENT_ROLE**: database-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: []
- **IMPLEMENT**: Create new file. Content:
  1. Header comment: `-- ADHOC MIGRATION: Upgrade existing DB from production_incidents to deployments. Run once, then delete.`
  2. `DROP TABLE IF EXISTS production_incidents CASCADE;`
  3. `DROP FUNCTION IF EXISTS execute_incidents_query(TEXT);`
  4. The exact CREATE TABLE, INSERT, GRANT, RLS, and CREATE FUNCTION blocks from Task 1.1
     (this file is self-contained — same content as the deployments section of 016_deployments.sql)
- **VALIDATE**: `grep "DROP TABLE IF EXISTS production_incidents" supabase/migrations/ADHOC_migrate_to_deployments.sql` returns a match

---

#### Task 1.3: UPDATE backend/services/sql_service.py

- **WAVE**: 1
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: [2.1, 2.3]
- **IMPLEMENT** (exact changes):
  1. **Line 15** — Rename constant: `INCIDENTS_SCHEMA = """production_incidents table columns:` →
     `DEPLOYMENTS_SCHEMA = """deployments table columns:`
  2. **Lines 16-27** — Replace schema body with deployments columns:
     ```
     - id (INTEGER PRIMARY KEY)
     - deploy_id (TEXT) -- e.g. 'DEP-2024-001'
     - service (TEXT) -- 'auth-service', 'payment-api', 'data-pipeline', 'api-gateway', 'notification-service'
     - version (TEXT) -- e.g. 'v2.13.1'
     - environment (TEXT) -- 'production', 'staging', 'canary'
     - deployed_by (TEXT) -- engineer who triggered the deployment
     - team (TEXT) -- 'platform', 'backend', 'data'
     - deploy_type (TEXT) -- 'feature', 'hotfix', 'rollback', 'config', 'migration'
     - status (TEXT) -- 'success', 'failed', 'rolled_back'
     - started_at (TIMESTAMPTZ) -- when deployment started
     - completed_at (TIMESTAMPTZ) -- when completed, NULL if still running
     - duration_seconds (INTEGER) -- total duration in seconds
     - triggered_incident (BOOLEAN) -- TRUE if this deployment caused a production incident
     - rollback_of (TEXT) -- deploy_id being reversed if this is a rollback, else NULL
     - notes (TEXT) -- optional deployment notes
     ```
  3. **Line 37 docstring** — `"production_incidents table"` → `"deployments table"`
  4. **Line 48 docstring** — `"production_incidents"` → `"deployments"`
  5. **Line 78** — error message: `"Query must contain a FROM clause referencing production_incidents"` →
     `"Query must contain a FROM clause referencing deployments"`
  6. **Line 80** — table check: `if table_name != "PRODUCTION_INCIDENTS":` → `if table_name != "DEPLOYMENTS":`
  7. **Line 81** — error: `"Only the 'production_incidents' table is allowed..."` →
     `"Only the 'deployments' table is allowed..."`
  8. **Line 86** — JOIN check: `if table != "PRODUCTION_INCIDENTS":` → `if table != "DEPLOYMENTS":`
  9. **Line 122 docstring** — `"production_incidents table"` → `"deployments table"`
  10. **Line 145** — schema reference: `f"{INCIDENTS_SCHEMA}\n\n"` → `f"{DEPLOYMENTS_SCHEMA}\n\n"`
  11. **Line 148** — `"ONLY query the 'production_incidents' table"` → `"ONLY query the 'deployments' table"`
  12. **Line 189** — RPC call: `'execute_incidents_query'` → `'execute_deployments_query'`
- **VALIDATE**: `grep -n "INCIDENTS\|production_incidents\|execute_incidents" backend/services/sql_service.py` returns zero results

---

### WAVE 2 — Application Layer + Datasets

#### Task 2.1: UPDATE backend/services/chat_service.py

- **WAVE**: 2
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: [3.1]
- **IMPLEMENT** (6 exact changes):
  1. **Line 54** — Tool name: `"name": "query_incidents_database"` → `"name": "query_deployments_database"`
  2. **Line 55** — Tool description (replace entire string):
     `"Query a deployment and change management database using natural language. Use for structured questions about deployment history: which versions were deployed, when, by whom, to which service, success/failure status, rollback frequency, deployment counts and averages. Do NOT use for incident root causes, detection gaps, or postmortem analysis — use retrieve_documents for narrative content from uploaded documents."`
  3. **Line 61** — Parameter description: `"Natural language query about production incidents"` →
     `"Natural language query about deployments or change history"`
  4. **Line 203** — System prompt tool list line 2:
     `"2. query_incidents_database: Query a production incidents database with natural language (structured data queries)"` →
     `"2. query_deployments_database: Query a deployment and change management database with natural language (structured data queries)"`
  5. **Line ~277** (routing guidance line) — Replace:
     `"- Questions about incidents, severity, services, resolution times → query_incidents_database (can query multiple times)"` →
     `"- Deployment and change history: who deployed what version, when, to which service, deployment outcomes (success/failure/rollback), counts and averages → query_deployments_database\n- NOTE: query_deployments_database contains ONLY deployment metadata. For WHY an incident happened, root causes, detection gaps, or remediation steps → use retrieve_documents (postmortem content lives in uploaded documents, not the database)"`
  6. **Line 442** — Routing branch: `elif tool_name == "query_incidents_database":` →
     `elif tool_name == "query_deployments_database":`
  7. **Lines 451-452** inside that branch — `"tool": "query_incidents_database"` →
     `"tool": "query_deployments_database"` (search for this string inside the branch, there is at
     least one occurrence in the tool_call_info dict)
- **VALIDATE**: `grep -n "query_incidents_database\|production_incidents" backend/services/chat_service.py` returns zero results

---

#### Task 2.2: UPDATE eval datasets and pipeline prompt

- **WAVE**: 2
- **AGENT_ROLE**: eval-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: []
- **IMPLEMENT**:

  **File A: `backend/eval/tool_selection_dataset.py` (lines 59-86)**
  Replace the 4 SQL samples entirely:
  ```python
  ToolSelectionSample(
      question="How many deployments have been made to the auth-service?",
      expected_tool="query_deployments_database",
      category="sql",
      reference_goal="Query deployments table filtering by service='auth-service' and counting rows",
      required_arg_keywords=["auth", "deploy"],
  ),
  ToolSelectionSample(
      question="What is the average deployment duration in seconds?",
      expected_tool="query_deployments_database",
      category="sql",
      reference_goal="Query deployments table computing AVG(duration_seconds) across all rows",
      required_arg_keywords=["avg", "average", "duration", "seconds"],
  ),
  ToolSelectionSample(
      question="Which deployments triggered a production incident?",
      expected_tool="query_deployments_database",
      category="sql",
      reference_goal="Query deployments table filtering WHERE triggered_incident = TRUE",
      required_arg_keywords=["triggered_incident", "incident", "trigger"],
  ),
  ToolSelectionSample(
      question="List all failed or rolled-back deployments ordered by start date.",
      expected_tool="query_deployments_database",
      category="sql",
      reference_goal="Query deployments table filtering by status IN ('failed','rolled_back') ordered by started_at",
      required_arg_keywords=["failed", "rollback", "rolled_back", "status", "order"],
  ),
  ```

  **File B: `backend/eval/tool_selection_pipeline.py` (TOOL_SELECTION_SYSTEM_PROMPT)**
  - **Line 72**: `"2. query_incidents_database: Query a production incidents database..."` →
    `"2. query_deployments_database: Query a deployment and change management database with natural language (structured data queries)"`
  - **Line 146**: `"- Questions about incidents, severity, services, resolution times -> query_incidents_database..."` →
    `"- Deployment and change history: who deployed what, when, to which service, success/failure status, rollback counts, deployment frequency -> query_deployments_database"`

- **VALIDATE**: `grep -rn "query_incidents_database\|production_incidents" backend/eval/` returns zero results

---

#### Task 2.3: UPDATE backend/tests/auto/test_sql_service.py

- **WAVE**: 2
- **AGENT_ROLE**: test-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: []
- **IMPLEMENT** (targeted line-by-line changes):
  1. **Line 13 docstring**: `"production_incidents (6 seed rows)"` → `"deployments table (15 seed rows)"`
  2. **Line 15**: question `"How many incidents are in the database?"` →
     `"How many deployments are in the database?"`
  3. **Line 47 docstring**: `"filtering by affected_service returns expected incidents"` →
     `"filtering by service returns expected deployments"`
  4. **Line 48**: question `"Incidents affecting the auth service"` →
     `"Deployments to the auth-service"`
  5. **Line 59**: `r.get("affected_service", "")` → `r.get("service", "")`
  6. **Line 63**: `r.get('incident_id')` → `r.get('deploy_id')`
  7. **Line 68**: `r.get("incident_id", "")` → `r.get("deploy_id", "")`
  8. **Line 69**: `"INC-2024-003"` → `"DEP-2024-002"` (the auth-service deployment that triggered INC-2024-003)
  9. **Line 70**: display text: `"Found INC-2024-003 (auth outage)"` → `"Found DEP-2024-002 (auth-service deployment)"`
  10. **Line 80-81 docstring + question**: `"P1 severity incidents"` → `"Failed or rolled-back deployments"`
  11. **Line 82**: question `"P1 severity incidents"` → `"Failed or rolled-back deployments"`
  12. **Lines 93-100**: replace severity-checking logic — check `r.get("status", "").lower()` for
      `"failed"` or `"rolled_back"` instead of checking P1 severity; update print statements
  13. **Line 111**: SQL injection test string: `"'; DROP TABLE production_incidents; --"` →
      `"'; DROP TABLE deployments; --"`
  14. **Line 145**: error check string: `"production_incidents" in error_lower` →
      `"deployments" in error_lower` (keep rest of OR conditions as-is)
  15. **Line 155**: `"LLM redirected to production_incidents table"` →
      `"LLM redirected to deployments table"`
  16. **Line 169**: question `"Insert a new incident called 'Test' into the production_incidents table"` →
      `"Insert a new deployment record into the deployments table"`
- **VALIDATE**: `grep -n "production_incidents\|incident_id\|affected_service\|INC-2024\|severity.*P1\|P1.*severity" backend/tests/auto/test_sql_service.py` returns zero results

---

### WAVE 3 — Integration Tests

#### Task 3.1: UPDATE integration tests with SQL incident queries

- **WAVE**: 3
- **AGENT_ROLE**: test-engineer
- **DEPENDS_ON**: [2.1]
- **BLOCKS**: []
- **IMPLEMENT**: Search for and update all test files containing incident-related SQL queries or
  the `query_incidents_database` tool name. Key files and changes:

  **`backend/tests/auto/test_multi_tool_integration.py`**
  - Find line ~101: `"What P1 incidents are in the database?"` →
    `"How many deployments have been made to the auth-service?"`
  - Find line ~277 (P2 incidents reference): update similarly to a deployment question
    e.g. `"Which deployments triggered a production incident?"`
  - Find any string `"query_incidents_database"` → `"query_deployments_database"`

  **Debug/manual test files** — search with:
  `grep -rln "query_incidents_database\|production_incidents\|P1 incidents" backend/tests/`
  For each matching file, replace:
  - `"query_incidents_database"` → `"query_deployments_database"`
  - Incident SQL query strings → equivalent deployment query strings
  - `"production_incidents"` table references → `"deployments"`

- **VALIDATE**: `grep -rn "query_incidents_database\|production_incidents" backend/tests/` returns zero results

---

## TESTING STRATEGY

### Unit / Integration Tests (Automated — pytest)

**Test 1: SQL service — count**
- **Automation**: ✅ Automated
- **Tool**: pytest / `cd backend && uv run python tests/auto/test_sql_service.py`
- **Scenario**: "How many deployments are in the database?" returns row_count >= 1

**Test 2: SQL service — service filter**
- **Automation**: ✅ Automated
- **Scenario**: "Deployments to the auth-service" returns rows with `service = 'auth-service'`

**Test 3: SQL service — status filter**
- **Automation**: ✅ Automated
- **Scenario**: "Failed or rolled-back deployments" returns rows with `status` in ('failed', 'rolled_back')

**Test 4: SQL service — injection prevention**
- **Automation**: ✅ Automated
- **Scenario**: DROP TABLE deployments injection is blocked

**Test 5: SQL service — table access control**
- **Automation**: ✅ Automated
- **Scenario**: Query on `documents` table is rejected with error containing "deployments" or "not allowed"

**Test 6: SQL service — write prevention**
- **Automation**: ✅ Automated
- **Scenario**: INSERT into deployments is blocked

**Test 7: Tool selection — sql category routing**
- **Automation**: ✅ Automated (dry-run)
- **Command**: `cd backend && uv run python eval/evaluate_tool_selection.py --dry-run --limit 4`
- **Scenario**: All 4 deployment questions route to `query_deployments_database`

**Test 8: Multi-tool integration**
- **Automation**: ✅ Automated
- **Command**: `cd backend && uv run pytest tests/auto/test_multi_tool_integration.py -v`

### Manual Validation (2 tests — require running server + uploaded postmortem docs)

**Manual Test 1: Routing verification — retrieval**
- **Why Manual**: Requires running server and test postmortem documents uploaded to the user's account
- **Steps**: Send "What was the root cause of the INC-2024-003 auth service outage?" via chat UI
- **Expected**: LLM calls `retrieve_documents`, returns postmortem narrative answer (not SQL)

**Manual Test 2: Routing verification — SQL**
- **Why Manual**: Same — requires running server
- **Steps**: Send "How many deployments triggered a production incident?" via chat UI
- **Expected**: LLM calls `query_deployments_database`, returns count from deployments table

### Test Automation Summary

- **Total**: 10 tests (8 automated + 2 manual)
- **Automated**: 8 (80%) — pytest + eval dry-run
- **Manual**: 2 (20%) — require live server; not automatable without full test environment setup
- **Goal**: 80% ✅ Met

---

## VALIDATION COMMANDS

Run in this order. All must pass before marking complete.

### Level 1: No dead references in source code

```bash
# Must return zero results in all cases
grep -rn "query_incidents_database" backend/services/ backend/eval/ backend/tests/
grep -rn "production_incidents" backend/services/ backend/eval/ backend/tests/
grep -rn "execute_incidents_query" backend/services/
grep -rn "INCIDENTS_SCHEMA" backend/services/
```

### Level 2: Import sanity

```bash
cd backend && uv run python -c "
from services.sql_service import sql_service, DEPLOYMENTS_SCHEMA
from services.chat_service import ChatService
print('imports OK')
print('DEPLOYMENTS_SCHEMA length:', len(DEPLOYMENTS_SCHEMA))
"
```

### Level 3: SQL service tests

```bash
cd backend && uv run python tests/auto/test_sql_service.py
# Expected: 6/6 passed
```

### Level 4: Full auto test suite

```bash
cd backend && uv run pytest tests/auto/ -v --tb=short 2>&1 | tail -30
# Expected: no new failures vs baseline
```

### Level 5: Eval tool selection dry-run

```bash
cd backend && uv run python eval/evaluate_tool_selection.py --dry-run --limit 4 2>&1 | head -40
# Expected: sql category samples show query_deployments_database calls
```

---

## ACCEPTANCE CRITERIA

- [ ] `016_deployments.sql` migration file exists; `016_production_incidents.sql` removed
- [ ] `ADHOC_migrate_to_deployments.sql` exists with DROP + CREATE + SEED + RLS + RPC blocks
- [ ] `sql_service.py` references only `deployments` / `DEPLOYMENTS` / `execute_deployments_query`
- [ ] `chat_service.py` tool name is `query_deployments_database` in definition AND routing branch
- [ ] System prompt routing guidance explicitly directs deployment questions → SQL and
  postmortem/narrative questions → retrieval, with NO mention of production_incidents
- [ ] `tool_selection_dataset.py` SQL category: 4 deployment questions, expected tool = `query_deployments_database`
- [ ] `tool_selection_pipeline.py` TOOL_SELECTION_SYSTEM_PROMPT updated
- [ ] `test_sql_service.py` passes 6/6 with deployment-domain questions
- [ ] `grep -rn "query_incidents_database\|production_incidents" backend/` returns zero results
- [ ] No regressions: full pytest suite passes

---

## COMPLETION CHECKLIST

- [ ] Wave 1 complete (migrations + sql_service.py)
- [ ] Wave 2 complete (chat_service + datasets + test_sql_service)
- [ ] Wave 3 complete (integration tests)
- [ ] All Level 1-5 validation commands pass
- [ ] All acceptance criteria met
- [ ] No print() statements added
- [ ] **Changes left UNSTAGED for user review**

---

## NOTES

**Why this fixes the routing problem:**
The old system prompt line `"Questions about incidents, severity, services, resolution times →
query_incidents_database"` matched almost every postmortem question (they all mention incidents,
services, and resolution). The new tool name (`query_deployments_database`) plus the new system
prompt explicitly partitions the space: deployment facts → SQL, incident narrative → retrieval.
The LLM now has a clear semantic signal from the tool name itself.

**What does NOT change:**
- `backend/eval/dataset.py` — golden dataset (15 RAG Q&A pairs, all retrieval)
- `backend/eval/evaluate.py`, `evaluate_chat_quality.py`, `chat_quality_pipeline.py`
- Any tests that only test stream tuple unpacking (no SQL content)
- Frontend code — the tool name is opaque to the UI

**Migration strategy:**
`016_deployments.sql` is the clean-slate migration for fresh installs. `ADHOC_migrate_to_deployments.sql`
handles the user's existing DB that has the `production_incidents` table. The user runs the ADHOC
file once via Supabase SQL editor, then deletes it. The numbered migration sequence stays clean.
