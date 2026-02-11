from openai import OpenAI, AsyncOpenAI
from config import settings
from typing import AsyncGenerator, List, Dict
import asyncio

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Optional: Wrap with LangSmith if available
try:
    from langsmith.wrappers import wrap_openai
    client = wrap_openai(client)
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
        """Stream a response using OpenAI Chat Completions API.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation

        Yields:
            Text deltas from the streaming response
        """
        try:
            # Build request parameters
            request_params = {
                "model": model,
                "messages": conversation_history,
                "stream": True,
            }

            # Note: Vector stores with file_search require the Assistants API
            # For stateless chat completions, RAG must be implemented manually
            # by retrieving relevant chunks and adding them to the conversation

            stream = await async_client.chat.completions.create(**request_params)

            async for chunk in stream:
                # Extract content delta from chunk
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            raise Exception(f"Failed to stream response: {str(e)}")


openai_service = OpenAIService()
