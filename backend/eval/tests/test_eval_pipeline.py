"""
Unit tests for eval pipeline. All external calls are mocked — no live API calls.
Run: cd backend && uv run python -m pytest eval/tests/ -v

Integration tests (marked with @pytest.mark.skipif) require:
  - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars set
  - Postmortem docs ingested via the app UI
Run them with: cd backend && uv run python -m pytest eval/tests/ -v -m integration
"""
import sys
import os

# Ensure backend root is on path for service imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eval.dataset import GOLDEN_DATASET, EvalSample
from eval.pipeline import run_rag_pipeline



# ── Test 1: Dataset size and shape ──────────────────────────────────────────

def test_dataset_has_15_entries():
    assert len(GOLDEN_DATASET) == 15
    for s in GOLDEN_DATASET:
        assert isinstance(s, EvalSample)
        assert len(s.question) > 10, f"Question too short: {s.question!r}"
        assert len(s.ground_truth) > 10, f"Ground truth too short for: {s.question!r}"
        assert s.source_doc.endswith(".md"), f"source_doc must be .md: {s.source_doc}"


# ── Test 2: All source docs reference known postmortem files ─────────────────

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


# ── Test 3: Pipeline returns correct shape when retrieval succeeds ───────────

@pytest.mark.asyncio
async def test_pipeline_returns_correct_shape():
    mock_chunks = [{"content": "Redis TTL misconfiguration caused cache misses."}]
    mock_answer = MagicMock()
    mock_answer.answer = "The root cause was Redis TTL misconfiguration."

    with patch(
        "eval.pipeline.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=mock_chunks),
    ), patch(
        "eval.pipeline.provider_service.create_structured_completion",
        new=AsyncMock(return_value=mock_answer),
    ):
        result = await run_rag_pipeline("What was the root cause?")

    assert result["question"] == "What was the root cause?"
    assert result["answer"] == "The root cause was Redis TTL misconfiguration."
    assert result["contexts"] == ["Redis TTL misconfiguration caused cache misses."]


# ── Test 4: Pipeline handles empty retrieval gracefully ──────────────────────

@pytest.mark.asyncio
async def test_pipeline_handles_empty_contexts():
    with patch(
        "eval.pipeline.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=[]),
    ):
        result = await run_rag_pipeline("Unanswerable question")

    assert result["contexts"] == []
    assert "No relevant context" in result["answer"]


# ── Behavioral correctness tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_includes_all_retrieved_contexts():
    """All retrieved chunks appear in the result contexts list, preserving order."""
    mock_chunks = [
        {"content": "Redis TTL was changed to 360 seconds."},
        {"content": "Mass token expiry began 6 minutes after deployment."},
        {"content": "Auth service logged 5xx errors at 14:32 UTC."},
    ]
    mock_answer = MagicMock()
    mock_answer.answer = "Root cause: Redis TTL misconfiguration."

    with patch(
        "eval.pipeline.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=mock_chunks),
    ), patch(
        "eval.pipeline.provider_service.create_structured_completion",
        new=AsyncMock(return_value=mock_answer),
    ):
        result = await run_rag_pipeline("What caused the auth outage?")

    assert len(result["contexts"]) == 3
    assert result["contexts"][0] == "Redis TTL was changed to 360 seconds."
    assert result["contexts"][2] == "Auth service logged 5xx errors at 14:32 UTC."


@pytest.mark.asyncio
async def test_pipeline_passes_contexts_to_llm():
    """All retrieved context chunks are concatenated with separator and sent to the LLM."""
    mock_chunks = [
        {"content": "First context chunk."},
        {"content": "Second context chunk."},
    ]
    mock_answer = MagicMock()
    mock_answer.answer = "Answer based on context."
    mock_completion = AsyncMock(return_value=mock_answer)

    with patch(
        "eval.pipeline.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=mock_chunks),
    ), patch(
        "eval.pipeline.provider_service.create_structured_completion",
        new=mock_completion,
    ):
        await run_rag_pipeline("Test question?")

    messages = mock_completion.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    assert "First context chunk." in user_content
    assert "Second context chunk." in user_content
    assert "---" in user_content          # separator between chunks
    assert "Test question?" in user_content


@pytest.mark.asyncio
@pytest.mark.parametrize("off_topic_question", [
    "What is the recipe for chocolate cake?",
    "Who won the FIFA World Cup in 2022?",
    "What is the current price of Bitcoin?",
])
async def test_off_topic_queries_return_no_context_fallback(off_topic_question):
    """Off-topic queries that retrieve nothing return the anti-hallucination fallback."""
    with patch(
        "eval.pipeline.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=[]),
    ):
        result = await run_rag_pipeline(off_topic_question)

    assert result["question"] == off_topic_question
    assert result["contexts"] == []
    assert "No relevant context" in result["answer"]


def test_build_ragas_dataset_shape():
    """build_ragas_dataset produces an EvaluationDataset with one sample per golden entry."""
    # Ensure pyarrow.dataset is mocked on Windows before any ragas import
    sys.modules.setdefault("pyarrow.dataset", MagicMock())
    sys.modules.setdefault("pyarrow._dataset", MagicMock())

    from eval.evaluate import build_ragas_dataset  # noqa: PLC0415 (lazy import intentional)

    fake_results = [
        {"question": s.question, "answer": "Fake answer.", "contexts": ["Fake context."]}
        for s in GOLDEN_DATASET
    ]
    dataset = build_ragas_dataset(fake_results)

    assert hasattr(dataset, "samples"), "EvaluationDataset must expose .samples"
    assert len(dataset.samples) == 15

    first = dataset.samples[0]
    assert hasattr(first, "user_input")
    assert hasattr(first, "response")
    assert hasattr(first, "retrieved_contexts")
    assert hasattr(first, "reference")
    assert first.user_input == GOLDEN_DATASET[0].question
    assert first.reference == GOLDEN_DATASET[0].ground_truth


# ── Integration tests (fixture cleans DB + ingests postmortem docs) ──────────
# Controlled by EVAL_DOCS_INGESTED=true in backend/.env (default: false).
# conftest.py:eval_ingestion_setup handles setup; tests are skipped when flag is false.

@pytest.mark.asyncio
async def test_in_distribution_query_live(eval_ingestion_setup):
    """[Integration] Golden dataset question retrieves relevant postmortem context."""
    user_id = eval_ingestion_setup
    result = await run_rag_pipeline(
        "What was the root cause of the INC-2024-003 auth service outage?",
        user_id=user_id,
    )
    assert len(result["contexts"]) > 0, (
        "No context retrieved — check that eval ingestion completed successfully"
    )
    assert result["answer"] != "No relevant context found in the knowledge base."


@pytest.mark.asyncio
async def test_no_context_query_live(eval_ingestion_setup):
    """[Integration] Completely off-topic query returns the anti-hallucination fallback."""
    user_id = eval_ingestion_setup
    result = await run_rag_pipeline(
        "What are the current cryptocurrency market prices?",
        user_id=user_id,
    )
    no_context_fallback = (
        result["contexts"] == []
        or "No relevant context" in result["answer"]
    )
    assert no_context_fallback, (
        f"Expected no-context fallback for off-topic query, got: {result['answer'][:120]}"
    )
