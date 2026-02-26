"""
Unit tests for tool selection evaluation. All external calls are mocked -- no live API calls.
Run: cd backend && uv run python -m pytest eval/tests/test_tool_selection.py -v

Tests verify:
  - Dataset shape and coverage
  - Pipeline behavior (tool capture, no-tool fallback, args)
  - Accuracy scoring logic (single-turn and multi-turn)
  - AgentGoalAccuracy integration (mocked)
  - Multi-turn pipeline: full sequence, message structure, edge cases
  - score_arg_quality: score storage, None handling, exception handling, multi-sample
"""
import sys
import os

# Ensure backend root is on path for service imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Mock pyarrow.dataset before any ragas imports
from unittest.mock import MagicMock
sys.modules.setdefault("pyarrow.dataset", MagicMock())
sys.modules.setdefault("pyarrow._dataset", MagicMock())

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eval.tool_selection_dataset import (
    TOOL_SELECTION_DATASET,
    MULTI_TURN_DATASET,
    ToolSelectionSample,
    MultiTurnSelectionSample,
)
from eval.tool_selection_pipeline import run_tool_selection_pipeline, run_multiturn_pipeline


# ── Helper: fake streaming chunks ───────────────────────────────────────────

def make_tool_call_chunk(tool_name: str, args: str = '{"query": "test"}', index: int = 0):
    """Build a fake streaming chunk with a tool_call delta."""
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
    """Build a fake stop chunk (finish_reason=tool_calls, no more delta)."""
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].finish_reason = "tool_calls"
    chunk.choices[0].delta.tool_calls = None
    chunk.choices[0].delta.content = None
    return chunk


async def fake_stream(*chunks):
    """Async generator yielding the given chunks."""
    for chunk in chunks:
        yield chunk


# ── Test 1: Dataset size and shape ───────────────────────────────────────────

def test_single_turn_dataset_has_12_entries():
    assert len(TOOL_SELECTION_DATASET) == 12
    valid_tools = {"retrieve_documents", "query_deployments_database", "search_web"}
    valid_cats = {"retrieve", "sql", "web"}
    for s in TOOL_SELECTION_DATASET:
        assert isinstance(s, ToolSelectionSample)
        assert len(s.question) > 10
        assert s.expected_tool in valid_tools, f"Unknown tool: {s.expected_tool}"
        assert s.category in valid_cats, f"Unknown category: {s.category}"
        assert len(s.reference_goal) > 10
        assert len(s.required_arg_keywords) >= 1, f"No keywords for: {s.question}"
        assert all(isinstance(kw, str) and len(kw) > 0 for kw in s.required_arg_keywords)


# ── Test 2: Dataset covers all tools equally ─────────────────────────────────

def test_dataset_covers_all_tools():
    categories = [s.category for s in TOOL_SELECTION_DATASET]
    assert categories.count("retrieve") == 4
    assert categories.count("sql") == 4
    assert categories.count("web") == 4


# ── Test 3: Multi-turn dataset size and shape ────────────────────────────────

def test_multiturn_dataset_has_3_entries():
    assert len(MULTI_TURN_DATASET) == 3
    for s in MULTI_TURN_DATASET:
        assert isinstance(s, MultiTurnSelectionSample)
        assert s.expected_sequence == ["retrieve_documents", "analyze_document_with_subagent"]
        assert s.category == "retrieve_then_analyze"
        assert len(s.reference_goal) > 10


# ── Test 4: Pipeline captures correct tool name ──────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_captures_correct_tool_name():
    chunks = [
        make_tool_call_chunk("retrieve_documents", '{"query": "auth outage root cause"}'),
        make_stop_chunk(),
    ]
    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        return_value=fake_stream(*chunks),
    ):
        actual_name, multi_turn = await run_tool_selection_pipeline("What caused the auth outage?")

    assert actual_name == "retrieve_documents"
    assert multi_turn.user_input[1].tool_calls is not None
    assert multi_turn.user_input[1].tool_calls[0].name == "retrieve_documents"


# ── Test 5: Pipeline handles no tool call (direct answer) ────────────────────

