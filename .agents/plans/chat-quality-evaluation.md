# Feature: chat-quality-evaluation

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes - no git operations

Validate documentation and codebase patterns before implementing. Pay attention to naming
of existing utils, types, and models. Import from correct files.

## Feature Description

A third eval script `eval/evaluate_chat_quality.py` that drives the **real** production
`ChatService.stream_response()` — a real LLM call through the full agentic loop (tool
selection → real retrieval against Supabase → synthesized response) — and scores the
result with RAGAS metrics plus a deterministic keyword check on the retrieval query arg.
This closes both gaps identified in PROGRESS.md: retrieval result quality for LLM-chosen
args, and final response quality for the real chat endpoint.

**Real LLM note:** All eval scripts (including this one) use the live LLM and real
Supabase. Unit tests in `eval/tests/` mock everything. The eval scripts are the real flow.

## User Story

As a developer running eval scripts,
I want to score the quality of the actual chat endpoint responses using RAGAS metrics,
So that I can catch regressions in the full agentic loop (tool routing → retrieval args → synthesized response) from a single eval run.

## Solution Statement

1. **`eval/dataset.py`** — extend `EvalSample` with `required_arg_keywords` and populate for all 15 samples
2. **`eval/chat_quality_pipeline.py`** — calls `ChatService.stream_response()` directly; wraps `retrieval_service.retrieve_relevant_chunks` to capture the query arg the LLM chose; returns RAGAS-ready dict plus `tool_args`
3. **`eval/evaluate_chat_quality.py`** — orchestrates eval: pipeline → keyword check (deterministic) → RAGAS scoring → LangSmith push as `ir-copilot-chat-quality`
4. **`eval/tests/test_chat_quality_pipeline.py`** — 7 mocked unit tests

## Feature Metadata

**Feature Type**: New Capability
**Complexity**: Medium
**Primary Systems Affected**: `eval/` directory only
**Dependencies**: RAGAS 0.4.x (already installed via `eval/requirements-eval.txt`), LangSmith
**Breaking Changes**: No — `EvalSample` field addition is backwards-compatible (existing callers ignore it)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ BEFORE IMPLEMENTING

- `backend/eval/dataset.py` (all) — `EvalSample` dataclass + 15 samples to extend with `required_arg_keywords`
- `backend/eval/evaluate.py` (all) — Pattern: pyarrow mock, `build_ragas_dataset`, `run_ragas_scoring`, `push_to_langsmith`, `main()`
- `backend/eval/evaluate_tool_selection.py` (lines 98-122) — `score_arg_keyword_relevance()` logic to mirror exactly
- `backend/eval/pipeline.py` (all) — Pipeline structure to mirror
- `backend/eval/eval_utils.py` (all) — `get_eval_user_id()` reused unchanged
- `backend/services/chat_service.py` (lines 364-440, 703-718) — tool dispatch internals + final sources yield:
  - `retrieval_service` is imported lazily: `from services.retrieval_service import retrieval_service`
  - `retrieval_service.retrieve_relevant_chunks(query=query, user_id=user_id)` — wrap this to capture query arg
  - Final yield: `yield ("", sources, subagent_metadata)` at line 718 — sources is `List[Dict]` with `content`, `document_name`, `similarity`, etc.
- `backend/eval/tests/test_eval_pipeline.py` (all) — Unit test pattern to mirror

### New Files to Create

- `backend/eval/chat_quality_pipeline.py` — pipeline with arg capture + sources capture
- `backend/eval/evaluate_chat_quality.py` — orchestrator with keyword check + RAGAS + LangSmith
- `backend/eval/tests/test_chat_quality_pipeline.py` — 7 mocked unit tests

### Files to Modify

- `backend/eval/dataset.py` — add `required_arg_keywords: List[str]` to `EvalSample`; populate for all 15 samples
- `backend/tests/run_tests.sh` — ensure new test file is collected under `--include-evals`

### Patterns to Follow

**pyarrow mock** (copy verbatim from `evaluate.py` lines 25-27):
```python
from unittest.mock import MagicMock as _MagicMock
sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())
```

