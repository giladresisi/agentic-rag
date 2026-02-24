# Feature: ragas-evaluation-pipeline

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution that were NOT explicitly requested
- Keep pre-existing debug logs already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing
- Only make code changes — no git operations

Validate documentation and codebase patterns before implementing. Call services as Python imports (not via HTTP). Mirror patterns from existing test files in `backend/tests/auto/`.

## Feature Description

Add a reproducible RAG evaluation pipeline using the RAGAS library. The pipeline runs 15 golden Q&A pairs (drawn from postmortem markdown documents) through the actual retrieval + LLM services, scores them with four RAGAS metrics (faithfulness, answer_relevancy, context_precision, context_recall), and pushes results to LangSmith as a named Experiment. Evaluation is run manually by developers; it is not a CI job.

## User Story

As a developer or hiring manager reviewing this project,
I want to run a single command that produces objective RAG quality scores visible in LangSmith,
So that I can see quantitative evidence of the system's correctness and faithfulness.

## Problem Statement

Without evaluation, quality claims about the RAG pipeline are subjective. A reproducible, LLM-graded benchmark with LangSmith integration demonstrates professional engineering practice, makes the project showcase-worthy, and provides a baseline for detecting regressions after pipeline changes.

## Solution Statement

Create `backend/eval/` with three modules: `dataset.py` (golden Q&A pairs), `pipeline.py` (calls retrieval + LLM directly as Python imports), and `evaluate.py` (RAGAS scoring + LangSmith push). Add `ragas` to `requirements.txt`. Add mocked unit tests for the pipeline logic.

## Feature Metadata

**Feature Type**: New Capability
**Complexity**: Medium
**Primary Systems Affected**: New `backend/eval/` module; `requirements.txt`
**Dependencies**: `ragas>=0.2`, existing `langsmith`, `langsmith` SDK, postmortem docs from Plan 001
**Breaking Changes**: No — eval is additive, no production code paths modified

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `backend/services/retrieval_service.py` (lines 13–120) — `retrieve_relevant_chunks(query, user_id, limit, similarity_threshold, enable_reranking)` signature and return shape `[{"id","content","document_id","document_name","similarity",...}]`; uses `get_supabase_admin()` at line 62
- `backend/services/provider_service.py` (line 293) — `create_structured_completion(provider, model, messages, response_schema, base_url)` for structured Pydantic output; (line 375) `stream_chat_completion` for streaming — do NOT use streaming in eval
- `backend/config.py` (lines 30–37) — `DEFAULT_PROVIDER`, `DEFAULT_MODEL`, `DEFAULT_BASE_URL`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` — read these for eval config
- `backend/services/supabase_service.py` (line 22) — `get_supabase_admin()` — admin client bypasses RLS; correct pattern for eval
- `backend/services/langsmith_service.py` — `setup_langsmith()` — call this at eval startup to configure LangSmith env vars from settings
- `backend/tests/auto/test_sql_service.py` — pattern for async test runner with `asyncio.run(main())`; mirror for eval unit tests
- `backend/eval/postmortems/` — 6 markdown files created by Plan 001; these must be ingested via the app UI before running eval

### New Files to Create

- `backend/eval/__init__.py` — empty
- `backend/eval/dataset.py` — 15 golden Q&A pairs as `EvalSample` dataclass list
- `backend/eval/pipeline.py` — `run_rag_pipeline(question: str) -> dict` using retrieval_service + provider_service
- `backend/eval/evaluate.py` — entry point: loads dataset, runs pipeline, calls RAGAS, pushes to LangSmith
- `backend/eval/tests/__init__.py` — empty
- `backend/eval/tests/test_eval_pipeline.py` — mocked unit tests (no live API calls)

### Relevant Documentation — READ BEFORE IMPLEMENTING

- RAGAS evaluate API: https://docs.ragas.io/en/stable/references/evaluate/ — `evaluate(dataset, metrics)` signature; `EvaluationDataset` construction from list of dicts
- RAGAS metrics: https://docs.ragas.io/en/stable/concepts/metrics/ — `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall` imports and behaviour
- LangSmith SDK: https://docs.smith.langchain.com/reference/python — `Client().create_dataset()`, `create_example()` API
- RAGAS LangSmith integration: https://docs.ragas.io/en/stable/howtos/integrations/langsmith/ — check at implementation time whether `upload_to_langsmith` helper exists in installed version

### Patterns to Follow

**Async runner pattern**: `backend/tests/auto/test_sql_service.py` — `asyncio.run(main())` at bottom of file
**sys.path pattern**: `backend/tests/auto/test_*` files that set `sys.path` before service imports
**dotenv pattern**: `from dotenv import load_dotenv; load_dotenv()` before importing services
**Admin client pattern**: `retrieval_service.py` line 62 — `supabase = get_supabase_admin()`
**Structured output pattern**: `sql_service.py` lines 100–130 — `create_structured_completion` with Pydantic schema

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
┌──────────────────────────────────────────────────────────┐
│ WAVE 1: Foundation (Parallel)                            │
├────────────────────┬─────────────────────────────────────┤
│ Task 1.1           │ Task 1.2                            │
│ Dependency check   │ dataset.py (golden Q&A pairs)       │
│ + install ragas    │ (no external deps needed)           │
└────────────────────┴─────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────┐
│ WAVE 2: Core (After Wave 1)                              │
├────────────────────┬─────────────────────────────────────┤
│ Task 2.1           │ Task 2.2                            │
│ pipeline.py        │ Unit tests (mocked)                 │
│ (service calls)    │ test_eval_pipeline.py               │
└────────────────────┴─────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────┐
│ WAVE 3: Integration (Sequential)                         │
├──────────────────────────────────────────────────────────┤
│ Task 3.1: evaluate.py (RAGAS + LangSmith push)           │
└──────────────────────────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────┐
│ WAVE 4: Documentation                                    │
├──────────────────────────────────────────────────────────┤
│ Task 4.1: README eval section                            │
└──────────────────────────────────────────────────────────┘
```