@pytest.mark.asyncio
async def test_pipeline_handles_no_tool_call():
    stop = make_stop_chunk()
    stop.choices[0].finish_reason = "stop"
    stop.choices[0].delta.tool_calls = None

    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        return_value=fake_stream(stop),
    ):
        actual_name, multi_turn = await run_tool_selection_pipeline("Hello!")

    assert actual_name is None
    assert multi_turn.user_input[1].tool_calls is None


# ── Test 6: Pipeline captures tool args correctly ────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_captures_tool_args():
    chunks = [
        make_tool_call_chunk("retrieve_documents", '{"query": "auth outage root cause"}'),
        make_stop_chunk(),
    ]
    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        return_value=fake_stream(*chunks),
    ):
        actual_name, multi_turn = await run_tool_selection_pipeline("Test question")

    tool_calls = multi_turn.user_input[1].tool_calls
    assert tool_calls is not None
    assert tool_calls[0].args == {"query": "auth outage root cause"}


# ── Test 7: Routing accuracy correct ─────────────────────────────────────────

def test_tool_routing_accuracy_correct():
    actual_name = "retrieve_documents"
    expected_name = "retrieve_documents"
    score = int(actual_name == expected_name)
    assert score == 1


# ── Test 8: Routing accuracy wrong ───────────────────────────────────────────

def test_tool_routing_accuracy_wrong():
    actual_name = "search_web"
    expected_name = "retrieve_documents"
    score = int(actual_name == expected_name)
    assert score == 0


# ── Test 9: Multi-turn sequence accuracy ─────────────────────────────────────

def test_multiturn_sequence_accuracy():
    expected = ["retrieve_documents", "analyze_document_with_subagent"]
    # Correct sequence
    assert int(["retrieve_documents", "analyze_document_with_subagent"] == expected) == 1
    # Wrong sequence
    assert int(["retrieve_documents"] == expected) == 0
    assert int(["analyze_document_with_subagent", "retrieve_documents"] == expected) == 0


# ── Test 10: AgentGoalAccuracy scoring (mocked) ──────────────────────────────

@pytest.mark.asyncio
async def test_arg_quality_scoring_correct():
    """AgentGoalAccuracy returns 1.0 for a correct tool call -- verify integration."""
    from ragas.messages import HumanMessage, AIMessage, ToolCall
    from ragas.dataset_schema import MultiTurnSample

    ragas_tc = ToolCall(name="retrieve_documents", args={"query": "auth outage root cause"})
    multi_turn = MultiTurnSample(
        user_input=[
            HumanMessage(content="What caused the auth outage?"),
            AIMessage(content="", tool_calls=[ragas_tc]),
        ]
    )
    reference_goal = "Retrieve documents about INC-2024-003 targeting root cause"

    mock_result = MagicMock()
    mock_result.value = 1.0
    mock_ascore = AsyncMock(return_value=mock_result)

    with patch(
        "ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference.ascore",
        new=mock_ascore,
    ):
        from ragas.metrics.collections.agent_goal_accuracy.metric import AgentGoalAccuracyWithReference
        from ragas.llms.base import llm_factory
        from openai import AsyncOpenAI
        metric = AgentGoalAccuracyWithReference(
            llm=llm_factory("gpt-4o-mini", client=AsyncOpenAI(api_key="test"))
        )
        result = await metric.ascore(
            user_input=multi_turn.user_input,
            reference=reference_goal,
        )

    assert float(result.value) == 1.0
    mock_ascore.assert_called_once_with(
        user_input=multi_turn.user_input,
        reference=reference_goal,
    )


# ── Test 11: All samples have non-empty reference_goals ──────────────────────

def test_dataset_has_reference_goals():
    for s in TOOL_SELECTION_DATASET:
        assert s.reference_goal, f"Empty reference_goal for: {s.question}"
    for s in MULTI_TURN_DATASET:
        assert s.reference_goal, f"Empty reference_goal for: {s.question}"


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-turn pipeline tests (Tests 12-15)
# run_multiturn_pipeline() was previously untested. These mock both LLM calls
# and the retrieval step to verify pipeline branching and RAGAS message structure.
# ═══════════════════════════════════════════════════════════════════════════════

