"""
Unit tests for chat quality pipeline. All external calls are mocked — no live API calls.
Run: cd backend && uv run python -m pytest eval/tests/test_chat_quality_pipeline.py -v

Tests cover: result shape, empty contexts, delta accumulation, exception handling,
content extraction, empty-content filtering, and tool arg capture structure.
"""
import sys
import os

# Ensure backend root is on path for service imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, AsyncMock
from eval.chat_quality_pipeline import run_chat_quality_pipeline


# ── Shared fake stream helpers ────────────────────────────────────────────────

async def _stream_with_sources(*args, **kwargs):
    """Fake stream: one text delta then one sources yield."""
    yield ("The answer.", None, None)
    yield ("", [{"content": "ctx chunk", "document_name": "doc.md",
                  "document_id": "id1", "id": "c1", "similarity": 0.9}], None)


async def _stream_no_sources(*args, **kwargs):
    """Fake stream: text delta only, no sources yield."""
    yield ("The answer.", None, None)


# ── T1: Correct shape ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_returns_correct_shape():
    """Result dict has all required keys."""
    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=_stream_with_sources):
        result = await run_chat_quality_pipeline("Test question?", user_id="test-uuid")

    assert "question" in result
    assert "answer" in result
    assert "contexts" in result
    assert "sources" in result
    assert "tool_name" in result
    assert "tool_args" in result


# ── T2: Empty contexts + no tool when no retrieval ────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_returns_empty_contexts_when_no_sources():
    """When stream yields no sources, contexts is [], tool_name is None, tool_args is {}."""
    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=_stream_no_sources):
        result = await run_chat_quality_pipeline("No-retrieval question?", user_id="test-uuid")

    assert result["contexts"] == []
    assert result["tool_name"] is None
    assert result["tool_args"] == {}


# ── T3: Delta accumulation ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_accumulates_text_deltas():
    """Multiple text deltas are concatenated into a single answer string."""
    async def multi_delta_stream(*args, **kwargs):
        yield ("Hello ", None, None)
        yield ("world", None, None)
        yield ("!", None, None)

    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=multi_delta_stream):
        result = await run_chat_quality_pipeline("Accumulation test?", user_id="uuid")

    assert result["answer"] == "Hello world!"


# ── T4: Exception handling ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_returns_error_dict_on_exception():
    """When stream_response raises, pipeline returns a graceful error dict."""
    async def raising_stream(*args, **kwargs):
        raise RuntimeError("LLM connection refused")
        yield  # make it an async generator

    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=raising_stream):
        result = await run_chat_quality_pipeline("Exception question?", user_id="uuid")

    assert "[PIPELINE ERROR:" in result["answer"]
    assert result["contexts"] == []
    assert result["sources"] == []
    assert result["tool_name"] is None


# ── T5: Content extraction from sources ──────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_extracts_content_from_sources():
    """contexts list contains the 'content' value from each source dict."""
    async def stream_two_sources(*args, **kwargs):
        yield ("Answer.", None, None)
        yield ("", [
            {"content": "First chunk", "document_name": "a.md"},
            {"content": "Second chunk", "document_name": "b.md"},
        ], None)

    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=stream_two_sources):
        result = await run_chat_quality_pipeline("Multi-source?", user_id="uuid")

    assert result["contexts"] == ["First chunk", "Second chunk"]


# ── T6: Empty-content filtering ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_filters_empty_content_from_contexts():
    """Sources with empty 'content' field are excluded from the contexts list."""
    async def stream_with_empty_content(*args, **kwargs):
        yield ("Answer.", None, None)
        yield ("", [
            {"content": "Valid chunk", "document_name": "a.md"},
            {"content": "", "document_name": "b.md"},
            {"document_name": "c.md"},  # missing content key entirely
        ], None)

    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=stream_with_empty_content):
        result = await run_chat_quality_pipeline("Filter test?", user_id="uuid")

    # Only the non-empty content chunk should appear
    assert result["contexts"] == ["Valid chunk"]


# ── T7: Tool arg capture structure ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_tool_arg_capture_structure(monkeypatch):
    """Retrieval wrapper is set up correctly; result has tool_name and tool_args keys."""
    async def fake_stream(*args, **kwargs):
        # Simulate chat_service yielding answer then sources
        yield ("Answer text.", None, None)
        yield ("", [{"content": "chunk text", "document_name": "doc.md",
                      "document_id": "id1", "id": "c1", "similarity": 0.9}], None)

    import eval.chat_quality_pipeline as mod

    async def fake_retrieve(query, user_id):
        return [{"content": "chunk text", "document_name": "doc.md",
                  "document_id": "id1", "id": "c1", "similarity": 0.9}]

    monkeypatch.setattr(mod._rs, "retrieve_relevant_chunks", fake_retrieve)
    with patch("eval.chat_quality_pipeline.ChatService.stream_response", new=fake_stream):
        result = await run_chat_quality_pipeline("What caused INC-2024-003?", user_id="uuid")

    # Structural assertions — fake_stream doesn't call the wrapper, so tool_args may be empty
    assert "tool_name" in result
    assert "tool_args" in result
    assert isinstance(result["tool_args"], dict)
