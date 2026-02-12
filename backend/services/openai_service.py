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

    # Verify API key is valid
    try:
        print("[DEBUG] Testing LangSmith API key...")
        # This will make a simple API call to verify credentials
        projects = list(langsmith_client.list_projects(limit=1))
        print(f"✓ LangSmith API key is VALID (found {len(projects)} project(s))")
    except Exception as e:
        print(f"✗ LangSmith API key test FAILED: {e}")
        print(f"[ERROR] Your LangSmith API key might be invalid or expired")
        raise

    # Wrap default OpenAI client for automatic tracing
    default_client = wrap_openai(default_client)

    langsmith_enabled = True
    print("=" * 60)
    print("✓ LangSmith OpenAI wrapper applied successfully")
    print(f"✓ LangSmith tracing: {os.getenv('LANGCHAIN_TRACING_V2', 'not set')}")
    print(f"✓ LangSmith project: {os.getenv('LANGCHAIN_PROJECT', 'not set')}")
    print(f"✓ LangSmith API key: {'SET' if os.getenv('LANGCHAIN_API_KEY') else 'NOT SET'}")

    # Test trace on startup
    try:
        import uuid
        project_name = os.getenv('LANGCHAIN_PROJECT')
        run_id = uuid.uuid4()
        langsmith_client.create_run(
            name="backend_startup_test",
            run_type="chain",
            inputs={"test": "connection"},
            project_name=project_name,
            id=run_id,
        )
        langsmith_client.update_run(
            run_id=run_id,
            outputs={"status": "success", "message": "Backend started successfully"}
        )
        print(f"✓ LangSmith connection test successful (project: {project_name})")
    except Exception as e:
        print(f"⚠ LangSmith connection test failed: {e}")

    print("=" * 60)
except ImportError as e:
    print(f"[WARN] LangSmith not available - continuing without tracing: {e}")
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
                except Exception as e:
                    print(f"[WARN] Failed to wrap custom client with LangSmith: {e}")

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
            except Exception as e:
                print(f"[WARN] Failed to create LangSmith run: {e}")
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
                except Exception as e:
                    print(f"[ERROR] Failed to close LangSmith run: {e}")

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

            print(f"[ERROR] Chat Completions streaming failed: {type(e).__name__}: {e}")
            raise Exception(f"Failed to stream response: {str(e)}")


openai_service = OpenAIService()