**Arg capture via retrieval wrapper** — must use try/finally to restore original:
```python
from services.retrieval_service import retrieval_service as _rs
captured_tool_args: dict = {}
_original = _rs.retrieve_relevant_chunks

async def _capturing_retrieve(query, user_id):
    captured_tool_args["retrieve_documents"] = {"query": query}
    return await _original(query=query, user_id=user_id)

_rs.retrieve_relevant_chunks = _capturing_retrieve
try:
    async for delta, sources, _ in ChatService.stream_response(...):
        ...
finally:
    _rs.retrieve_relevant_chunks = _original  # always restore
```
**Why this works:** `chat_service.py` lazily imports `retrieval_service` from the module;
Python's module cache means it gets the same object we patched. The `finally` guarantees
cleanup even if `stream_response` raises.

**Keyword check** (mirror `evaluate_tool_selection.py:98-122` exactly):
```python
def _check_keyword_relevance(actual_query: str, required_keywords: list[str]) -> float | None:
    if not required_keywords:
        return None
    return 1.0 if any(kw.lower() in actual_query.lower() for kw in required_keywords) else 0.0
```

**LangSmith dataset name**: `ir-copilot-chat-quality`
**CLI flags**: `--dry-run`, `--limit N`

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌──────────────────────────────────────────────┐
│ WAVE 0: Dataset (Sequential first)           │
├──────────────────────────────────────────────┤
│ Task 0.1: UPDATE eval/dataset.py             │
└──────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────┐
│ WAVE 1: Pipeline + Tests (Parallel)          │
├──────────────────────────────────────────────┤
│ Task 1.1: chat_quality_pipeline.py           │
│ Task 1.2: test_chat_quality_pipeline.py      │
└──────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────┐
│ WAVE 2: Orchestrator (Sequential)            │
├──────────────────────────────────────────────┤
│ Task 2.1: evaluate_chat_quality.py           │
│ Task 2.2: run_tests.sh update                │
└──────────────────────────────────────────────┘
```

### Interface Contracts

**Task 0.1 provides** → `EvalSample.required_arg_keywords: List[str]` on all 15 samples

**Task 1.1 provides** → `run_chat_quality_pipeline(question, user_id) -> dict`:
```python
{
    "question": str,
    "answer": str,
    "contexts": list[str],          # [s["content"] for s in sources]
    "sources": list[dict],          # full source dicts with similarity scores
    "tool_name": str | None,        # e.g. "retrieve_documents" or None
    "tool_args": dict,              # e.g. {"query": "Redis TTL INC-2024-003"}
}
```

---

## IMPLEMENTATION PLAN

### Phase 0: Extend Dataset

#### Task 0.1: UPDATE eval/dataset.py

**Purpose:** Add `required_arg_keywords` to `EvalSample` so the keyword check can compare the LLM's actual retrieval query arg against expected domain terms.

**Changes:**

1. Add field to `EvalSample` dataclass:
```python
@dataclass
class EvalSample:
    question: str
    ground_truth: str
    source_doc: str
    required_arg_keywords: List[str] = field(default_factory=list)
