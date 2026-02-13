from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from middleware.auth_middleware import get_current_user
from services.supabase_service import get_supabase_admin
from services.openai_service import openai_service, default_client
from services.provider_service import provider_service
from models.thread import ThreadCreate, ThreadResponse
from models.message import MessageCreate, MessageResponse
from typing import List
import json
from datetime import datetime
from config import settings

router = APIRouter()


@router.get("/providers")
async def get_providers():
    """Get available LLM provider presets."""
    return {
        "providers": provider_service.get_providers(),
        "defaults": {
            "provider": settings.DEFAULT_PROVIDER,
            "model": settings.DEFAULT_MODEL,
            "base_url": settings.DEFAULT_BASE_URL
        }
    }


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat thread."""
    supabase = get_supabase_admin()

    # Save to database
    response = supabase.table("threads").insert({
        "user_id": current_user["id"],
        "title": thread_data.title
    }).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create thread")

    thread = response.data[0]

    return ThreadResponse(
        id=str(thread["id"]),
        title=thread["title"],
        created_at=str(thread["created_at"]),
        updated_at=str(thread["updated_at"])
    )


@router.get("/threads", response_model=List[ThreadResponse])
async def list_threads(current_user: dict = Depends(get_current_user)):
    """List all threads for the current user."""
    try:
        supabase = get_supabase_admin()

        response = supabase.table("threads")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .order("created_at", desc=True)\
            .execute()

        return [
            ThreadResponse(
                id=str(thread["id"]),
                title=thread["title"],
                created_at=str(thread["created_at"]),
                updated_at=str(thread["updated_at"])
            )
            for thread in response.data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}")


@router.post("/threads/{thread_id}/generate-title", response_model=ThreadResponse)
async def generate_thread_title(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a title for a thread based on the first user message."""
    supabase = get_supabase_admin()

    # Verify thread ownership
    thread_response = supabase.table("threads")\
        .select("*")\
        .eq("id", thread_id)\
        .eq("user_id", current_user["id"])\
        .single()\
        .execute()

    if not thread_response.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get the first user message
    messages_response = supabase.table("messages")\
        .select("*")\
        .eq("thread_id", thread_id)\
        .eq("role", "user")\
        .order("created_at")\
        .limit(1)\
        .execute()

    if not messages_response.data:
        raise HTTPException(status_code=400, detail="No messages in thread")

    first_message = messages_response.data[0]["content"]

    # Generate title using LLM
    try:
        response = await default_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a concise, 3-7 word title for a conversation that starts with the following user message. Return only the title, nothing else."
                },
                {
                    "role": "user",
                    "content": first_message
                }
            ],
            temperature=0.7,
            max_tokens=20
        )

        # Validate response
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from LLM")

        generated_title = response.choices[0].message.content.strip()

        # Remove quotes if present
        if generated_title.startswith('"') and generated_title.endswith('"'):
            generated_title = generated_title[1:-1]

        # Fallback if title is still empty
        if not generated_title:
            generated_title = first_message[:50] + ("..." if len(first_message) > 50 else "")

    except Exception as e:
        # Fallback to first 50 chars of message if title generation fails
        generated_title = first_message[:50] + ("..." if len(first_message) > 50 else "")

    # Update thread title
    update_response = supabase.table("threads")\
        .update({"title": generated_title})\
        .eq("id", thread_id)\
        .execute()

    if not update_response.data:
        raise HTTPException(status_code=500, detail="Failed to update thread title")

    updated_thread = update_response.data[0]

    return ThreadResponse(
        id=str(updated_thread["id"]),
        title=updated_thread["title"],
        created_at=str(updated_thread["created_at"]),
        updated_at=str(updated_thread["updated_at"])
    )