**Interface Contracts:**
- Task 1.2 provides: `GOLDEN_DATASET: List[EvalSample]` with `.question` and `.ground_truth`
- Task 2.1 provides: `run_rag_pipeline(question) -> {"question": str, "answer": str, "contexts": List[str]}`
- Task 3.1 consumes both: iterates dataset, calls pipeline per question, feeds to RAGAS

---

## IMPLEMENTATION PLAN

### Phase 1: Dependency + Dataset

#### Task 1.1: Verify and install ragas dependency

**WAVE**: 1 | **AGENT_ROLE**: backend-specialist | **DEPENDS_ON**: [] | **BLOCKS**: [3.1]

**Steps:**
```bash
cd backend
# Check for conflicts before installing
venv/Scripts/pip install ragas --dry-run 2>&1 | grep -iE "conflict|error|incompatible|cannot"

# Install
venv/Scripts/pip install ragas

# Verify import
venv/Scripts/python -c "import ragas; print('ragas version:', ragas.__version__)"

# Verify key imports work
venv/Scripts/python -c "
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
print('All RAGAS metrics imported OK')
"

# Check what version was installed
venv/Scripts/pip show ragas | grep Version
```

If `--dry-run` shows conflicts, check which package conflicts and pin to compatible version. Document the version in the requirements.txt entry.

Add to `backend/requirements.txt`:
```
ragas>=0.2
```

**VALIDATE:**
```bash
cd backend && venv/Scripts/python -c "from ragas.metrics import faithfulness; print('OK')"
```

---

#### Task 1.2: CREATE `backend/eval/dataset.py`

**WAVE**: 1 | **AGENT_ROLE**: content-specialist | **DEPENDS_ON**: [] | **BLOCKS**: [3.1]
**PROVIDES**: `GOLDEN_DATASET` list of 15 `EvalSample` objects

**Implement:**
```python
from dataclasses import dataclass
from typing import List

@dataclass
class EvalSample:
    question: str
    ground_truth: str
    source_doc: str  # postmortem filename for traceability

GOLDEN_DATASET: List[EvalSample] = [
    # INC-2024-003 auth-outage (2-3 questions)
    EvalSample(
        question="What was the root cause of the INC-2024-003 auth service outage?",
        ground_truth="...",  # derive from postmortem doc
        source_doc="INC-2024-003-auth-outage.md",
    ),
    # ... 14 more
]
```