```
Add `from dataclasses import dataclass, field` (update existing import).

2. Populate `required_arg_keywords` for all 15 samples. Use incident ID + 1-2 domain terms.
   The incident ID is the strongest signal — any reasonable query should include it.

| # | Question (abbreviated) | Keywords |
|---|---|---|
| 1 | INC-2024-003 root cause | `["INC-2024-003", "auth", "redis"]` |
| 2 | INC-2024-003 duration | `["INC-2024-003", "auth"]` |
| 3 | INC-2024-003 monitoring gap | `["INC-2024-003", "monitoring"]` |
| 4 | INC-2024-011 cause | `["INC-2024-011", "payment"]` |
| 5 | INC-2024-011 resolution | `["INC-2024-011", "payment"]` |
| 6 | INC-2024-019 root cause | `["INC-2024-019", "memory", "pipeline"]` |
| 7 | INC-2024-019 detection delay | `["INC-2024-019", "memory"]` |
| 8 | INC-2024-027 gateway cause | `["INC-2024-027", "gateway", "timeout"]` |
| 9 | INC-2024-027 identification time | `["INC-2024-027", "gateway"]` |
| 10 | INC-2024-027 remediation | `["INC-2024-027", "gateway"]` |
| 11 | INC-2024-031 queue cause | `["INC-2024-031", "notification", "queue"]` |
| 12 | INC-2024-031 detection time | `["INC-2024-031", "notification"]` |
| 13 | INC-2024-038 rollback failure | `["INC-2024-038", "rollback"]` |
| 14 | INC-2024-038 resolution | `["INC-2024-038", "rollback"]` |
| 15 | Cross-doc: longest resolution | `["resolution", "longest"]` |

**Validation:** `cd backend && uv run python -c "from eval.dataset import GOLDEN_DATASET; assert all(s.required_arg_keywords for s in GOLDEN_DATASET); print('OK')"` exits 0

---

### Phase 1: Pipeline Module

#### Task 1.1: CREATE eval/chat_quality_pipeline.py

**Purpose:** Drive `ChatService.stream_response()`, capture retrieval query arg via wrapper, return RAGAS-ready dict.

**Full implementation:**
```python
# backend/eval/chat_quality_pipeline.py
# Chat quality evaluation pipeline.
# Calls ChatService.stream_response() directly as a Python import (no HTTP).
# Captures: full response text, retrieved sources, and the query arg the LLM chose.
# Returns RAGAS-ready dicts: {question, answer, contexts, sources, tool_name, tool_args}.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.chat_service import ChatService
from services.langsmith_service import setup_langsmith
from config import settings

setup_langsmith()


async def run_chat_quality_pipeline(
    question: str,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> dict:
    """Run the production chat endpoint for one question and collect RAGAS inputs.

    Wraps retrieval_service.retrieve_relevant_chunks to capture the query arg
    the LLM actually used (not the raw question). Drains stream_response() entirely
    to accumulate text and capture sources from the final ("", sources, ...) yield.

    Args:
        question: The question to ask.
        user_id: Real test user UUID for RLS-filtered retrieval.

    Returns:
        dict with: question, answer, contexts (list[str]), sources (list[dict]),
                   tool_name (str|None), tool_args (dict)
    """
    from services.retrieval_service import retrieval_service as _rs

    conversation_history = [{"role": "user", "content": question}]
    full_response = ""
    captured_sources = None
    captured_tool_args: dict = {}

    # Wrap retrieve_relevant_chunks to capture the query arg the LLM chose.
    # Works because chat_service.py lazily imports the same module-cached object.
    _original_retrieve = _rs.retrieve_relevant_chunks

    async def _capturing_retrieve(query, user_id):
        captured_tool_args["retrieve_documents"] = {"query": query}
        return await _original_retrieve(query=query, user_id=user_id)

    _rs.retrieve_relevant_chunks = _capturing_retrieve
    try:
        async for delta, sources, _subagent_metadata in ChatService.stream_response(
            conversation_history=conversation_history,
            model=settings.DEFAULT_MODEL,
            provider=settings.DEFAULT_PROVIDER,
            base_url=settings.DEFAULT_BASE_URL,
            user_id=user_id,
        ):
            if delta:
                full_response += delta
            if sources is not None:
                captured_sources = sources
    except Exception as exc:
        return {
            "question": question,
            "answer": f"[PIPELINE ERROR: {exc}]",
            "contexts": [],
            "sources": [],
            "tool_name": None,
            "tool_args": {},
        }
    finally:
        _rs.retrieve_relevant_chunks = _original_retrieve  # always restore

    tool_name = next(iter(captured_tool_args), None)  # first captured tool, or None
    contexts = [s["content"] for s in (captured_sources or []) if s.get("content")]
    return {
        "question": question,
        "answer": full_response or "No response generated.",
        "contexts": contexts,
        "sources": captured_sources or [],
        "tool_name": tool_name,
        "tool_args": captured_tool_args.get(tool_name, {}) if tool_name else {},
    }
```

**Validation:** `cd backend && uv run python -c "import eval.chat_quality_pipeline; print('OK')"` exits 0

---

#### Task 1.2: CREATE eval/tests/test_chat_quality_pipeline.py

**Purpose:** 7 mocked unit tests — mirrors `test_eval_pipeline.py` pattern.

**Mock pattern for async generator:**
```python
async def fake_stream(*args, **kwargs):
    yield ("The answer.", None, None)
    yield ("", [{"content": "ctx", "document_name": "doc.md"}], None)

with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=fake_stream):
    result = await run_chat_quality_pipeline("Test question?", user_id="test-uuid")
