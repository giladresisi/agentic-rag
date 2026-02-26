# Feature: ragas-tool-call-accuracy

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs added during execution that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing

Validate codebase patterns before implementing. Pay attention to naming of existing
utils, types, and models. Import from correct files.

## Feature Description

Two related changes combined into one plan:

**1. Production incidents DB migration:** Replace the `books` demo table and all
references (`query_books_database` tool, `execute_books_query` RPC, `BOOKS_SCHEMA`,
system prompt text, tests) with a `production_incidents` table seeded from the 6
postmortem incidents. This makes the SQL tool coherent with the rest of the eval domain.

**2. RAGAS ToolCallAccuracy eval suite:** Add a tool-selection evaluation that scores
the LLM's routing accuracy using three mandatory metrics — custom `tool_routing_accuracy`
(name match, 0/1), `sequence_accuracy` for multi-turn sequences, and RAGAS
`AgentGoalAccuracy` (LLM-graded) for arg quality. Both single-turn and multi-turn
(retrieve → analyze) sequences are tested. The broken `ToolCallAccuracy(args={})` approach
(which always returns 0.0) is not used.

## Feature Metadata

**Feature Type**: Migration + New Capability
**Complexity**: Medium
**Primary Systems Affected**: `supabase/migrations/`, `backend/services/`,
`backend/tests/`, `backend/eval/`
**Dependencies**: No new packages (RAGAS AgentGoalAccuracy already installed)
**Breaking Changes**: Renames `query_books_database` → `query_incidents_database`
everywhere; existing tests updated in-place

---

## CONTEXT REFERENCES

### Must Read Before Implementing

- `supabase/migrations/013_sql_tool.sql` — books table + RPC to mirror for incidents
- `backend/services/sql_service.py` (all) — BOOKS_SCHEMA, _validate_query table check,
  execute_books_query RPC call, SQL system prompt
- `backend/services/chat_service.py` (lines 51-70, 203, 277, 442-505) — TEXT_TO_SQL_TOOL
  definition, system prompt line, routing hint line, tool dispatch block
- `backend/tests/auto/test_sql_service.py` (all) — all 6 test functions to rewrite
- `backend/tests/auto/test_multi_tool_integration.py` (lines 101-138, 252-338) —
  `test_books_query` and multi-tool sequence Turn 2 to rewrite
- `backend/eval/evaluate.py` (all) — orchestration pattern to mirror
- `backend/eval/pipeline.py` (all) — single-turn pipeline pattern
- `backend/eval/dataset.py` (all) — EvalSample dataclass + dataset list pattern
- `backend/eval/tests/test_eval_pipeline.py` (all) — unit test patterns
- `.venv/Lib/site-packages/ragas/metrics/collections/tool_call_accuracy/util.py` —
  `exact_match_args(pred, ref)` → returns `0.0` when `ref={}`, making
  `ToolCallAccuracy` unusable for free-text query args; confirmed: do NOT use it

### Scoring Design — Why ToolCallAccuracy Is Partially Unusable Here

`ToolCallAccuracy.ascore()` multiplies sequence_alignment × mean(arg_score).
`exact_match_args(pred, ref={})` returns `0.0` (not 1.0) when ref_args is empty,
so the total score is always 0.0 for correct name selection with free-text query args.
Even with non-empty reference args, exact string matching on LLM-generated query
strings will score 0 because the LLM phrases queries non-deterministically.

**Scoring approach used in this plan (all three passes are mandatory):**
- **Pass 1**: custom `tool_routing_accuracy` = mean(pred_name == expected_name, 0/1 per sample)
- **Pass 2**: custom `sequence_accuracy` = mean(pred_sequence == expected_sequence, multi-turn)
- **Pass 3**: RAGAS `AgentGoalAccuracy` — LLM-graded (binary 0/1), checks whether the
  tool call and args accomplish the `reference_goal`. Uses `gpt-4o-mini` via `llm_factory`.
  Init: `metric = AgentGoalAccuracyWithReference(llm=llm_factory("gpt-4o-mini", client=AsyncOpenAI()))`
  Score: `await metric.ascore(user_input=multi_turn.user_input, reference=sample.reference_goal)`
  Requires ~15 extra LLM calls (one per sample). Always runs, not gated on API key presence.

### New Files to Create

- `supabase/migrations/016_production_incidents.sql`
- `backend/eval/tool_selection_dataset.py`
- `backend/eval/tool_selection_pipeline.py`
- `backend/eval/evaluate_tool_selection.py`
- `backend/eval/tests/test_tool_selection.py`