Write 15 entries, 2–3 per postmortem document. Include these question types (spread across dataset):
- **Factual root cause** (5 questions): "What was the root cause of [incident]?"
- **Timeline** (3 questions): "How long did [incident] last?", "When was [incident] first detected?"
- **Detection gap** (3 questions): "What monitoring gap allowed [incident] to go undetected?"
- **Remediation** (3 questions): "What follow-up actions were recommended after [incident]?"
- **Cross-doc** (1 question): "Which incident had the longest resolution time?" (harder — tests retrieval across docs)

Ground truth answers: 1–3 sentences, directly verifiable against the postmortem markdown text, specific enough to make `context_recall` meaningful.

**VALIDATE:**
```bash
cd backend
venv/Scripts/python -c "
from eval.dataset import GOLDEN_DATASET
print(f'Dataset size: {len(GOLDEN_DATASET)}')
assert len(GOLDEN_DATASET) == 15
print('All questions:', [s.question[:40] for s in GOLDEN_DATASET[:3]])
"
```

---

### Phase 2: Pipeline + Tests

#### Task 2.1: CREATE `backend/eval/pipeline.py`

**WAVE**: 2 | **AGENT_ROLE**: backend-specialist | **DEPENDS_ON**: [1.1] | **BLOCKS**: [3.1]
**PROVIDES**: `run_rag_pipeline(question: str) -> dict`

**Implement:**
```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.retrieval_service import RetrievalService
from services.provider_service import provider_service
from services.langsmith_service import setup_langsmith
from config import settings
from pydantic import BaseModel

setup_langsmith()

class AnswerOutput(BaseModel):
    answer: str

EVAL_SYSTEM_PROMPT = (
    "You are a precise assistant. Answer the question using ONLY the information "
    "provided in the context below. If the context does not contain enough information "
    "to fully answer, say so explicitly. Do not add information from outside the context."
)

async def run_rag_pipeline(question: str) -> dict:
    """Run retrieval + generation for one question. Returns RAGAS-ready dict."""
    # 1. Retrieve — use admin client (eval is not a user session)
    chunks = await RetrievalService.retrieve_relevant_chunks(
        query=question,
        user_id="00000000-0000-0000-0000-000000000000",  # placeholder; admin bypasses RLS
    )
    contexts = [c["content"] for c in chunks]

    if not contexts:
        return {
            "question": question,
            "answer": "No relevant context found in the knowledge base.",
            "contexts": [],
        }

    context_block = "\n\n---\n\n".join(contexts)
    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"},
    ]

    # 2. Generate — use create_structured_completion (provider_service.py:293)
    result = await provider_service.create_structured_completion(
        provider=settings.DEFAULT_PROVIDER,
        model=settings.DEFAULT_MODEL,
        messages=messages,
        response_schema=AnswerOutput,
        base_url=settings.DEFAULT_BASE_URL,
    )

    return {
        "question": question,
        "answer": result.answer,
        "contexts": contexts,
    }
```

**VALIDATE (requires postmortem docs ingested + backend .env):**
```bash
cd backend
venv/Scripts/python -c "
import asyncio
from eval.pipeline import run_rag_pipeline
result = asyncio.run(run_rag_pipeline('What was the root cause of the auth service outage?'))
print('answer:', result['answer'][:120])
print('contexts found:', len(result['contexts']))
assert 'answer' in result and 'contexts' in result
print('Pipeline shape OK')
"
```
If `contexts: 0` — postmortem docs not yet ingested. Upload them via the app UI first.

---

#### Task 2.2: CREATE `backend/eval/tests/test_eval_pipeline.py`

**WAVE**: 2 | **AGENT_ROLE**: test-specialist | **DEPENDS_ON**: [1.2] | **BLOCKS**: []

**Implement 4 mocked unit tests (no live API calls):**

