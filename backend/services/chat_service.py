from config import settings
from services.provider_service import provider_service
from typing import AsyncGenerator, List, Dict, Tuple, Optional
import os
import json

# Initialize LangSmith tracing
langsmith_enabled = False
langsmith_client = None

try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable as ls_traceable

    langsmith_client = LangSmithClient()
    langsmith_enabled = True

except ImportError:
    ls_traceable = lambda *args, **kwargs: lambda f: f  # No-op decorator


class ChatService:
    """Provider-agnostic service for chat completions with tool calling support."""

    # Tool definition for document retrieval
    RETRIEVAL_TOOL = {
        "type": "function",
        "function": {
            "name": "retrieve_documents",
            "description": "Search and retrieve relevant document chunks from the user's knowledge base to help answer questions. Use this when you need specific information from uploaded documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant document chunks"
                    }
                },
                "required": ["query"]
            }
        }
    }

    @staticmethod
    def build_conversation_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Build conversation history in Chat Completions format.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            List of message dicts in OpenAI format
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

    @staticmethod
    async def stream_response(
        conversation_history: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        base_url: str | None = None,
        user_id: str | None = None
    ) -> AsyncGenerator[Tuple[str, Optional[List[Dict]]], None]:
        """Stream a response using the specified provider with tool calling support.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation
            provider: Provider identifier
            base_url: Optional custom base URL for provider
            user_id: Optional user ID for retrieval RLS filtering

        Yields:
            Tuples of (text_delta, sources) where sources is populated on final yield
        """
        full_response = ""
        trace_closed = False
        sources = None

        # Create LangSmith run if tracing is enabled
        run_id = None
        if langsmith_enabled and langsmith_client:
            try:
                import uuid
                from datetime import datetime, timezone
                run_id = uuid.uuid4()
                langsmith_client.create_run(
                    id=run_id,
                    name="chat_completions_stream",
                    run_type="llm",
                    inputs={
                        "messages": conversation_history,
                        "model": model,
                        "provider": provider,
                        "base_url": base_url,
                    },
                    project_name=os.getenv('LANGCHAIN_PROJECT'),
                    start_time=datetime.now(timezone.utc),
                )
            except Exception:
                run_id = None

        try:
            # Stream from provider with tools
            tool_calls = []
            current_tool_call = None

            async for chunk in provider_service.stream_chat_completion(
                provider=provider,
                model=model,
                messages=conversation_history,
                base_url=base_url,
                tools=[ChatService.RETRIEVAL_TOOL],
            ):
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # Handle content delta
                    if delta.content:
                        full_response += delta.content
                        yield (delta.content, None)

                    # Handle tool call deltas
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            if tool_call_delta.index is not None:
                                while len(tool_calls) <= tool_call_delta.index:
                                    tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                current_tool_call = tool_calls[tool_call_delta.index]

                            if tool_call_delta.id:
                                current_tool_call["id"] = tool_call_delta.id
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    current_tool_call["function"]["name"] = tool_call_delta.function.name
                                if tool_call_delta.function.arguments:
                                    current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments

            # If tool calls were detected, execute them and continue
            if tool_calls and user_id:
                from services.retrieval_service import retrieval_service

                for tool_call in tool_calls:
                    if tool_call["function"]["name"] == "retrieve_documents":
                        args = json.loads(tool_call["function"]["arguments"])
                        query = args.get("query", "")

                        chunks = await retrieval_service.retrieve_relevant_chunks(
                            query=query,
                            user_id=user_id
                        )

                        context_text = "\n\n".join([
                            f"Document: {chunk['document_name']}\n{chunk['content']}"
                            for chunk in chunks
                        ])

                        sources = [
                            {
                                "document_id": chunk["document_id"],
                                "document_name": chunk["document_name"],
                                "chunk_id": chunk["id"],
                                "content": chunk["content"],
                                "similarity": chunk["similarity"]
                            }
                            for chunk in chunks
                        ]

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "retrieve_documents",
                                    "arguments": tool_call["function"]["arguments"]
                                }
                            }]
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": context_text
                        })

                        # Follow-up stream without tools
                        async for chunk in provider_service.stream_chat_completion(
                            provider=provider,
                            model=model,
                            messages=conversation_history,
                            base_url=base_url,
                        ):
                            if chunk.choices and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                if delta.content:
                                    full_response += delta.content
                                    yield (delta.content, None)

            # Yield sources on final message (if any)
            if sources:
                yield ("", sources)

            # Close LangSmith trace on success
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        outputs={"content": full_response, "sources": sources},
                        end_time=datetime.now(timezone.utc),
                    )
                    trace_closed = True
                except Exception:
                    pass

        except Exception as e:
            # Close trace with error
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        error=str(e),
                        end_time=datetime.now(timezone.utc),
                    )
                except:
                    pass

            raise Exception(f"Failed to stream response: {str(e)}")


chat_service = ChatService()