### Files to Modify

- `supabase/rollback_all.sql` — add incidents table/function to rollback
- `backend/services/sql_service.py` — schema, validate, RPC name, docstrings
- `backend/services/chat_service.py` — tool name/description, system prompt (3 lines),
  dispatch block
- `backend/tests/auto/test_sql_service.py` — rewrite all 6 test functions
- `backend/tests/auto/test_multi_tool_integration.py` — rewrite `test_books_query`,
  multi-tool Turn 2
- `backend/tests/auto/test_simple_strategic.py` — update query string
- `backend/tests/auto/test_debug_stream.py` — update query string
- `backend/tests/manual/test_strategic_final.py` — update query strings
- `backend/tests/manual/test_strategic_retrieval.py` — update query string
- `backend/eval/README.md` — document tool selection eval

### Patterns to Follow

**Migration numbering**: next is `016_` (last is `015_realtime_documents.sql`)
**Table validation pattern** (sql_service.py `_validate_query`): update string
`"BOOKS"` → `"PRODUCTION_INCIDENTS"` in two `if table_name !=` checks
**Dispatch pattern** (chat_service.py): `elif tool_name == "query_books_database":` → update string only, logic stays identical

---

## PARALLEL EXECUTION STRATEGY

```
┌──────────────────────────────────────────────────────────────────┐
│ WAVE 0: DB Migration (must complete before any chat_service      │
│         changes are tested; parallel tasks safe to split)        │
├──────────────────────┬───────────────────────────────────────────┤
│ Task 0.1             │ Task 0.2                                  │
│ SQL migration + RPC  │ sql_service.py + chat_service.py updates  │
└──────────────────────┴───────────────────────────────────────────┘
                    ↓ (apply migration before Wave 1)
┌──────────────────────────────────────────────────────────────────┐
│ WAVE 1: Tests + Eval Dataset + Pipelines (Parallel)              │
├──────────────────────┬───────────────────┬───────────────────────┤
│ Task 1.1             │ Task 1.2          │ Task 1.3              │
│ Update all test      │ tool_selection_   │ tool_selection_       │
│ files (sql +         │ dataset.py        │ pipeline.py           │
│ multi-tool)          │                   │ (single + multi-turn) │
└──────────────────────┴───────────────────┴───────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────────┐
│ WAVE 2: Orchestration + Docs (Parallel)                          │
├──────────────────────────────────────┬───────────────────────────┤
│ Task 2.1                             │ Task 2.2                  │
│ evaluate_tool_selection.py           │ Update eval/README.md     │
└──────────────────────────────────────┴───────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────────┐
│ WAVE 3: Unit Tests                                               │
│ Task 3.1: test_tool_selection.py                                 │
└──────────────────────────────────────────────────────────────────┘
```

### Interface Contracts

**Task 0.1 provides** → `production_incidents` table + `execute_incidents_query` RPC
applied to Supabase; migration file committed to repo

**Task 0.2 provides** → Updated `sql_service.py` (INCIDENTS_SCHEMA, validate checks,
RPC name) + updated `chat_service.py` (tool name `query_incidents_database`, system
prompt, dispatch key)

**Task 1.2 provides** → `TOOL_SELECTION_DATASET: List[ToolSelectionSample]` and
`MULTI_TURN_DATASET: List[MultiTurnSelectionSample]`

**Task 1.3 provides** → `run_tool_selection_pipeline(question) -> (actual_name, MultiTurnSample)`
and `run_multiturn_pipeline(question) -> (actual_sequence, MultiTurnSample)`

**Task 2.1 consumes** → 1.2 + 1.3 interfaces; produces LangSmith dataset
`ir-copilot-tool-selection`

---

## IMPLEMENTATION PLAN

### WAVE 0: Production Incidents Migration

#### Task 0.1: CREATE `supabase/migrations/016_production_incidents.sql`

**New table schema** (derived from the 6 postmortem docs):
```sql
CREATE TABLE IF NOT EXISTS production_incidents (
    id SERIAL PRIMARY KEY,
    incident_id TEXT NOT NULL UNIQUE,       -- 'INC-2024-003'
    title TEXT NOT NULL,                    -- 'Auth Service Outage'
    affected_service TEXT NOT NULL,         -- 'auth', 'payment', 'pipeline', etc.
    severity TEXT NOT NULL,                 -- 'P1', 'P2'
    root_cause_category TEXT,               -- 'misconfiguration', 'migration_error', 'memory_leak', 'resource_exhaustion', 'overload'
    detection_gap_minutes INTEGER,          -- minutes from incident start to detection
    resolution_time_minutes INTEGER,        -- total resolution time in minutes
    incident_date DATE NOT NULL,
    status TEXT DEFAULT 'resolved'
);
```

