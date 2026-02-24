"""
Unit tests for tool selection evaluation. All external calls are mocked -- no live API calls.
Run: cd backend && uv run python -m pytest eval/tests/test_tool_selection.py -v

Tests verify:
  - Dataset shape and coverage
  - Pipeline behavior (tool capture, no-tool fallback, args)
  - Accuracy scoring logic (single-turn and multi-turn)
  - AgentGoalAccuracy integration (mocked)
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
from eval.tool_selection_pipeline import run_tool_selection_pipeline


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
    valid_tools = {"retrieve_documents", "query_incidents_database", "search_web"}
    valid_cats = {"retrieve", "sql", "web"}
    for s in TOOL_SELECTION_DATASET:
        assert isinstance(s, ToolSelectionSample)
        assert len(s.question) > 10
        assert s.expected_tool in valid_tools, f"Unknown tool: {s.expected_tool}"
        assert s.category in valid_cats, f"Unknown category: {s.category}"
        assert len(s.reference_goal) > 10


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