```python
"""
Unit tests for eval pipeline. All external calls are mocked.
Run: cd backend && venv/Scripts/python -m pytest eval/tests/ -v
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eval.dataset import GOLDEN_DATASET, EvalSample
from eval.pipeline import run_rag_pipeline

# Test 1: dataset size and shape
def test_dataset_has_15_entries():
    assert len(GOLDEN_DATASET) == 15
    for s in GOLDEN_DATASET:
        assert isinstance(s, EvalSample)
        assert len(s.question) > 10
        assert len(s.ground_truth) > 10
        assert s.source_doc.endswith(".md")

# Test 2: all source docs reference known postmortem files
def test_dataset_source_docs_known():
    known = {
        "INC-2024-003-auth-outage.md",
        "INC-2024-011-payment-db-corruption.md",
        "INC-2024-019-pipeline-memory-leak.md",
        "INC-2024-027-gateway-timeout.md",
        "INC-2024-031-notif-queue-backup.md",
        "INC-2024-038-deploy-rollback.md",
    }
    for s in GOLDEN_DATASET:
        assert s.source_doc in known, f"Unknown source_doc: {s.source_doc}"

# Test 3: pipeline returns correct shape when retrieval succeeds
@pytest.mark.asyncio
async def test_pipeline_returns_correct_shape():
    mock_chunks = [{"content": "Redis TTL misconfiguration caused cache misses."}]
    mock_answer = MagicMock()
    mock_answer.answer = "The root cause was Redis TTL misconfiguration."

    with patch("eval.pipeline.RetrievalService.retrieve_relevant_chunks",
               new=AsyncMock(return_value=mock_chunks)), \
         patch("eval.pipeline.provider_service.create_structured_completion",
               new=AsyncMock(return_value=mock_answer)):
        result = await run_rag_pipeline("What was the root cause?")

    assert result["question"] == "What was the root cause?"
    assert result["answer"] == "The root cause was Redis TTL misconfiguration."
    assert result["contexts"] == ["Redis TTL misconfiguration caused cache misses."]

# Test 4: pipeline handles empty retrieval gracefully
@pytest.mark.asyncio
async def test_pipeline_handles_empty_contexts():
    with patch("eval.pipeline.RetrievalService.retrieve_relevant_chunks",
               new=AsyncMock(return_value=[])):
        result = await run_rag_pipeline("Unanswerable question")

    assert result["contexts"] == []
    assert "No relevant context" in result["answer"]
```

Install `pytest-asyncio` if not present: `venv/Scripts/pip install pytest-asyncio`

**VALIDATE:**
```bash
cd backend
venv/Scripts/python -m pytest eval/tests/test_eval_pipeline.py -v
# expect: 4 tests pass, 0 live API calls
```

---

### Phase 3: Evaluation Entry Point

#### Task 3.1: CREATE `backend/eval/evaluate.py`

**WAVE**: 3 | **AGENT_ROLE**: backend-specialist | **DEPENDS_ON**: [1.2, 2.1] | **BLOCKS**: []

**Implement:**
```python
"""
RAGAS evaluation entry point.

Prerequisites:
  1. Postmortem docs uploaded via app UI (backend/eval/postmortems/*.md)
  2. LANGSMITH_API_KEY set in backend/.env
  3. Run: cd backend && venv/Scripts/python eval/evaluate.py
"""
import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.langsmith_service import setup_langsmith
setup_langsmith()

from eval.dataset import GOLDEN_DATASET
from eval.pipeline import run_rag_pipeline


async def collect_pipeline_results():
    """Run pipeline for all questions and collect results."""
    print(f"Running pipeline for {len(GOLDEN_DATASET)} questions...")
    results = []
    for i, sample in enumerate(GOLDEN_DATASET):
        print(f"  [{i+1:02d}/{len(GOLDEN_DATASET)}] {sample.question[:55]}...")
        result = await run_rag_pipeline(sample.question)
        results.append(result)
    return results


def build_ragas_dataset(pipeline_results):
    """Build RAGAS EvaluationDataset from pipeline results + golden ground truths."""
    from datasets import Dataset
    data = {
        "question":     [s.question       for s in GOLDEN_DATASET],
        "answer":       [r["answer"]       for r in pipeline_results],
        "contexts":     [r["contexts"]     for r in pipeline_results],
        "ground_truth": [s.ground_truth    for s in GOLDEN_DATASET],
    }
    return Dataset.from_dict(data)


def run_ragas_scoring(dataset):
    """Run RAGAS evaluate with all 4 metrics."""
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    print("\nScoring with RAGAS (LLM-graded — takes 1–3 minutes)...")
    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )


def print_results(score):
    df = score.to_pandas()
    print("\n" + "=" * 65)
    print("EVALUATION RESULTS")
    print("=" * 65)
    cols = ["faithfulness","answer_relevancy","context_precision","context_recall"]
    for col in cols:
        mean = df[col].mean()
        print(f"  {col:<22}: {mean:.3f}")
    print("=" * 65)
    return df


def push_to_langsmith(df, experiment_name: str):
    """Push per-sample scores to LangSmith as a dataset + examples."""
    from langsmith import Client
    client = Client()
    dataset_name = "ir-copilot-golden-set"

    # Get or create dataset
    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        dataset = existing[0]
        print(f"  Using existing LangSmith dataset: {dataset_name}")
    else:
        dataset = client.create_dataset(dataset_name=dataset_name,
                                         description="IR-Copilot RAG golden evaluation set")
        print(f"  Created LangSmith dataset: {dataset_name}")

    metric_cols = ["faithfulness","answer_relevancy","context_precision","context_recall"]
    for _, row in df.iterrows():
        outputs = {"answer": row["answer"], "ground_truth": row["ground_truth"]}
        for col in metric_cols:
            if col in row:
                outputs[col] = float(row[col]) if row[col] == row[col] else None  # NaN-safe
        client.create_example(
            inputs={"question": row["question"]},
            outputs=outputs,
            dataset_id=dataset.id,
        )
    print(f"  Pushed {len(df)} examples to dataset: {dataset_name}")
    print(f"  Experiment label: {experiment_name}")


async def main():
    pipeline_results = await collect_pipeline_results()
    dataset = build_ragas_dataset(pipeline_results)
    score = run_ragas_scoring(dataset)
    df = print_results(score)
    push_to_langsmith(df, experiment_name=f"rag-eval-{date.today()}")
    print(f"\nDone. View results at: https://smith.langchain.com/")


if __name__ == "__main__":
    asyncio.run(main())
```