**Seed data** (6 rows, one per postmortem):
```sql
INSERT INTO production_incidents (...) VALUES
('INC-2024-003','Auth Service Outage','auth','P1','misconfiguration',6,47,'2024-01-03','resolved'),
('INC-2024-011','Payment DB Corruption','payment','P1','migration_error',30,480,'2024-01-11','resolved'),
('INC-2024-019','Pipeline Memory Leak','pipeline','P2','memory_leak',371,200,'2024-01-19','resolved'),
('INC-2024-027','API Gateway Timeout Cascade','gateway','P1','resource_exhaustion',2,47,'2024-01-27','resolved'),
('INC-2024-031','Notification Queue Backup','notification','P2','overload',150,858,'2024-01-31','resolved'),
('INC-2024-038','Deployment Rollback Failure','deploy','P2','migration_error',NULL,120,'2024-02-07','resolved')
ON CONFLICT (incident_id) DO NOTHING;
```

**Permissions**: Mirror `013_sql_tool.sql` exactly — create `sql_query_role` if not
exists, GRANT SELECT, REVOKE write ops.

**RPC function**: `execute_incidents_query(query_text TEXT)` — same logic as
`execute_books_query` but validate `FROM PRODUCTION_INCIDENTS` instead of `FROM BOOKS`.

**Also update** `supabase/rollback_all.sql` — add:
```sql
DROP TABLE IF EXISTS production_incidents;
DROP FUNCTION IF EXISTS execute_incidents_query(TEXT);
```

**VALIDATE**: Apply migration against Supabase dev instance. Confirm table exists and
RPC returns data: `SELECT * FROM execute_incidents_query('SELECT * FROM production_incidents LIMIT 3');`

---

#### Task 0.2: UPDATE `sql_service.py` + `chat_service.py`

**`backend/services/sql_service.py` — all changes:**

1. Rename `BOOKS_SCHEMA` → `INCIDENTS_SCHEMA`, replace content:
```python
INCIDENTS_SCHEMA = """production_incidents table columns:
- id (INTEGER PRIMARY KEY)
- incident_id (TEXT) -- e.g. 'INC-2024-003'
- title (TEXT)
- affected_service (TEXT)
- severity (TEXT) -- 'P1' or 'P2'
- root_cause_category (TEXT)
- detection_gap_minutes (INTEGER)
- resolution_time_minutes (INTEGER)
- incident_date (DATE)
- status (TEXT)"""
```
2. `_get_sql_query_client` docstring: s/books table/production_incidents table/; s/execute_books_query/execute_incidents_query/
3. `_validate_query` docstring + body: s/books table/production_incidents table/; `table_name != "BOOKS"` → `table_name != "PRODUCTION_INCIDENTS"`; `table != "BOOKS"` → `table != "PRODUCTION_INCIDENTS"`; error messages updated
4. `natural_language_to_sql` docstring: s/books table/production_incidents table/
5. SQL system prompt messages: s/`{BOOKS_SCHEMA}`/`{INCIDENTS_SCHEMA}`/; s/ONLY query the 'books' table/ONLY query the 'production_incidents' table/
6. RPC call: `'execute_books_query'` → `'execute_incidents_query'`
7. Result context string `f"... ({sql_response.row_count} books):"` → `f"... ({sql_response.row_count} rows):"`

**`backend/services/chat_service.py` — all changes:**

1. `TEXT_TO_SQL_TOOL["function"]["name"]`: `"query_books_database"` → `"query_incidents_database"`
2. `TEXT_TO_SQL_TOOL["function"]["description"]`: Update to:
   `"Query a database of production incidents using natural language. Use for questions about incidents, severity, affected services, root causes, detection times, resolution times. Examples: 'P1 incidents in 2024', 'Incidents affecting auth service', 'Average resolution time by severity'"`
3. `TEXT_TO_SQL_TOOL["function"]["parameters"]["properties"]["query"]["description"]`:
   `"Natural language query about production incidents"`
4. System prompt line 203: `"2. query_books_database: Query a books database..."` →
   `"2. query_incidents_database: Query a production incidents database with natural language (structured data queries)"`
5. System prompt line 277: `"- Questions about books/authors/genres → query_books_database"` →
   `"- Questions about incidents, severity, services, resolution times → query_incidents_database"`
