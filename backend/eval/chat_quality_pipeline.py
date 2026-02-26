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
from services.retrieval_service import retrieval_service as _rs
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
