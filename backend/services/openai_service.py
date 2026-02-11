from openai import AsyncOpenAI
from config import settings
from typing import AsyncGenerator, List, Dict

# Initialize OpenAI client
async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Optional: Wrap with LangSmith if available
try:
    from langsmith.wrappers import wrap_openai
    async_client = wrap_openai(async_client)
    print("[OK] LangSmith wrapper applied to OpenAI client")
except ImportError:
    print("[WARN] LangSmith not available - continuing without tracing")


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
                print(f"[INFO] Using vector store: {settings.OPENAI_VECTOR_STORE_ID}")

            # Stream response using Responses API
            print(f"[DEBUG] Calling responses.stream() with params: {list(request_params.keys())}")
            async with async_client.responses.stream(**request_params) as stream:
                async for event in stream:
                    # Check event type
                    event_type = getattr(event, 'type', None) or getattr(event, 'event', None)

                    # Handle text delta events
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, 'delta', None)
                        if delta:
                            yield delta
                    # Handle done event
                    elif event_type == "response.done":
                        print("[DEBUG] Response stream completed")
                    # Handle errors
                    elif event_type == "error":
                        raise Exception(f"OpenAI API error: {event}")

        except Exception as e:
            print(f"[ERROR] Response streaming failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to stream response: {str(e)}")


openai_service = OpenAIService()