6. Dispatch block line 442: `elif tool_name == "query_books_database":` →
   `elif tool_name == "query_incidents_database":`
7. All string literals `"query_books_database"` in tool_calls_summary entries and LangSmith tracing calls → `"query_incidents_database"`
8. Context string `f"... ({sql_response.row_count} books):\n"` → `f"... ({sql_response.row_count} rows):\n"`
9. LangSmith `"table": "books"` → `"table": "production_incidents"`
10. Tool message `"name": "query_books_database"` → `"name": "query_incidents_database"`

**VALIDATE**: `cd backend && uv run python -c "from services.chat_service import ChatService; print(ChatService.TEXT_TO_SQL_TOOL['function']['name'])"`
Expected: `query_incidents_database`

---

### WAVE 1: Tests + Eval Dataset + Pipelines (Parallel)

#### Task 1.1: UPDATE all test files that reference books

For each file, replace book-domain queries with incident-domain queries. All files
except `test_sql_service.py` need only string updates; `test_sql_service.py` needs
logic rewrites because column names and expected values change.

**`backend/tests/auto/test_sql_service.py`** — rewrite all 6 test functions:

| Old test | New equivalent |
|----------|---------------|
| `test_count_query`: "How many books in DB?" | "How many incidents are in the database?" → expect `row_count >= 1` (6 rows) |
| `test_author_filter`: "Books by George Orwell" | "Incidents affecting the auth service" → expect `affected_service == 'auth'` |
| `test_genre_filter`: "Fantasy books" | "P1 severity incidents" → expect `severity == 'P1'` |
| `test_sql_injection`: unchanged logic | Update injection string to `'; DROP TABLE production_incidents; --'` |
| `test_table_access_control`: "Show records from documents" | Same query; update error message check from `"books"` → `"production_incidents"` |
| `test_write_prevention`: insert into books | `"Insert a new incident called 'Test' into the production_incidents table"` |

Key: check `affected_service`, `severity`, `incident_id` columns instead of `title`, `author`, `genre`.

**`backend/tests/auto/test_multi_tool_integration.py`:**
- `test_books_query` function: rename → `test_incidents_query`; change question to
  `"What P1 incidents are in the database?"` ; check response for "P1" / "INC-" / "auth"
  instead of "harry potter" / "rowling"; update `sources is None` assertion (still valid
  for SQL tool); update all `results["books"]` → `results["incidents"]` keys
- Multi-tool sequence Turn 2: question `"List some fantasy genre books"` →
  `"List all P2 incidents in the database"` ; `has_books` → `has_incidents`; check for
  `"P2"` / `"incident"` / `"INC-"` in response
- All `results["books_query"]` → `results["incidents_query"]`

**`backend/tests/auto/test_simple_strategic.py`:** Update multi-part question from
books to incidents, e.g., "1. What P1 incidents had resolution times over 100 minutes?
2. Which incidents affected the payment service?"

**`backend/tests/auto/test_debug_stream.py` (line 39):** Update query string from
books to incidents.

**`backend/tests/manual/test_strategic_final.py` + `test_strategic_retrieval.py`:**
Update all books query strings to incidents equivalents.

**VALIDATE**: `cd backend && uv run python -m pytest tests/auto/test_sql_service.py -v`
(requires live Supabase + migration applied; skip in CI with `--ignore` if needed)

---

#### Task 1.2: CREATE `backend/eval/tool_selection_dataset.py`

**Dataclasses:**
```python
@dataclass
class ToolSelectionSample:
    question: str
    expected_tool: str   # exact function name
    category: str        # "retrieve" | "sql" | "web"
    reference_goal: str  # AgentGoalAccuracy reference — what a correct tool call should accomplish

@dataclass
class MultiTurnSelectionSample:
    question: str
    expected_sequence: List[str]  # ordered list of tool names
    category: str        # "retrieve_then_analyze"
    reference_goal: str  # AgentGoalAccuracy reference — what the full agentic sequence should accomplish
```

**`TOOL_SELECTION_DATASET` — 12 single-turn samples (include `reference_goal` for each):**

4× `retrieve_documents` (postmortem questions):
- question: "What was the root cause of the INC-2024-003 auth service outage?"
  reference_goal: "Retrieve documents about INC-2024-003 with a query targeting the root cause of the auth outage"
- question: "What monitoring gap allowed the auth outage to go undetected for 6 minutes?"
  reference_goal: "Retrieve documents about INC-2024-003 with a query targeting the monitoring or detection gap"
