"""Service for executing document-scoped sub-agent tasks."""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from models.subagent import SubAgentRequest, SubAgentResult, ReasoningStep
from services.document_service import get_document_by_id, read_full_document
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

    # Read document
    try:
        document = get_document_by_id(request.document_id, user_id)
        document_name = document.get("filename", "unknown")
    except HTTPException as e:
        if e.status_code == 404:
            return SubAgentResult(
                status="failed",
                error="Document not found",
                document_name=document_name,
            )
        return SubAgentResult(
            status="failed",
            error=f"Failed to fetch document: {e.detail}",
            document_name=document_name,
        )

    try:
        document_text = await read_full_document(request.document_id, user_id)
    except HTTPException as e:
        return SubAgentResult(
            status="failed",
            error=f"Failed to read document content: {e.detail}",
            document_name=document_name,
        )

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

    # Stream response and collect reasoning steps
    full_response = ""
    reasoning_steps = []
    step_number = 0

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
                    full_response += delta.content
                    step_number += 1
                    reasoning_steps.append(
                        ReasoningStep(
                            step_number=step_number,
                            content=delta.content,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )

        # Close LangSmith trace on success
        if langsmith_enabled and langsmith_client and run_id:
            try:
                langsmith_client.update_run(
                    run_id=run_id,
                    outputs={
                        "content": full_response,
                        "document_name": document_name,
                        "step_count": step_number,
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
            reasoning_steps=reasoning_steps,
            document_name=document_name,
        )
