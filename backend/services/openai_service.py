from openai import AsyncOpenAI
from config import settings
from typing import AsyncGenerator, List, Dict, Tuple, Optional
import os
import time
import json

# Initialize default OpenAI client
default_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Initialize LangSmith tracing
langsmith_enabled = False
langsmith_client = None

try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable as ls_traceable
    from langsmith.wrappers import wrap_openai

    langsmith_client = LangSmithClient()

    # Wrap default OpenAI client for automatic tracing
    default_client = wrap_openai(default_client)
    langsmith_enabled = True

except ImportError:
    ls_traceable = lambda *args, **kwargs: lambda f: f  # No-op decorator


class OpenAIService:
    """Service for OpenAI-compatible Chat Completions API operations."""

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
    def _get_client(base_url: str | None = None, api_key: str | None = None) -> AsyncOpenAI:
        """Get OpenAI client with custom configuration.

        Args:
            base_url: Optional custom base URL
            api_key: Optional custom API key

        Returns:
            Configured AsyncOpenAI client
        """
        # Use custom config if provided, otherwise use default client
        if base_url or api_key:
            client_kwargs = {}
            if base_url:
                client_kwargs["base_url"] = base_url
            if api_key:
                client_kwargs["api_key"] = api_key
            else:
                # Use default API key if only base_url is custom
                client_kwargs["api_key"] = settings.OPENAI_API_KEY

            client = AsyncOpenAI(**client_kwargs)

            # Wrap with LangSmith if enabled
            if langsmith_enabled:
                try:
                    client = wrap_openai(client)
                except Exception:
                    pass  # Continue without tracing for custom client

            return client

        return default_client

    @staticmethod
    async def stream_response(
        conversation_history: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
        user_id: str | None = None
    ) -> AsyncGenerator[Tuple[str, Optional[List[Dict]]], None]:
        """Stream a response using OpenAI Chat Completions API with tool calling support.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation
            base_url: Optional custom base URL for provider
            api_key: Optional custom API key
            user_id: Optional user ID for retrieval RLS filtering

        Yields:
            Tuples of (text_delta, sources) where sources is populated on final yield
        """
        full_response = ""
        trace_closed = False
        sources = None

        # Get client with custom config if provided
        client = OpenAIService._get_client(base_url, api_key)

        # Create LangSmith run if tracing is enabled
        run_id = None
        if langsmith_enabled and langsmith_client:
            try:
                import uuid
                from datetime import datetime, timezone
                run_id = uuid.uuid4()
                langsmith_client.create_run(
                    id=run_id,
                    name="openai_chat_completions_stream",
                    run_type="llm",
                    inputs={
                        "messages": conversation_history,
                        "model": model,
                        "base_url": base_url,
                    },
                    project_name=os.getenv('LANGCHAIN_PROJECT'),
                    start_time=datetime.now(timezone.utc),
                )
            except Exception:
                run_id = None

        try:
            # Call Chat Completions API with streaming and tools
            stream = await client.chat.completions.create(
                model=model,
                messages=conversation_history,
                stream=True,
                temperature=0.7,
                tools=[OpenAIService.RETRIEVAL_TOOL],
                tool_choice="auto"
            )

            # Track tool calls
            tool_calls = []
            current_tool_call = None

            # Process streaming response
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # Handle content delta
                    if delta.content:
                        full_response += delta.content
                        yield (delta.content, None)

                    # Handle tool call deltas
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            # Initialize new tool call
                            if tool_call_delta.index is not None:
                                while len(tool_calls) <= tool_call_delta.index:
                                    tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                current_tool_call = tool_calls[tool_call_delta.index]

                            # Update tool call data
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
                        # Parse arguments
                        args = json.loads(tool_call["function"]["arguments"])
                        query = args.get("query", "")

                        # Retrieve relevant chunks
                        chunks = await retrieval_service.retrieve_relevant_chunks(
                            query=query,
                            user_id=user_id
                        )

                        # Format chunks as context
                        context_text = "\n\n".join([
                            f"Document: {chunk['document_name']}\n{chunk['content']}"
                            for chunk in chunks
                        ])

                        # Store sources for frontend
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

                        # Append tool call and result to conversation
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

                        # Make follow-up request with context
                        follow_up_stream = await client.chat.completions.create(
                            model=model,
                            messages=conversation_history,
                            stream=True,
                            temperature=0.7,
                        )

                        # Stream the final response
                        async for chunk in follow_up_stream:
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


openai_service = OpenAIService()