- question: "How was the INC-2024-038 failed deployment rollback resolved?"
  reference_goal: "Retrieve documents about INC-2024-038 with a query targeting resolution or remediation steps"
- question: "What caused the API gateway timeout cascade in INC-2024-027?"
  reference_goal: "Retrieve documents about INC-2024-027 with a query targeting the API gateway timeout root cause"

4× `query_incidents_database` (structured incident queries):
- question: "Which incidents had a severity of P1?"
  reference_goal: "Query production_incidents filtered by severity='P1' to return P1 incidents"
- question: "What is the average resolution time across all incidents?"
  reference_goal: "Query production_incidents to compute AVG(resolution_time_minutes) across all rows"
- question: "Which incidents affected the payment service?"
  reference_goal: "Query production_incidents filtered by affected_service='payment'"
- question: "List all incidents sorted by detection gap in minutes."
  reference_goal: "Query production_incidents ordered by detection_gap_minutes"

4× `search_web` (real-time / current events):
- question: "What is the current weather in London right now today?"
  reference_goal: "Search the web for current real-time weather conditions in London"
- question: "What are the latest technology news headlines today?"
  reference_goal: "Search the web for today's technology news headlines"
- question: "What happened in the tech industry this week?"
  reference_goal: "Search the web for recent tech industry news from the current week"
- question: "What is the current Bitcoin price?"
  reference_goal: "Search the web for the current live Bitcoin price"

**`MULTI_TURN_DATASET` — 3 multi-turn samples (retrieve → analyze):**
- question: "Analyze the INC-2024-003 auth outage document in detail and extract all action items."
  reference_goal: "First retrieve documents about INC-2024-003, then delegate deep analysis to the subagent tool"
- question: "Give me a comprehensive summary of the payment database corruption incident."
  reference_goal: "First retrieve documents about INC-2024-011 payment DB corruption, then delegate analysis to the subagent tool"
- question: "Analyze the memory leak incident document and explain the detection gap."
  reference_goal: "First retrieve documents about INC-2024-019 memory leak, then delegate analysis to the subagent tool"

Each maps to `expected_sequence = ["retrieve_documents", "analyze_document_with_subagent"]`

**VALIDATE**: `cd backend && uv run python -c "from eval.tool_selection_dataset import TOOL_SELECTION_DATASET, MULTI_TURN_DATASET; assert len(TOOL_SELECTION_DATASET) == 12; assert len(MULTI_TURN_DATASET) == 3; print('OK')"`

---

#### Task 1.3: CREATE `backend/eval/tool_selection_pipeline.py`

**Two pipeline functions:**

**`run_tool_selection_pipeline(question, user_id) -> tuple[str|None, MultiTurnSample]`:**
Sends the question to the LLM with all 4 tools. Accumulates streaming tool_call deltas
(same pattern as `chat_service.py` lines 345-364). Stops when `finish_reason == "tool_calls"`.
Returns `(actual_tool_name, MultiTurnSample)` where `actual_tool_name` is the first
tool called (or `None` if the LLM chose to answer directly without tools).

```python
async def run_tool_selection_pipeline(
    question: str,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> tuple[str | None, MultiTurnSample]:
    messages = [
        {"role": "system", "content": TOOL_SELECTION_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls_buffer = []
    async for chunk in provider_service.stream_chat_completion(
        provider=settings.DEFAULT_PROVIDER,
        model=settings.DEFAULT_MODEL,
        messages=messages,
        base_url=settings.DEFAULT_BASE_URL,
        tools=ALL_TOOLS,
    ):
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                while len(tool_calls_buffer) <= tc_delta.index:
                    tool_calls_buffer.append({"name": "", "args_str": ""})
                buf = tool_calls_buffer[tc_delta.index]
                if tc_delta.function.name:
                    buf["name"] += tc_delta.function.name
                if tc_delta.function.arguments:
                    buf["args_str"] += tc_delta.function.arguments
        if chunk.choices[0].finish_reason in ("tool_calls", "stop"):
            break

    ragas_tool_calls = []
    for buf in tool_calls_buffer:
        try:
            args = json.loads(buf["args_str"]) if buf["args_str"] else {}
        except json.JSONDecodeError:
            args = {}
        ragas_tool_calls.append(ToolCall(name=buf["name"], args=args))

    actual_name = ragas_tool_calls[0].name if ragas_tool_calls else None
    sample = MultiTurnSample(
        user_input=[
            HumanMessage(content=question),
            AIMessage(content="", tool_calls=ragas_tool_calls or None),
        ]
    )
    return actual_name, sample
```