@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all messages in a thread."""
    supabase = get_supabase_admin()

    # Verify thread ownership
    thread_response = supabase.table("threads")\
        .select("*")\
        .eq("id", thread_id)\
        .eq("user_id", current_user["id"])\
        .single()\
        .execute()

    if not thread_response.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get messages
    messages_response = supabase.table("messages")\
        .select("*")\
        .eq("thread_id", thread_id)\
        .order("created_at")\
        .execute()

    return [
        MessageResponse(
            id=str(msg["id"]),
            thread_id=str(msg["thread_id"]),
            role=msg["role"],
            content=msg["content"],
            created_at=str(msg["created_at"]),
            sources=msg.get("sources")
        )
        for msg in messages_response.data
    ]


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str,
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message and stream the response via SSE."""
    supabase = get_supabase_admin()

    # Verify thread ownership
    thread_response = supabase.table("threads")\
        .select("*")\
        .eq("id", thread_id)\
        .eq("user_id", current_user["id"])\
        .single()\
        .execute()

    if not thread_response.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread = thread_response.data

    # Fetch conversation history for this thread
    history_response = supabase.table("messages")\
        .select("role, content")\
        .eq("thread_id", thread_id)\
        .order("created_at")\
        .execute()

    # Build conversation history
    conversation_history = openai_service.build_conversation_history(
        history_response.data
    )

    # Add current user message to history
    conversation_history.append({
        "role": "user",
        "content": message_data.content
    })

    # Save user message
    user_message_response = supabase.table("messages").insert({
        "thread_id": thread_id,
        "user_id": current_user["id"],
        "role": "user",
        "content": message_data.content
    }).execute()

    if not user_message_response.data:
        raise HTTPException(status_code=500, detail="Failed to save message")

    # Validate provider configuration
    is_valid, error_msg = provider_service.validate_provider_config(
        provider=message_data.provider,
        model=message_data.model,
        base_url=message_data.base_url,
        has_default_api_key=bool(settings.OPENAI_API_KEY)
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Stream assistant response
    async def event_generator():
        full_response = ""
        chunk_count = 0
        sources = None

        try:
            # Determine base_url and api_key
            base_url = message_data.base_url
            api_key = None

            # If no base_url provided, get from provider preset
            if not base_url:
                provider_config = provider_service.get_provider_config(message_data.provider)
                if provider_config:
                    base_url = provider_config.get("base_url")

            # Use server-side api_key for providers that require it
            provider_config = provider_service.get_provider_config(message_data.provider)
            if provider_config and provider_config.get("requires_api_key"):
                api_key = settings.OPENAI_API_KEY

            async for delta, chunk_sources in openai_service.stream_response(
                conversation_history,
                model=message_data.model,
                base_url=base_url,
                api_key=api_key,
                user_id=current_user["id"]
            ):
                chunk_count += 1

                # Handle content delta
                if delta:
                    full_response += delta
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "content_delta", "delta": delta})
                    }

                # Store sources if received
                if chunk_sources:
                    sources = chunk_sources

            # Save assistant message with sources
            message_data_to_insert = {
                "thread_id": thread_id,
                "user_id": current_user["id"],
                "role": "assistant",
                "content": full_response
            }

            # Add sources if available
            if sources:
                message_data_to_insert["sources"] = sources

            supabase.table("messages").insert(message_data_to_insert).execute()

            # Update thread timestamp
            supabase.table("threads")\
                .update({"updated_at": datetime.utcnow().isoformat()})\
                .eq("id", thread_id)\
                .execute()

            yield {"event": "message", "data": "[DONE]"}

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a thread and all its messages."""
    supabase = get_supabase_admin()

    # Verify ownership
    thread_response = supabase.table("threads")\
        .select("*")\
        .eq("id", thread_id)\
        .eq("user_id", current_user["id"])\
        .single()\
        .execute()

    if not thread_response.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Delete messages first
    supabase.table("messages")\
        .delete()\
        .eq("thread_id", thread_id)\
        .execute()

    # Delete thread
    supabase.table("threads")\
        .delete()\
        .eq("id", thread_id)\
        .execute()

    return {"message": "Thread deleted successfully"}
