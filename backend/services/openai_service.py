from openai import AsyncOpenAI
from config import settings
from typing import AsyncGenerator, List, Dict
import os
import time

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
        api_key: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream a response using OpenAI Chat Completions API.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation
            base_url: Optional custom base URL for provider
            api_key: Optional custom API key

        Yields:
            Text deltas from the streaming response
        """
        full_response = ""
        trace_closed = False

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
            # Call Chat Completions API with streaming
            stream = await client.chat.completions.create(
                model=model,
                messages=conversation_history,
                stream=True,
                temperature=0.7,
            )

            # Process streaming response
            async for chunk in stream:
                # Extract content delta from chunk
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_response += delta.content
                        yield delta.content

            # Close LangSmith trace on success
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        outputs={"content": full_response},
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