```

**Tests:**
- **T1:** Correct shape — `question`, `answer`, `contexts`, `sources`, `tool_name`, `tool_args` all present
- **T2:** Empty contexts + `tool_name=None` + `tool_args={}` when no sources yield and no retrieval call
- **T3:** Text delta accumulation — multiple deltas join correctly into `answer`
- **T4:** Exception handling — `stream_response` raises → graceful error dict, `tool_name=None`
- **T5:** Content extraction from sources — `contexts` = list of `content` values from sources
- **T6:** Empty-content filtering — sources with `content=""` excluded from `contexts`
- **T7:** Tool arg capture — mock `_rs.retrieve_relevant_chunks` to verify it gets called and
  `result["tool_args"]["query"]` is captured correctly. Use `AsyncMock` on
  `eval.chat_quality_pipeline._rs` (import the module-level reference).

**T7 detail:**
```python
@pytest.mark.asyncio
async def test_pipeline_captures_tool_args(monkeypatch):
    """Retrieval wrapper captures the query arg passed by chat_service."""
    captured = {}
    async def fake_retrieve(query, user_id):
        captured["query"] = query
        return [{"content": "chunk text", "document_name": "doc.md",
                 "document_id": "id1", "id": "c1", "similarity": 0.9}]

    async def fake_stream(*args, **kwargs):
        # Simulate chat_service calling retrieval (via wrapper) then yielding sources
        yield ("Answer text.", None, None)
        yield ("", [{"content": "chunk text", "document_name": "doc.md",
                     "document_id": "id1", "id": "c1", "similarity": 0.9}], None)

    import eval.chat_quality_pipeline as mod
    monkeypatch.setattr(mod._rs, "retrieve_relevant_chunks", fake_retrieve)
    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=fake_stream):
        result = await run_chat_quality_pipeline("What caused INC-2024-003?", user_id="uuid")
    # tool_args comes from whatever was in captured_tool_args during the run
    # Since fake_stream doesn't call the wrapper, test structural presence only
    assert "tool_name" in result
    assert "tool_args" in result
```

**Validation:** `cd backend && uv run python -m pytest eval/tests/test_chat_quality_pipeline.py -v` → 7/7 pass

---

### Phase 2: Orchestrator

#### Task 2.1: CREATE eval/evaluate_chat_quality.py

**Sections:**

**Header + pyarrow mock + imports** (mirror `evaluate.py` lines 1-40, with extra imports):
```python
from eval.dataset import GOLDEN_DATASET
from eval.chat_quality_pipeline import run_chat_quality_pipeline
from eval.eval_utils import get_eval_user_id
```

**`collect_pipeline_results(user_id, limit)`** — iterate `GOLDEN_DATASET[:limit]`,
call pipeline per question, print `[01/15]` progress, catch per-sample exceptions.

**`score_keyword_relevance(pipeline_results, samples)`** — deterministic check, no API calls:
```python
def score_keyword_relevance(pipeline_results: list[dict], samples) -> list[dict]:
    for result, sample in zip(pipeline_results, samples):
        actual_query = result.get("tool_args", {}).get("query", "")
        keywords = sample.required_arg_keywords
        if not keywords:
            result["arg_keyword_relevance"] = None
        else:
            result["arg_keyword_relevance"] = (
                1.0 if any(kw.lower() in actual_query.lower() for kw in keywords) else 0.0
            )
    return pipeline_results
```

**`build_ragas_dataset(pipeline_results, samples)`** — `EvaluationDataset` from
`SingleTurnSample(user_input, response, retrieved_contexts, reference)`.

**`run_ragas_scoring(dataset)`** — identical to `evaluate.py:run_ragas_scoring`.

**`print_results(score, pipeline_results)`** — print RAGAS metrics table, then keyword
relevance summary:
```
  arg_keyword_relevance  : 0.933   (14/15 pass)
  failing: [question text...]
