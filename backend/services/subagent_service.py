"""Service for executing document-scoped sub-agent tasks."""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from models.subagent import SubAgentRequest, SubAgentResult, ReasoningStep
from services.document_service import read_full_document
from services.supabase_service import get_supabase_admin
from services.provider_service import provider_service

# Initialize LangSmith tracing
langsmith_enabled = False
langsmith_client = None

try:
    from langsmith import Client as LangSmithClient
    langsmith_client = LangSmithClient()
    langsmith_enabled = True
except ImportError:
    pass

# Configuration
MAX_RECURSION_DEPTH = 2
SUBAGENT_MODEL = "gpt-4o-mini"

# Tool definition for reading the full document (no-op since document is preloaded)
READ_FULL_DOCUMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "read_full_document",
        "description": "Read the full content of the document that has been provided to you. The document text is already included in your context, so use this only if you need to confirm you have the complete document.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why you want to re-read the document."
                }
            },
            "required": ["reason"]
        }
    }
}

SUBAGENT_SYSTEM_PROMPT = """You are a focused document analysis sub-agent. You have been given a specific task to perform on a document.

DOCUMENT CONTENT:
---
{document_text}
---

INSTRUCTIONS:
1. Analyze the document above carefully to complete the task.
2. Be thorough and precise in your analysis.
3. Base your response ONLY on the document content provided.
4. If the document does not contain enough information to complete the task, say so clearly.
5. Provide a clear, well-structured response."""


async def execute_subagent(request: SubAgentRequest, user_id: str) -> SubAgentResult:
    """Execute a sub-agent task against a specific document.

    Args:
        request: Sub-agent request with task details
        user_id: Authenticated user ID for RLS

    Returns:
        SubAgentResult with status, result, and reasoning steps
    """
    document_name = "unknown"
    run_id = None

    # Check recursion limit
    if request.parent_depth >= MAX_RECURSION_DEPTH:
        return SubAgentResult(
            status="failed",
            error="Recursion limit exceeded",
            document_name=document_name,
        )

    # Use caller-supplied document_name if available to skip an extra DB round-trip.
    # read_full_document internally validates the document exists, so we avoid calling
    # get_document_by_id separately when the caller already has the name.
    # If not supplied, do a cheap single-field lookup after confirming the doc exists.
    document_name = request.document_name or "unknown"

    try:
        document_text = await read_full_document(request.document_id, user_id)
    except HTTPException as e:
        error = "Document not found" if e.status_code == 404 else f"Failed to read document content: {e.detail}"
        return SubAgentResult(
            status="failed",
            error=error,
            document_name=document_name,
        )

    # Resolve document name if caller didn't supply it (single cheap field query)
    if not request.document_name:
        try:
            supabase = get_supabase_admin()
            resp = supabase.table("documents").select("filename").eq("id", request.document_id).single().execute()
            document_name = resp.data.get("filename", "unknown")
        except Exception:
            pass

    # Build isolated conversation
    system_message = SUBAGENT_SYSTEM_PROMPT.format(document_text=document_text)
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": request.task_description},
    ]

    # Create LangSmith trace
    if langsmith_enabled and langsmith_client:
        try:
            run_id = uuid.uuid4()
            langsmith_client.create_run(
                id=run_id,
                name="subagent_execution",
                run_type="llm",
                inputs={
                    "task_description": request.task_description,
                    "document_id": request.document_id,
                    "document_name": document_name,
                    "model": SUBAGENT_MODEL,
                    "parent_depth": request.parent_depth,
                },
                project_name=os.getenv("LANGCHAIN_PROJECT"),
                start_time=datetime.now(timezone.utc),
            )
        except Exception:
            run_id = None

    # Stream response — collect chunks into a list to avoid O(n²) string concatenation.
    # Reasoning steps represent meaningful analysis phases, not individual tokens.
    response_parts = []
    start_time = datetime.now(timezone.utc).isoformat()

    try:
        async for chunk in provider_service.stream_chat_completion(
            provider="openai",
            model=SUBAGENT_MODEL,
            messages=messages,
            tools=[READ_FULL_DOCUMENT_TOOL],
            temperature=0.3,
        ):
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    response_parts.append(delta.content)

        full_response = "".join(response_parts)

        # Two meaningful steps: document read + analysis result (not one per token)
        reasoning_steps = [
            ReasoningStep(step_number=1, content="Read and analyzed document content", timestamp=start_time),
            ReasoningStep(step_number=2, content=full_response, timestamp=datetime.now(timezone.utc).isoformat()),
        ]

        # Close LangSmith trace on success
        if langsmith_enabled and langsmith_client and run_id:
            try:
                langsmith_client.update_run(
                    run_id=run_id,
                    outputs={
                        "content": full_response,
                        "document_name": document_name,
                        "step_count": len(reasoning_steps),
                    },
                    end_time=datetime.now(timezone.utc),
                )
            except Exception:
                pass

        return SubAgentResult(
            status="completed",
            result=full_response,
            reasoning_steps=reasoning_steps,
            document_name=document_name,
        )

    except Exception as e:
        # Close trace with error
        if langsmith_enabled and langsmith_client and run_id:
            try:
                langsmith_client.update_run(
                    run_id=run_id,
                    error=str(e),
                    end_time=datetime.now(timezone.utc),
                )
            except Exception:
                pass

        return SubAgentResult(
            status="failed",
            error=f"Sub-agent execution failed: {str(e)}",
            document_name=document_name,
        )