**`run_multiturn_pipeline(question, user_id) -> tuple[list[str], MultiTurnSample]`:**
Executes the full two-step agentic sequence:
1. Send question → LLM calls `retrieve_documents`
2. Actually execute `RetrievalService.retrieve_relevant_chunks(query, user_id)`
3. Append tool result to messages
4. Send again → LLM calls `analyze_document_with_subagent`
5. Capture both tool calls; return `(actual_sequence, MultiTurnSample)` with all
   messages in `user_input` (HumanMessage + AIMessage-with-tool-call-1 +
   ToolMessage-with-result + AIMessage-with-tool-call-2)

**`TOOL_SELECTION_SYSTEM_PROMPT`**: Copy verbatim from `chat_service.py`
`stream_response` system prompt (lines 205-295 approximately) so the LLM sees the
same routing instructions during eval as it does in production.

**`ALL_TOOLS`**: Import the 4 tool dicts from `ChatService` directly:
```python
from services.chat_service import ChatService
ALL_TOOLS = [
    ChatService.RETRIEVAL_TOOL,
    ChatService.TEXT_TO_SQL_TOOL,
    ChatService.WEB_SEARCH_TOOL,
    ChatService.ANALYZE_DOCUMENT_TOOL,
]
```

**VALIDATE**: `cd backend && uv run python -c "from eval.tool_selection_pipeline import run_tool_selection_pipeline, run_multiturn_pipeline; print('imports OK')"`

---

### WAVE 2: Orchestration + Docs (Parallel)

#### Task 2.1: CREATE `backend/eval/evaluate_tool_selection.py`

**Three scoring passes:**

**Pass 1 — Single-turn routing accuracy (12 samples):**
```python
async def collect_single_turn_results(user_id: str) -> list[dict]:
    results = []
    for sample in TOOL_SELECTION_DATASET:
        actual_name, multi_turn = await run_tool_selection_pipeline(
            sample.question, user_id
        )
        correct = int(actual_name == sample.expected_tool)
        results.append({
            "question": sample.question,
            "expected_tool": sample.expected_tool,
            "actual_tool": actual_name,
            "category": sample.category,
            "tool_routing_accuracy": correct,
            "_multi_turn": multi_turn,        # kept for Pass 3
            "_reference_goal": sample.reference_goal,
        })
    return results
```

**Pass 2 — Multi-turn sequence accuracy (3 samples):**
```python
async def collect_multiturn_results(user_id: str) -> list[dict]:
    results = []
    for sample in MULTI_TURN_DATASET:
        actual_seq, multi_turn = await run_multiturn_pipeline(
            sample.question, user_id
        )
        correct = int(actual_seq == sample.expected_sequence)
        results.append({
            "question": sample.question,
            "expected_sequence": sample.expected_sequence,
            "actual_sequence": actual_seq,
            "category": sample.category,
            "sequence_accuracy": correct,
            "_multi_turn": multi_turn,
            "_reference_goal": sample.reference_goal,
        })
    return results
```

**Pass 3 — Arg quality via AgentGoalAccuracy (all 15 samples):**
```python
async def score_arg_quality(all_results: list[dict]) -> list[dict]:
    from ragas.metrics.collections.agent_goal_accuracy.metric import AgentGoalAccuracyWithReference
    from ragas.llms.base import llm_factory
    from openai import AsyncOpenAI
    metric = AgentGoalAccuracyWithReference(
        llm=llm_factory("gpt-4o-mini", client=AsyncOpenAI())
    )
    for r in all_results:
        multi_turn = r.pop("_multi_turn")
        reference_goal = r.pop("_reference_goal")
        result = await metric.ascore(
            user_input=multi_turn.user_input,
            reference=reference_goal,
        )
        r["arg_quality"] = float(result.value)  # 0.0 or 1.0
    return all_results
```

Call order in `main()`:
```python
single_results = await collect_single_turn_results(user_id)
multi_results = await collect_multiturn_results(user_id)
all_results = await score_arg_quality(single_results + multi_results)
```

**Print summary:**
```
Tool Selection Evaluation
================================================================
Single-turn routing accuracy (12 samples):
  overall  : 0.833
  retrieve : 1.000   (4/4)
  sql      : 0.750   (3/4)
  web      : 0.750   (3/4)

Multi-turn sequence accuracy (3 samples):
  retrieve -> analyze : 0.667   (2/3)

Arg quality / AgentGoalAccuracy (15 samples):
  overall  : 0.867
================================================================
```