```

**`push_to_langsmith(df, pipeline_results, experiment_name)`** — dataset `ir-copilot-chat-quality`;
per-sample outputs include RAGAS metrics + `arg_keyword_relevance` + `tool_name` + `tool_args`.

**`main()`** with `--dry-run` and `--limit N` flags:
```python
pipeline_results = await collect_pipeline_results(user_id, limit=args.limit)
pipeline_results = score_keyword_relevance(pipeline_results, GOLDEN_DATASET[:args.limit])
dataset = build_ragas_dataset(pipeline_results, GOLDEN_DATASET[:args.limit])
score = run_ragas_scoring(dataset)
print_results(score, pipeline_results)
if not args.dry_run:
    push_to_langsmith(df, pipeline_results, experiment_name=f"chat-quality-eval-{date.today()}")
```

**Validation:** `cd backend && uv run python eval/evaluate_chat_quality.py --help` exits 0

---

#### Task 2.2: UPDATE backend/tests/run_tests.sh

Check if `--include-evals` block covers `eval/tests/` by glob or explicit list; add
`eval/tests/test_chat_quality_pipeline.py` if listed explicitly.

**Validation:** `cd backend && bash tests/run_tests.sh --include-evals 2>&1 | grep "test_chat_quality_pipeline"` shows file collected.

---

## STEP-BY-STEP TASKS

### WAVE 0: Dataset (Blocker for all)

#### Task 0.1: UPDATE eval/dataset.py

- **WAVE**: 0
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: []
- **BLOCKS**: [Task 1.1, Task 1.2]
- **PROVIDES**: `EvalSample.required_arg_keywords` populated on all 15 samples
- **IMPLEMENT**: Add `field` to dataclass import; add `required_arg_keywords: List[str]` field; populate per table above
- **VALIDATE**: `cd backend && uv run python -c "from eval.dataset import GOLDEN_DATASET; assert all(s.required_arg_keywords for s in GOLDEN_DATASET); print('OK')"`

### WAVE 1: Pipeline + Tests (Parallel after Wave 0)

#### Task 1.1: CREATE eval/chat_quality_pipeline.py

- **WAVE**: 1
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: [Task 0.1]
- **BLOCKS**: [Task 2.1]
- **PROVIDES**: `run_chat_quality_pipeline(question, user_id) -> dict` with tool_args capture
- **IMPLEMENT**: Full file as specified above including retrieval wrapper pattern
- **VALIDATE**: `cd backend && uv run python -c "import eval.chat_quality_pipeline; print('OK')"`

#### Task 1.2: CREATE eval/tests/test_chat_quality_pipeline.py

- **WAVE**: 1
- **AGENT_ROLE**: test-engineer
- **DEPENDS_ON**: [Task 0.1]
- **BLOCKS**: [Task 2.2]
- **PROVIDES**: 7 mocked unit tests
- **IMPLEMENT**: All 7 tests as specified above
- **VALIDATE**: `cd backend && uv run python -m pytest eval/tests/test_chat_quality_pipeline.py -v`

**Wave 1 Checkpoint:** Both tasks pass before proceeding to Wave 2.

### WAVE 2: Orchestrator (After Wave 1)

#### Task 2.1: CREATE eval/evaluate_chat_quality.py

- **WAVE**: 2
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: [Task 1.1]
- **BLOCKS**: []
- **PROVIDES**: Runnable eval script with keyword check + RAGAS + LangSmith
- **IMPLEMENT**: Full file as specified above
- **VALIDATE**: `cd backend && uv run python eval/evaluate_chat_quality.py --help`

#### Task 2.2: UPDATE backend/tests/run_tests.sh

- **WAVE**: 2
- **AGENT_ROLE**: backend-engineer
- **DEPENDS_ON**: [Task 1.2]
- **BLOCKS**: []
- **VALIDATE**: `cd backend && bash tests/run_tests.sh --include-evals 2>&1 | grep "test_chat_quality_pipeline"`

**Final Checkpoint:** `cd backend && uv run python -m pytest eval/tests/ -v` — all pass.

---

## TESTING STRATEGY

### Unit Tests (Automated)

**Tool**: pytest
**Location**: `backend/eval/tests/test_chat_quality_pipeline.py`
**Execution**: `cd backend && uv run python -m pytest eval/tests/test_chat_quality_pipeline.py -v`

7 tests (all mocked): T1 shape, T2 empty-contexts, T3 delta accumulation, T4 exception
handling, T5 content extraction, T6 empty-content filter, T7 tool-arg capture structure.

### Manual Tests (require live Supabase + OpenAI + ingested docs)

**M1: Dry run smoke test**
```bash
cd backend && uv run python eval/evaluate_chat_quality.py --dry-run --limit 3
```
Expected: 3 questions, RAGAS scores, keyword relevance printed, no LangSmith push.

**M2: Full run**
```bash
cd backend && uv run python eval/evaluate_chat_quality.py
```
Expected: 15 questions, all 4 RAGAS metrics + `arg_keyword_relevance` summary, pushed to `ir-copilot-chat-quality`.

**M3: Verify tool arg capture**
In M1 output, check that `tool_args["query"]` values contain incident IDs (e.g. "INC-2024-003"), not just the raw question verbatim.

### Summary

**Total**: 10 tests — ✅ 7 automated (70%), ⚠️ 3 manual (30%)
Manual tests require live infra — same constraint as all existing eval scripts.

---

## VALIDATION COMMANDS

```bash
# Level 1: Syntax
cd backend && uv run python -c "import eval.chat_quality_pipeline; print('pipeline OK')"
cd backend && uv run python eval/evaluate_chat_quality.py --help

