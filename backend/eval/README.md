# RAGAS Evaluation Suite

Built-in evaluation for the RAG pipeline using [RAGAS](https://docs.ragas.io). Runs 15 golden Q&A pairs through the full retrieval + generation pipeline, scores them on four RAGAS metrics, and pushes per-sample results to LangSmith.

---

## What's scored

| Metric | What it measures |
|--------|-----------------|
| **Faithfulness** | Does the answer stay grounded in the retrieved context? (no hallucination) |
| **Answer Relevancy** | Is the answer on-topic and responsive to the question? |
| **Context Precision** | Are the retrieved chunks actually relevant to the question? |
| **Context Recall** | Did retrieval surface all the information needed to answer? |

---

## Golden dataset

15 hand-crafted Q&A pairs across 6 synthetic postmortem incident documents:

| Source document | # Questions | Aspects tested |
|----------------|-------------|----------------|
| `INC-2024-003-auth-outage.md` | 3 | Root cause, timeline, monitoring gap |
| `INC-2024-011-payment-db-corruption.md` | 2 | Root cause, remediation |
| `INC-2024-019-pipeline-memory-leak.md` | 2 | Root cause, detection gap |
| `INC-2024-027-gateway-timeout.md` | 3 | Root cause, timeline, remediation |
| `INC-2024-031-notif-queue-backup.md` | 2 | Root cause, detection gap |
| `INC-2024-038-deploy-rollback.md` | 2 | Root cause, remediation |
| Cross-document | 1 | Longest resolution time across all incidents |

All 15 questions are **in-distribution** — every answer is grounded in the postmortem documents. There are no off-topic queries in the RAGAS dataset (see Anti-hallucination tests below for that coverage).

The postmortem `.md` files live in `backend/eval/postmortems/`. Upload them via the app UI before running the evaluation.

---

## Anti-hallucination behavioral tests

Separate from RAGAS scoring, `tests/test_eval_pipeline.py` includes off-topic query tests that verify the pipeline returns a "No relevant context" fallback rather than fabricating answers:

- **Unit tests** (mocked retrieval): "What is the recipe for chocolate cake?", "Who won the FIFA World Cup in 2022?", "What is the current price of Bitcoin?"
- **Live integration test**: "What are the current cryptocurrency market prices?" — runs against the real retrieval stack

These tests run with the main test suite and don't require RAGAS or LangSmith.

---

## Running the evaluation

### Prerequisites

1. Postmortem docs uploaded via the app UI (`backend/eval/postmortems/*.md`)
2. `LANGSMITH_API_KEY` set in `backend/.env`
3. `TEST_EMAIL` / `TEST_PASSWORD` set in `backend/.env` (the account used to upload the docs)
4. Eval dependencies installed:

```bash
cd backend
uv pip install -r eval/requirements-eval.txt
```

### Run

```bash
cd backend
uv run python eval/evaluate.py
```

Output: aggregate scores printed to stdout + per-sample rows pushed to LangSmith under dataset `ir-copilot-golden-set`.

### Cohere free-tier note

If `RERANKING_PROVIDER=cohere` and you're on the free tier (10 requests/minute), the evaluation will hit a 429 at question 11. Use `RERANKING_PROVIDER=local` instead — it runs an on-device cross-encoder with no rate limits.

### Running unit tests only (no API calls)

```bash
cd backend
uv run python -m pytest eval/tests/ -v
```

### Running integration tests (requires live Supabase + ingested docs)

```bash
cd backend
uv run python -m pytest eval/tests/ -v -m integration
```

---

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
# or dry-run (no LangSmith push):
uv run python eval/evaluate_tool_selection.py --dry-run
```

---

## File structure

```
backend/eval/
├── dataset.py                    # 15 golden Q&A pairs (EvalSample dataclass)
├── pipeline.py                   # RAG pipeline wrapper for eval (retrieve + generate)
├── evaluate.py                   # Entry point: collects results, scores with RAGAS, pushes to LangSmith
├── tool_selection_dataset.py     # 12 single-turn + 3 multi-turn tool routing samples
├── tool_selection_pipeline.py    # Sends questions to LLM, captures tool call name + args
├── evaluate_tool_selection.py    # Scores routing/sequence/arg quality, pushes to LangSmith
├── postmortems/                  # 6 golden source documents (upload these via the app UI)
│   ├── INC-2024-003-auth-outage.md
│   ├── INC-2024-011-payment-db-corruption.md
│   ├── INC-2024-019-pipeline-memory-leak.md
│   ├── INC-2024-027-gateway-timeout.md
│   ├── INC-2024-031-notif-queue-backup.md
│   └── INC-2024-038-deploy-rollback.md
├── requirements-eval.txt
└── tests/
    ├── conftest.py
    ├── test_eval_pipeline.py
    └── test_tool_selection.py
```