**LangSmith push**: Dataset name `"ir-copilot-tool-selection"`. Mirror pattern from
`evaluate.py:push_to_langsmith`. Each example:
- `inputs={"question": ..., "expected_tool": ..., "category": ...}`
- `outputs={"actual_tool": ..., "tool_routing_accuracy": ..., "arg_quality": ...}` (single-turn) OR
  `outputs={"actual_sequence": ..., "sequence_accuracy": ..., "arg_quality": ...}` (multi-turn)

**CLI args**: `--dry-run` skips LangSmith push. `--single-only` skips multi-turn
(useful when docs not ingested).

**pyarrow mock** (top of file, same as `evaluate.py` lines 24-27):
```python
from unittest.mock import MagicMock as _MagicMock
sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())
```

**VALIDATE**: `cd backend && uv run python eval/evaluate_tool_selection.py --dry-run --single-only`

---

#### Task 2.2: UPDATE `backend/eval/README.md`

Add after existing "Running the evaluation" section:

```markdown
## Tool Selection Evaluation

Scores the LLM's routing accuracy: does it call the right tool for each query type?

### Metrics

| Metric | How computed |
|--------|-------------|
| **tool_routing_accuracy** | Binary per sample (1 = correct tool, 0 = wrong), mean across 12 single-turn queries |
| **sequence_accuracy** | Binary per sample (1 = correct 2-step sequence, 0 = wrong), mean across 3 multi-turn queries |
| **arg_quality** | RAGAS `AgentGoalAccuracy` (LLM-graded, binary 0/1) — checks whether the tool call and args match the expected `reference_goal`; mean across all 15 samples |

*Note: RAGAS ToolCallAccuracy (with args={}) is not used — it returns 0.0 for correct
tool selection when reference args are empty, making it unsuitable for free-text queries.*

### Dataset

| Tool | # Single-turn | # Multi-turn |
|------|--------------|-------------|
| retrieve_documents | 4 | — |
| query_incidents_database | 4 | — |
| search_web | 4 | — |
| retrieve_documents → analyze_document_with_subagent | — | 3 |

### Run

```bash
cd backend
uv run python eval/evaluate_tool_selection.py
# or dry-run (no LangSmith):
uv run python eval/evaluate_tool_selection.py --dry-run
```
```

---

### WAVE 3: Unit Tests

#### Task 3.1: CREATE `backend/eval/tests/test_tool_selection.py`

Mirror `test_eval_pipeline.py` style: all mocked, no live API calls.

**Tests (9 total):**

1. `test_single_turn_dataset_has_12_entries` — `len == 12`, all fields non-empty,
   `expected_tool` in `{"retrieve_documents", "query_incidents_database", "search_web"}`,
   `category` in `{"retrieve", "sql", "web"}`

2. `test_dataset_covers_all_tools` — each category appears exactly 4 times

3. `test_multiturn_dataset_has_3_entries` — `len == 3`, each `expected_sequence ==
   ["retrieve_documents", "analyze_document_with_subagent"]`

4. `test_pipeline_captures_correct_tool_name` — mock `stream_chat_completion` to
   yield a fake tool_call chunk for `"retrieve_documents"` then a stop chunk;
   assert `actual_name == "retrieve_documents"` and `multi_turn.user_input[1].tool_calls[0].name == "retrieve_documents"`

5. `test_pipeline_handles_no_tool_call` — mock yields no tool_calls (LLM answers
   directly); assert `actual_name is None`, `multi_turn.user_input[1].tool_calls is None`

6. `test_pipeline_captures_tool_args` — mock yields tool_call with
   `args_str='{"query": "auth outage root cause"}'`; assert `tool_calls[0].args == {"query": "auth outage root cause"}`

7. `test_tool_routing_accuracy_correct` — `actual_name == expected_name` → score 1

8. `test_tool_routing_accuracy_wrong` — `actual_name != expected_name` → score 0

9. `test_multiturn_sequence_accuracy` — `actual_sequence == expected_sequence` → 1;
   wrong sequence → 0

10. `test_arg_quality_scoring_correct` — mock `AgentGoalAccuracyWithReference.ascore` to
    return `MetricResult(value=1.0)`; assert `arg_quality == 1.0`; verify `ascore` called
    with `user_input=multi_turn.user_input, reference=sample.reference_goal`

11. `test_dataset_has_reference_goals` — every entry in `TOOL_SELECTION_DATASET` and
    `MULTI_TURN_DATASET` has a non-empty `reference_goal` string

