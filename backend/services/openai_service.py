from openai import AsyncOpenAI
from config import settings
from typing import AsyncGenerator, List, Dict
import os
import time

# Initialize OpenAI client
async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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

    # Wrap OpenAI client for automatic tracing
    async_client = wrap_openai(async_client)

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
    """Service for OpenAI Responses API operations."""

    @staticmethod
    def build_conversation_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Build conversation history in Responses API format.

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
        model: str = "gpt-4o-mini"
    ) -> AsyncGenerator[str, None]:
        """Stream a response using OpenAI Responses API.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation

        Yields:
            Text deltas from the streaming response
        """
        full_response = ""
        trace_closed = False

        # Create LangSmith run if tracing is enabled
        run_id = None
        if langsmith_enabled and langsmith_client:
            try:
                import uuid
                from datetime import datetime, timezone
                run_id = uuid.uuid4()
                langsmith_client.create_run(
                    id=run_id,
                    name="openai_responses_stream",
                    run_type="llm",
                    inputs={
                        "messages": conversation_history,
                        "model": model,
                    },
                    project_name=os.getenv('LANGCHAIN_PROJECT'),
                    start_time=datetime.now(timezone.utc),
                )
            except Exception as e:
                print(f"[WARN] Failed to create LangSmith run: {e}")
                run_id = None

        try:
            # Build request parameters for Responses API
            request_params = {
                "model": model,
                "input": conversation_history,
                "store": False,  # Stateless - no data retention
            }

            # Add file_search tool if vector store is configured
            if settings.OPENAI_VECTOR_STORE_ID:
                request_params["tools"] = [
                    {
                        "type": "file_search",
                        "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID]
                    }
                ]

            async with async_client.responses.stream(**request_params) as stream:
                async for event in stream:
                    # Check event type
                    event_type = getattr(event, 'type', None) or getattr(event, 'event', None)

                    # Handle text delta events
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, 'delta', None)
                        if delta:
                            full_response += delta
                            yield delta
                    # Handle completion event
                    elif event_type == "response.completed":
                        # Close LangSmith trace
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

                    # Handle errors
                    elif event_type == "error":
                        raise Exception(f"OpenAI API error: {event}")

            # Fallback: close trace if not already closed
            if langsmith_enabled and langsmith_client and run_id and not trace_closed:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        outputs={"content": full_response},
                        end_time=datetime.now(timezone.utc),
                    )
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

            print(f"[ERROR] Response streaming failed: {type(e).__name__}: {e}")
            raise Exception(f"Failed to stream response: {str(e)}")


openai_service = OpenAIService()