FAKE_RETRIEVAL_RESULTS = [
    {"document_name": "inc-2024-003.md", "content": "Auth outage root cause: misconfigured rate limiter."},
]


def make_retrieve_chunks():
    return [
        make_tool_call_chunk("retrieve_documents", '{"query": "auth outage root cause"}'),
        make_stop_chunk(),
    ]


def make_analyze_chunks():
    return [
        make_tool_call_chunk(
            "analyze_document_with_subagent",
            '{"document_name": "inc-2024-003.md", "task": "Extract all action items"}',
        ),
        make_stop_chunk(),
    ]


# ── Test 12: Multi-turn happy path returns correct sequence ──────────────────

@pytest.mark.asyncio
async def test_multiturn_pipeline_returns_full_sequence():
    """Happy path: LLM calls retrieve then analyze -- sequence list is correct."""
    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        side_effect=[fake_stream(*make_retrieve_chunks()), fake_stream(*make_analyze_chunks())],
    ), patch(
        "services.retrieval_service.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=FAKE_RETRIEVAL_RESULTS),
    ):
        actual_sequence, _ = await run_multiturn_pipeline(
            "Analyze the INC-2024-003 auth outage document and extract all action items."
        )

    assert actual_sequence == ["retrieve_documents", "analyze_document_with_subagent"]


# ── Test 13: Multi-turn RAGAS message structure has all 4 messages ───────────

@pytest.mark.asyncio
async def test_multiturn_pipeline_ragas_message_structure():
    """MultiTurnSample contains [Human, AI(retrieve), Tool(context), AI(analyze)] in order."""
    from ragas.messages import HumanMessage, AIMessage, ToolMessage

    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        side_effect=[fake_stream(*make_retrieve_chunks()), fake_stream(*make_analyze_chunks())],
    ), patch(
        "services.retrieval_service.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=FAKE_RETRIEVAL_RESULTS),
    ):
        _, multi_turn = await run_multiturn_pipeline("Analyze the auth outage document.")

    msgs = multi_turn.user_input
    assert len(msgs) == 4, f"Expected 4 messages, got {len(msgs)}: {[type(m).__name__ for m in msgs]}"
    assert isinstance(msgs[0], HumanMessage)
    assert isinstance(msgs[1], AIMessage)
    assert msgs[1].tool_calls[0].name == "retrieve_documents"
    assert isinstance(msgs[2], ToolMessage)
    # The retrieved document name must be in the context injected to the LLM
    assert "inc-2024-003.md" in msgs[2].content
    assert isinstance(msgs[3], AIMessage)
    assert msgs[3].tool_calls[0].name == "analyze_document_with_subagent"


# ── Test 14: Wrong first tool causes early exit ───────────────────────────────

@pytest.mark.asyncio
async def test_multiturn_pipeline_early_exit_wrong_first_tool():
    """If the first tool is not retrieve_documents, pipeline returns early without retrieval."""
    wrong_chunks = [
        make_tool_call_chunk("search_web", '{"query": "auth outage"}'),
        make_stop_chunk(),
    ]
    mock_retrieve = AsyncMock()

    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        return_value=fake_stream(*wrong_chunks),
    ), patch(
        "services.retrieval_service.RetrievalService.retrieve_relevant_chunks",
        new=mock_retrieve,
    ):
        actual_sequence, multi_turn = await run_multiturn_pipeline("Some question")

    assert actual_sequence == ["search_web"]
    mock_retrieve.assert_not_called()
    # Only 2 RAGAS messages: Human + AI(wrong tool)
    assert len(multi_turn.user_input) == 2


# ── Test 15: No second tool call yields 3-message RAGAS sample ───────────────