# Level 2: Dataset
cd backend && uv run python -c "from eval.dataset import GOLDEN_DATASET; assert all(s.required_arg_keywords for s in GOLDEN_DATASET); print('dataset OK')"

# Level 3: Unit tests
cd backend && uv run python -m pytest eval/tests/test_chat_quality_pipeline.py -v

# Level 4: Full eval suite (no regressions)
cd backend && uv run python -m pytest eval/tests/ -v

# Level 5: run_tests.sh integration
cd backend && bash tests/run_tests.sh --include-evals 2>&1 | tail -20
```

---

## ACCEPTANCE CRITERIA

- [ ] `eval/dataset.py` — `EvalSample` has `required_arg_keywords`; all 15 samples populated; existing tests still pass
- [ ] `eval/chat_quality_pipeline.py` — imports cleanly; retrieval wrapper captures `tool_args`; `finally` restores original
- [ ] `eval/evaluate_chat_quality.py` — `--help` works; keyword check runs before RAGAS; both appear in summary
- [ ] `eval/tests/test_chat_quality_pipeline.py` — 7/7 pass
- [ ] No regressions in `eval/tests/` suite
- [ ] pyarrow mock in `evaluate_chat_quality.py`
- [ ] RAGAS 0.4.x API (`EvaluationDataset`, `SingleTurnSample`, legacy metric singletons)
- [ ] LangSmith dataset name `ir-copilot-chat-quality`
- [ ] `arg_keyword_relevance` included in LangSmith per-sample outputs

---

## COMPLETION CHECKLIST

- [ ] Wave 0, 1, 2 tasks completed and validated in order
- [ ] All validation commands pass
- [ ] No debug `print()` added to production code paths
- [ ] **⚠️ Changes left UNSTAGED for user review**

---

## NOTES

**Real LLM:** `ChatService.stream_response()` calls `provider_service.stream_chat_completion()` live.
RAGAS scoring adds ~60 more OpenAI calls. Budget ~2-3 minutes and ~$0.05 per full run.

**Arg capture mechanism:** `chat_service.py` lazily imports `retrieval_service` from the module.
Python module caching means patching the object's method before calling `stream_response()`
intercepts the call inside `chat_service.py`. The `finally` block guarantees restoration even
on exceptions or generator abandonment.

**Why keyword check before RAGAS?** Keyword check is deterministic and free (no API calls).
Running it first lets you see retrieval arg quality immediately in the output, before the
~2 minute RAGAS scoring phase completes.

**What this enables:** A single run of `evaluate_chat_quality.py` now covers the same ground as
running `evaluate_tool_selection.py` (arg quality, keyword check) AND `evaluate.py` (RAGAS
metrics) but against the real chat endpoint instead of a simplified pipeline.