**Mock helper** (fake streaming chunk with tool_call delta):
```python
def make_tool_call_chunk(tool_name: str, args: str = '{"query": "test"}', index: int = 0):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].finish_reason = None
    tc = MagicMock()
    tc.index = index
    tc.function.name = tool_name
    tc.function.arguments = args
    chunk.choices[0].delta.tool_calls = [tc]
    chunk.choices[0].delta.content = None
    return chunk

def make_stop_chunk():
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].finish_reason = "tool_calls"
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].delta.content = None
    return chunk
```

**VALIDATE**: `cd backend && uv run python -m pytest eval/tests/test_tool_selection.py -v`
All 9 tests must pass.

---

## VALIDATION COMMANDS

### Level 0: Migration Applied
```bash
# Confirm production_incidents table exists and RPC works
# Run via Supabase dashboard SQL editor or psql
SELECT * FROM execute_incidents_query('SELECT incident_id, severity FROM production_incidents ORDER BY incident_id') LIMIT 6;
```
Expected: 6 rows with INC-2024-003 through INC-2024-038.

### Level 1: Service Imports + Tool Names
```bash
cd backend
uv run python -c "
from services.chat_service import ChatService
from services.sql_service import SQLService, INCIDENTS_SCHEMA
assert ChatService.TEXT_TO_SQL_TOOL['function']['name'] == 'query_incidents_database'
assert 'production_incidents' in INCIDENTS_SCHEMA
print('Level 1: OK')
"
```

### Level 2: Unit Tests
```bash
cd backend
uv run python -m pytest eval/tests/ -v
```
All tests must pass (existing + new).

### Level 3: Eval Dry Run
```bash
cd backend
uv pip install -r eval/requirements-eval.txt
uv run python eval/evaluate_tool_selection.py --dry-run --single-only
```
Expected: 12 questions run, scores printed, no LangSmith errors.

### Level 4: SQL Service Tests (requires live Supabase)
```bash
cd backend
uv run python tests/auto/test_sql_service.py
```
Expected: count/filter/security tests pass against `production_incidents`.

---

## ACCEPTANCE CRITERIA

- [ ] `production_incidents` table with 6 rows exists in Supabase; `execute_incidents_query` RPC works
- [ ] `query_books_database` has been replaced with `query_incidents_database` in all files
- [ ] `sql_service.py` validates against `PRODUCTION_INCIDENTS` table, calls `execute_incidents_query`
- [ ] All existing SQL tests updated and passing against new table
- [ ] `tool_selection_dataset.py` — 12 single-turn + 3 multi-turn samples
- [ ] `tool_selection_pipeline.py` — single-turn and multi-turn pipelines; captures tool name + args
- [ ] `evaluate_tool_selection.py` — all three scoring passes (routing, sequence, arg quality), summary print, LangSmith push, `--dry-run`
- [ ] `AgentGoalAccuracy` scores all 15 samples and `arg_quality` appears in print summary and LangSmith outputs
- [ ] 11 new unit tests pass (9 original + 2 AgentGoalAccuracy tests)
- [ ] Existing `pytest eval/tests/` suite still passes
- [ ] `eval/README.md` documents tool selection eval including why ToolCallAccuracy+args={} is not used

---

## NOTES

**Why not use RAGAS ToolCallAccuracy as the primary metric:**
`exact_match_args(pred, ref={})` returns `0.0` per the source at
`.venv/.../tool_call_accuracy/util.py` line 10: `if not ref_args: return 0.0`. This is
confirmed, not speculative. For free-text query args, exact string matching is also
too strict. Custom scoring (name equality mean) is more honest and interpretable.

**Multi-turn pipeline must execute retrieve_documents for real.** The LLM won't call
`analyze_document_with_subagent` without seeing actual document names from a prior
retrieval result. The multi-turn pipeline must do a real RetrievalService call and
inject the result as a ToolMessage before the second LLM call.

**AgentGoalAccuracy always runs (not gated).** The `score_arg_quality` function runs
for every sample after Passes 1 and 2 complete. It uses `gpt-4o-mini` (~15 extra LLM
calls). The `MultiTurnSample.user_input` returned by both pipeline functions already
contains `[HumanMessage, AIMessage(tool_calls)]` — sufficient for the metric to infer
the agent's end state without executing the actual tool or generating a final answer.
Import path: `ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference`

**SQL tool questions change from books to incidents.** The 4 eval dataset samples for
`query_incidents_database` use the `production_incidents` schema — they test that the
LLM routes incident-structured queries to the SQL tool, not the retrieval tool.
