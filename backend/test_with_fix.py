"""Test with the fix applied (threshold 0.4 + system prompt)."""
import asyncio
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.chat_service import chat_service

# Force reload of config
import importlib
import config
importlib.reload(config)
from config import settings

load_dotenv()

async def test():
    print("=" * 60)
    print("TEST WITH FIX APPLIED")
    print("=" * 60)

    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": "test@...",
        "password": "***"
    })
    user_id = auth_response.user.id

    print(f"\n[CONFIG] Similarity threshold: {settings.RETRIEVAL_SIMILARITY_THRESHOLD}")
    print(f"[CONFIG] Retrieval limit: {settings.RETRIEVAL_LIMIT}")

    # Test with a more general query that should match better
    conversation_history = [
        {"role": "user", "content": "What's in my uploaded document?"}
    ]

    print("\nTest 1: General query about document content")
    print("-" * 60)
    full_response = ""
    sources = None

    async for delta, chunk_sources in chat_service.stream_response(
        conversation_history=conversation_history,
        user_id=user_id,
        model="gpt-4o-mini",
        provider="openai"
    ):
        if delta:
            full_response += delta
        if chunk_sources:
            sources = chunk_sources

    print(f"\nResponse: {full_response[:300]}...")

    if sources:
        print(f"\n✓ SUCCESS! Tool was called and returned {len(sources)} source(s)")
        for idx, source in enumerate(sources):
            print(f"  {idx + 1}. {source['document_name']} (similarity: {source['similarity']:.3f})")
            print(f"     Content: {source['content'][:80]}...")
    else:
        print("\n✗ FAILED: No sources returned")

    # Test 2: Try the user's specific query
    conversation_history2 = [
        {"role": "user", "content": "What is the first line of text in the document?"}
    ]

    print("\n\nTest 2: User's specific query (first line)")
    print("-" * 60)
    full_response2 = ""
    sources2 = None

    async for delta, chunk_sources in chat_service.stream_response(
        conversation_history=conversation_history2,
        user_id=user_id,
        model="gpt-4o-mini",
        provider="openai"
    ):
        if delta:
            full_response2 += delta
        if chunk_sources:
            sources2 = chunk_sources

    print(f"\nResponse: {full_response2[:300]}...")

    if sources2:
        print(f"\n✓ SUCCESS! Tool returned {len(sources2)} source(s)")
    else:
        print("\n✗ FAILED: No sources returned (query too specific)")

if __name__ == "__main__":
    asyncio.run(test())