@pytest.mark.asyncio
async def test_multiturn_pipeline_no_second_tool_call():
    """If second LLM call answers directly (no tool), sequence has only first tool."""
    direct_answer_stop = make_stop_chunk()
    direct_answer_stop.choices[0].finish_reason = "stop"
    direct_answer_stop.choices[0].delta.tool_calls = None

    with patch(
        "eval.tool_selection_pipeline.provider_service.stream_chat_completion",
        side_effect=[fake_stream(*make_retrieve_chunks()), fake_stream(direct_answer_stop)],
    ), patch(
        "services.retrieval_service.RetrievalService.retrieve_relevant_chunks",
        new=AsyncMock(return_value=FAKE_RETRIEVAL_RESULTS),
    ):
        actual_sequence, multi_turn = await run_multiturn_pipeline("Some question")

    assert actual_sequence == ["retrieve_documents"]
    # 3 RAGAS messages: Human, AI(retrieve), Tool(context) — no second AI message
    assert len(multi_turn.user_input) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# score_arg_quality tests (Tests 16-19)
# The function delegates to AgentGoalAccuracyWithReference (LLM judge). These
# tests verify the function's logic around calling the metric, handling failures,
# and storing results -- without making live LLM calls.
# ═══════════════════════════════════════════════════════════════════════════════

def _make_single_result(score_value=None):
    """Build a fake single-turn result dict with private scoring fields."""
    from ragas.messages import HumanMessage, AIMessage, ToolCall
    from ragas.dataset_schema import MultiTurnSample

    tc = ToolCall(name="retrieve_documents", args={"query": "auth outage root cause"})
    mt = MultiTurnSample(
        user_input=[
            HumanMessage(content="What caused the auth outage?"),
            AIMessage(content="", tool_calls=[tc]),
        ]
    )
    return {
        "question": "What caused the auth outage?",
        "expected_tool": "retrieve_documents",
        "actual_tool": "retrieve_documents",
        "tool_routing_accuracy": 1,
        "_multi_turn": mt,
        "_reference_goal": "Retrieve documents about INC-2024-003 targeting root cause",
    }


# ── Test 16: score_arg_quality stores the metric's score ─────────────────────

@pytest.mark.asyncio
async def test_score_arg_quality_stores_metric_score():
    """score_arg_quality sets arg_quality from the metric result and removes private keys."""
    from eval.evaluate_tool_selection import score_arg_quality

    mock_result = MagicMock()
    mock_result.value = 0.85

    results = [_make_single_result()]

    with patch("ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference") as mock_class, \
         patch("ragas.llms.base.llm_factory", return_value=MagicMock()), \
         patch("openai.AsyncOpenAI", return_value=MagicMock()):
        mock_metric = MagicMock()
        mock_metric.ascore = AsyncMock(return_value=mock_result)
        mock_class.return_value = mock_metric

        scored = await score_arg_quality(results)

    assert scored[0]["arg_quality"] == 0.85
    assert "_multi_turn" not in scored[0]
    assert "_reference_goal" not in scored[0]


# ── Test 17: score_arg_quality skips metric when _multi_turn is None ─────────

@pytest.mark.asyncio
async def test_score_arg_quality_handles_none_multi_turn():
    """When _multi_turn is None (pipeline error), arg_quality=0.0 without calling ascore."""
    from eval.evaluate_tool_selection import score_arg_quality

    results = [{
        "question": "Some question",
        "_multi_turn": None,
        "_reference_goal": "Some goal",
    }]

    with patch("ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference") as mock_class, \
         patch("ragas.llms.base.llm_factory", return_value=MagicMock()), \
         patch("openai.AsyncOpenAI", return_value=MagicMock()):
        mock_metric = MagicMock()
        mock_metric.ascore = AsyncMock()
        mock_class.return_value = mock_metric

        scored = await score_arg_quality(results)

    assert scored[0]["arg_quality"] == 0.0
    mock_metric.ascore.assert_not_called()


# ── Test 18: score_arg_quality sets 0.0 on metric exception ──────────────────

@pytest.mark.asyncio
async def test_score_arg_quality_handles_metric_exception():
    """When ascore raises, arg_quality is set to 0.0 instead of propagating."""
    from eval.evaluate_tool_selection import score_arg_quality

    results = [_make_single_result()]

    with patch("ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference") as mock_class, \
         patch("ragas.llms.base.llm_factory", return_value=MagicMock()), \
         patch("openai.AsyncOpenAI", return_value=MagicMock()):
        mock_metric = MagicMock()
        mock_metric.ascore = AsyncMock(side_effect=RuntimeError("Simulated API failure"))
        mock_class.return_value = mock_metric

        scored = await score_arg_quality(results)

    assert scored[0]["arg_quality"] == 0.0


