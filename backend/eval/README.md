# RAGAS Evaluation Suite

Three evaluation pipelines covering the full quality stack — from simplified retrieval through tool routing to end-to-end chat quality — with results pushed to LangSmith.

---

## Latest scores (2026-02-27, run 7)

### `evaluate.py` — simplified RAG pipeline (run 7)

| Metric | Score |
|--------|-------|
| faithfulness | **0.950** |
| answer_relevancy | **0.883** |
| context_precision | 0.567 |
| context_recall | **0.878** |

### `evaluate_tool_selection.py` — tool routing + arg quality (run 5)

| Metric | Score |
|--------|-------|
| routing accuracy (overall) | **1.000 (12/12)** |
| — retrieve | 1.000 (4/4) |
| — sql | 1.000 (4/4) |
| — web | 1.000 (4/4) |
| arg_keyword_relevance | **1.000 (12/12)** |
| multi-turn sequence accuracy | **1.000 (3/3)** |
| arg_quality / AgentGoalAccuracy | **0.917 (12 single-turn)** |

### `evaluate_chat_quality.py` — real ChatService end-to-end (run 4)

| Metric | Score |
|--------|-------|
| faithfulness | **0.941** |
| answer_relevancy | **0.969** |
| context_precision | 0.622 |
| context_recall | **0.800** |
| arg_keyword_relevance | **1.000 (15/15)** |

---

## Running the evals

### Prerequisites

1. Postmortem docs uploaded via the app UI (`backend/eval/postmortems/*.md`)
2. `TEST_EMAIL` / `TEST_PASSWORD` set in `backend/.env`
3. `LANGSMITH_API_KEY` set in `backend/.env`
4. Eval dependencies installed:

```bash
cd backend
uv pip install -r eval/requirements-eval.txt
```

### Run all three pipelines

```bash
# From project root:
cd backend && bash eval/run_evals.sh

# Dry run (print scores only, skip LangSmith push):
cd backend && bash eval/run_evals.sh --dry-run
```

### Run individual pipelines

```bash
cd backend

# RAG pipeline eval (retrieve → one-shot LLM completion)
uv run python eval/evaluate.py

# Chat quality eval (real ChatService agentic loop)
uv run python eval/evaluate_chat_quality.py

# Tool selection eval (routing accuracy + arg quality)
uv run python eval/evaluate_tool_selection.py
```

All scripts support `--dry-run` to skip LangSmith push.

### Rate limit notes

**Supabase RPC** — `evaluate.py` adds a 2-second delay between pipeline calls to stay under Supabase's free-tier RPC rate limit. Without this, calls 10–15 return HTTP errors whose headers are silently embedded in answers, zeroing context_recall for those samples.

**Cohere reranker** — if `RERANKING_PROVIDER=cohere` on the free tier (10 req/min), the eval hits a 429 at question 11. Use `RERANKING_PROVIDER=local` instead — it runs an on-device cross-encoder with no rate limits.

---

## Eval pipeline details

### 1. `evaluate.py` — simplified RAG pipeline

Calls `eval/pipeline.py` directly (no `chat_service.py`): retrieves top-k chunks for the question, runs a single structured LLM completion, scores with all four RAGAS metrics. Measures **retrieval quality and grounded response quality** in isolation from the agentic loop.

Output: scores printed to stdout + 15 per-sample rows pushed to LangSmith dataset `ir-copilot-golden-set`.

### 2. `evaluate_chat_quality.py` — real ChatService

Calls `chat_service.stream_response()` directly as a Python import (no HTTP server needed). This exercises the **full agentic loop**: tool selection → retrieval/SQL/web/subagent → LLM synthesis. Captures tool calls, retrieved contexts, and final response text. Scores with RAGAS + a deterministic keyword check on the retrieval query arg.

Additional metric — **arg_keyword_relevance**: checks that the query arg the LLM chose for `retrieve_documents` contains at least one domain keyword from the ground-truth list. 1.0 = match, 0.0 = miss. Free (no API calls).

Output: scores printed to stdout + 15 per-sample rows pushed to LangSmith dataset `ir-copilot-chat-quality`.

### 3. `evaluate_tool_selection.py` — tool routing + arg quality

Scores the LLM's routing decision across three passes:

| Pass | Metric | How |
|------|--------|-----|
| 1 | `tool_routing_accuracy` | Binary per sample — did the model call the right tool? (12 single-turn) |
| 2 | `sequence_accuracy` | Binary per sample — correct 2-step sequence? (3 multi-turn: retrieve → analyze) |
| 3a | `arg_keyword_relevance` | Deterministic keyword check on the query arg (12 single-turn, free) |
| 3b | `arg_quality` | RAGAS `AgentGoalAccuracy` LLM judge — do the args satisfy the reference goal? (12 single-turn only) |

Multi-turn samples are excluded from pass 3b: `AgentGoalAccuracyWithReference` does not handle multi-step reference goals reliably, producing 0 for every multi-turn sample regardless of actual arg quality. Sequence correctness for multi-turn is already captured by `sequence_accuracy`.

Supports `--single-only` to skip the multi-turn pipeline.

Output: scores printed to stdout + 15 per-sample rows pushed to LangSmith dataset `ir-copilot-tool-selection`.

