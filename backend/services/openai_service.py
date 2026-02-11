from openai import OpenAI, AsyncOpenAI
from config import settings
from typing import AsyncGenerator
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
    def create_thread() -> str:
        """Create a new OpenAI thread and return its ID."""
        thread = client.beta.threads.create()
        return thread.id

    @staticmethod
    async def stream_message(
        thread_id: str,
        content: str,
        assistant_id: str = settings.OPENAI_ASSISTANT_ID
    ) -> AsyncGenerator[str, None]:
        """
        Add a user message to a thread and stream the assistant's response.

        Yields content deltas as they arrive from OpenAI.
        """
        # Add user message to thread
        await async_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )

        # Stream the assistant's response
        async with async_client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
        ) as stream:
            async for event in stream:
                # Check for message deltas
                if event.event == 'thread.message.delta':
                    delta = event.data.delta
                    if delta.content:
                        for content_block in delta.content:
                            if hasattr(content_block, 'text') and content_block.text:
                                yield content_block.text.value


openai_service = OpenAIService()