# ── Test 19: score_arg_quality scores each sample independently ───────────────

@pytest.mark.asyncio
async def test_score_arg_quality_scores_multiple_samples():
    """All samples in the list are scored; each gets its own arg_quality value."""
    from eval.evaluate_tool_selection import score_arg_quality

    def make_result(q):
        r = _make_single_result()
        r["question"] = q
        return r

    results = [make_result("Q1"), make_result("Q2"), make_result("Q3")]

    r1, r2, r3 = MagicMock(), MagicMock(), MagicMock()
    r1.value, r2.value, r3.value = 1.0, 0.5, 0.0

    with patch("ragas.metrics.collections.agent_goal_accuracy.metric.AgentGoalAccuracyWithReference") as mock_class, \
         patch("ragas.llms.base.llm_factory", return_value=MagicMock()), \
         patch("openai.AsyncOpenAI", return_value=MagicMock()):
        mock_metric = MagicMock()
        mock_metric.ascore = AsyncMock(side_effect=[r1, r2, r3])
        mock_class.return_value = mock_metric

        scored = await score_arg_quality(results)

    assert len(scored) == 3
    assert scored[0]["arg_quality"] == 1.0
    assert scored[1]["arg_quality"] == 0.5
    assert scored[2]["arg_quality"] == 0.0
    assert mock_metric.ascore.call_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# score_arg_keyword_relevance tests (Tests 20-22)
# Deterministic check: does the captured query arg contain at least one
# domain-relevant keyword? Tests verify match, no-match, and empty-query cases.
# ═══════════════════════════════════════════════════════════════════════════════

def _make_keyword_result(actual_query: str, keywords: list) -> dict:
    """Minimal result dict for keyword relevance testing."""
    return {
        "question": "Test question",
        "actual_tool": "retrieve_documents",
        "tool_routing_accuracy": 1,
        "_actual_query": actual_query,
        "_required_arg_keywords": keywords,
    }


# ── Test 20: Matching keyword scores 1.0 ─────────────────────────────────────

def test_score_arg_keyword_relevance_match():
    """Query containing a required keyword scores 1.0."""
    from eval.evaluate_tool_selection import score_arg_keyword_relevance

    results = [_make_keyword_result(
        actual_query="root cause of the INC-2024-003 auth outage",
        keywords=["INC-2024-003", "auth", "root cause"],
    )]
    scored = score_arg_keyword_relevance(results)

    assert scored[0]["arg_keyword_relevance"] == 1.0
    assert "_actual_query" not in scored[0]
    assert "_required_arg_keywords" not in scored[0]


# ── Test 21: No keyword match scores 0.0 ─────────────────────────────────────

def test_score_arg_keyword_relevance_no_match():
    """Query with no required keyword scores 0.0, including empty query."""
    from eval.evaluate_tool_selection import score_arg_keyword_relevance

    # Completely off-topic query
    off_topic = [_make_keyword_result(
        actual_query="current weather in London today",
        keywords=["INC-2024-003", "auth", "root cause"],
    )]
    scored = score_arg_keyword_relevance(off_topic)
    assert scored[0]["arg_keyword_relevance"] == 0.0

    # Empty query (right tool called, but no meaningful arg)
    empty_query = [_make_keyword_result(
        actual_query="",
        keywords=["Bitcoin", "BTC", "price"],
    )]
    scored = score_arg_keyword_relevance(empty_query)
    assert scored[0]["arg_keyword_relevance"] == 0.0


# ── Test 22: Keyword check is case-insensitive ────────────────────────────────

def test_score_arg_keyword_relevance_case_insensitive():
    """Keyword match is case-insensitive: 'bitcoin' matches keyword 'Bitcoin'."""
    from eval.evaluate_tool_selection import score_arg_keyword_relevance

    results = [_make_keyword_result(
        actual_query="what is the bitcoin price right now",  # lowercase
        keywords=["Bitcoin", "BTC", "price"],               # mixed case keyword
    )]
    scored = score_arg_keyword_relevance(results)
    assert scored[0]["arg_keyword_relevance"] == 1.0