---

## Golden dataset

15 hand-crafted Q&A pairs across 6 synthetic postmortem incident documents:

| Source document | Questions | Aspects tested |
|----------------|-----------|----------------|
| `INC-2024-003-auth-outage.md` | 3 | Root cause, timeline, monitoring gap |
| `INC-2024-011-payment-db-corruption.md` | 2 | Root cause, remediation |
| `INC-2024-019-pipeline-memory-leak.md` | 2 | Root cause, detection gap |
| `INC-2024-027-gateway-timeout.md` | 3 | Root cause, timeline, remediation |
| `INC-2024-031-notif-queue-backup.md` | 2 | Root cause, detection gap |
| `INC-2024-038-deploy-rollback.md` | 2 | Root cause, remediation |
| Cross-document | 1 | Longest resolution time across all incidents |

All 15 questions are **in-distribution** — every answer is grounded in the postmortem documents. The postmortem `.md` files live in `backend/eval/postmortems/`. Upload them via the app UI before running the evaluation.

---

## Anti-hallucination behavioral tests

Separate from RAGAS scoring, `tests/test_eval_pipeline.py` includes off-topic query tests that verify the pipeline returns a "No relevant context" fallback rather than fabricating answers:

- **Unit tests** (mocked retrieval): "What is the recipe for chocolate cake?", "Who won the FIFA World Cup in 2022?", "What is the current price of Bitcoin?"
- **Live integration test**: "What are the current cryptocurrency market prices?" — runs against the real retrieval stack

These run with the main test suite and don't require RAGAS or LangSmith.

---

## Running unit tests only (no API calls)

```bash
cd backend
uv run python -m pytest eval/tests/ -v
```

---

## File structure

```
backend/eval/
├── dataset.py                    # 15 golden Q&A pairs (EvalSample dataclass)
├── pipeline.py                   # Simplified RAG pipeline for eval (retrieve + one-shot LLM)
├── evaluate.py                   # Entry point: RAG pipeline scores + LangSmith push
├── chat_quality_pipeline.py      # Full ChatService pipeline wrapper for eval
├── evaluate_chat_quality.py      # Entry point: chat quality scores + LangSmith push
├── tool_selection_dataset.py     # 12 single-turn + 3 multi-turn routing samples
├── tool_selection_pipeline.py    # Captures tool call name + args from LLM
├── evaluate_tool_selection.py    # Routing/sequence/arg quality scores + LangSmith push
├── eval_utils.py                 # Shared helpers (get_eval_user_id, etc.)
├── run_evals.sh                  # One-command runner for all 3 pipelines
├── requirements-eval.txt         # Eval-only deps (ragas, datasets) — install separately
├── postmortems/                  # 6 golden source documents (upload via app UI)
│   ├── INC-2024-003-auth-outage.md
│   ├── INC-2024-011-payment-db-corruption.md
│   ├── INC-2024-019-pipeline-memory-leak.md
│   ├── INC-2024-027-gateway-timeout.md
│   ├── INC-2024-031-notif-queue-backup.md
│   └── INC-2024-038-deploy-rollback.md
└── tests/
    ├── conftest.py
    ├── test_eval_pipeline.py
    ├── test_chat_quality_pipeline.py
    └── test_tool_selection.py
```

---

## Why ragas is installed separately

`ragas` conflicts with the project's `pydantic-settings==2.5.2` pin via its `langchain-community` transitive dependency. Installing via `uv pip install -r eval/requirements-eval.txt` (rather than `uv sync`) installs into the already-resolved env without re-solving project constraints. Re-run after any `uv sync`.

---

## Known metric quirks

| Metric | Issue | Status |
|--------|-------|--------|
| `AgentGoalAccuracy` | Long JSON prompts hit `gpt-4o-mini` output token limit — truncated responses, all 0.0 | Fixed: switched to `gpt-4o`; multi-turn samples excluded (metric not designed for multi-step goals) |
| `AgentGoalAccuracy` multi-turn | Scores 0 for all multi-turn samples even when sequence is correct — metric limitation with multi-step reference goals | By design: multi-turn excluded from pass 3b; covered by `sequence_accuracy` instead |
| `context_precision` / `context_recall` | Were low (0.1–0.35) — root cause was dataset quality bug, not retrieval | Fixed: all 15 ground truths rewritten; run 6 shows context_recall 0.878 |
| Supabase RPC rate limiting | 15 questions fired without delay saturate Supabase's free-tier RPC limit (~10 rapid calls). Affected samples silently return `contexts=[]` and inject raw HTTP response headers into answers, corrupting RAGAS scores. | Fixed: `asyncio.sleep(2)` between pipeline calls in `evaluate.py` |
| RAGAS scoring wall time ~17 min | RAGAS runs all 60 scoring jobs in one parallel batch; wall time = slowest job. With `RETRIEVAL_LIMIT=10`, the faithfulness prompt (10 contexts × ~1000 chars) exceeds instructor's default `max_tokens=3072`, triggering 3 retries at ~5-6 min each. | Fixed: `evaluate.py` configures RAGAS LLM with `max_tokens=8192` |
| `pyarrow.dataset` import | DLL blocked by Windows Application Control — mocked at startup in all eval scripts | Fixed (harmless) |