**VALIDATE:**
```bash
# Quick smoke test (validates imports only, no API calls)
cd backend
venv/Scripts/python -c "
import ast, sys
with open('eval/evaluate.py') as f:
    ast.parse(f.read())
print('evaluate.py parses OK')
"

# Full run (requires ingested docs + LANGSMITH_API_KEY)
# cd backend && venv/Scripts/python eval/evaluate.py
```

---

### Phase 4: Documentation

#### Task 4.1: UPDATE `README.md` — add Evaluation section

**WAVE**: 4 | **AGENT_ROLE**: docs-specialist | **DEPENDS_ON**: [3.1] | **BLOCKS**: []

Add after the existing Testing section in README.md:

```markdown
## Evaluation

The RAG pipeline is evaluated using [RAGAS](https://docs.ragas.io) against a golden dataset
of 15 Q&A pairs drawn from postmortem documents.

**Metrics:** Faithfulness · Answer Relevancy · Context Precision · Context Recall

**Prerequisites:**
1. Apply migration 016 (production_incidents table)
2. Upload postmortem documents via the app UI (`backend/eval/postmortems/*.md`)
3. Set `LANGSMITH_API_KEY` in `backend/.env`

**Run:**
```bash
cd backend
venv/Scripts/python eval/evaluate.py
```

Results are pushed to LangSmith as dataset `ir-copilot-golden-set`.
```

**VALIDATE:**
```bash
grep -n "Evaluation\|ragas\|RAGAS" README.md | head -5
```

---

## TESTING STRATEGY

### Unit Tests (mocked)

**Automation**: ✅ Fully Automated | **Tool**: pytest + pytest-asyncio
**Location**: `backend/eval/tests/test_eval_pipeline.py`
**Execution**: `cd backend && venv/Scripts/python -m pytest eval/tests/ -v`
**Coverage**: Dataset shape (2 tests), pipeline return shape (1), empty context handling (1)

### Dependency Validation

**Automation**: ✅ Automated (bash)
**Execution**: `cd backend && venv/Scripts/python -c "from ragas.metrics import faithfulness; print('OK')"`

### Integration Test (smoke — imports only)

**Automation**: ✅ Automated
**Execution**: `cd backend && venv/Scripts/python -c "import ast; ast.parse(open('eval/evaluate.py').read()); print('OK')"`

### Live Evaluation Run

**Automation**: ⚠️ Manual — requires: LANGSMITH_API_KEY, postmortem docs ingested, OpenAI API key for RAGAS LLM scoring
**Why Manual**: RAGAS LLM-graded metrics make ~60 OpenAI API calls (4 metrics × 15 questions); not suitable for unattended CI
**Steps**:
1. Upload 6 postmortem markdown files via app UI
2. `cd backend && venv/Scripts/python eval/evaluate.py`
3. Check LangSmith → Datasets → `ir-copilot-golden-set`

**Expected**: 15 rows, 4 score columns, faithfulness mean ≥ 0.65

### Test Automation Summary

**Total**: 4 unit + 1 smoke + 1 live = 6 tests
- ✅ **Automated**: 5 (83%) — pytest + bash
- ⚠️ **Manual**: 1 (17%) — live evaluation run (API cost + prerequisite data)
- **Goal**: 83% ✅ Met for automated-able tests

---

## VALIDATION COMMANDS

### Level 1: Dependency installed
```bash
cd backend && venv/Scripts/python -c "import ragas; print(ragas.__version__)"
```

### Level 2: Dataset valid
```bash
cd backend && venv/Scripts/python -c "
from eval.dataset import GOLDEN_DATASET
assert len(GOLDEN_DATASET) == 15, f'Expected 15, got {len(GOLDEN_DATASET)}'
print('Dataset OK:', len(GOLDEN_DATASET), 'samples')
"
```

### Level 3: Unit tests (mocked)
```bash
cd backend && venv/Scripts/python -m pytest eval/tests/ -v
```

### Level 4: Pipeline smoke (requires .env + ingested docs)
```bash
cd backend && venv/Scripts/python -c "
import asyncio
from eval.pipeline import run_rag_pipeline
r = asyncio.run(run_rag_pipeline('What was the root cause of the auth outage?'))
print('contexts:', len(r['contexts']), '| answer:', r['answer'][:60])
"
```

### Level 5: Full evaluation (manual — see prerequisites above)
```bash
cd backend && venv/Scripts/python eval/evaluate.py
```

---

## ACCEPTANCE CRITERIA

- [ ] `ragas` installs without dependency conflicts
- [ ] `backend/eval/dataset.py` has exactly 15 `EvalSample` entries with non-empty question + ground_truth
- [ ] `backend/eval/pipeline.py` returns `{"question", "answer", "contexts"}` dict
- [ ] `backend/eval/evaluate.py` runs without error (smoke test: import + AST parse)
- [ ] 4 unit tests pass with no live API calls
- [ ] README.md contains evaluation section with run instructions
- [ ] No modifications to production service files (`chat_service.py`, `retrieval_service.py`, etc.)

---

## COMPLETION CHECKLIST

- [ ] ragas installed + added to requirements.txt
- [ ] `backend/eval/__init__.py` created
- [ ] `backend/eval/dataset.py` — 15 EvalSample entries
- [ ] `backend/eval/pipeline.py` — retrieval + structured generation
- [ ] `backend/eval/evaluate.py` — RAGAS scoring + LangSmith push
- [ ] `backend/eval/tests/__init__.py` created
- [ ] `backend/eval/tests/test_eval_pipeline.py` — 4 mocked tests passing
- [ ] README.md updated with evaluation section
- [ ] Full pytest suite has no regressions: `venv/Scripts/python -m pytest tests/auto/ -v`
- [ ] **⚠️ Changes left UNSTAGED for user review**

---

## NOTES

- **Prerequisite dependency on Plan 001**: `backend/eval/postmortems/` must exist with 6 markdown files before a live eval run is possible. The unit tests (Task 2.2) and imports work without this.
- **RAGAS LLM for scoring**: By default RAGAS uses OpenAI (`gpt-4o-mini` or similar) for scoring faithfulness and answer_relevancy. The same `OPENAI_API_KEY` from `backend/.env` is used. Expect ~$0.05–0.15 per full evaluation run at 15 questions.
- **user_id placeholder in pipeline**: `retrieve_relevant_chunks` passes `user_id` into the Supabase RPC for RLS filtering, but since we use `get_supabase_admin()` as the client, RLS is bypassed and the value is not checked. The placeholder UUID `00000000-0000-0000-0000-000000000000` is safe.
- **RAGAS API changes**: RAGAS 0.1→0.2 changed `Dataset` import path. At implementation time, verify: `from ragas import evaluate` and `from datasets import Dataset` (HuggingFace datasets). If API differs from this plan, adapt accordingly and note in execution report.
- **pytest-asyncio**: Required for `@pytest.mark.asyncio` tests. Add to requirements.txt if not present: `pytest-asyncio>=0.21`.
