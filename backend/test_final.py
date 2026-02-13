"""Final E2E test with config reload."""
import sys
import asyncio

# Force fresh imports
for module in list(sys.modules.keys()):
    if module.startswith('config') or module.startswith('services'):
        del sys.modules[module]

from dotenv import load_dotenv
load_dotenv()

from services.supabase_service import get_supabase_admin
from services.chat_service import chat_service
from config import settings

async def test():
    print("=" * 70)
    print("FINAL RETRIEVAL TEST")
    print("=" * 70)

    print(f"\n[CONFIG] Similarity threshold: {settings.RETRIEVAL_SIMILARITY_THRESHOLD}")

    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": "test@...",
        "password": "***"
    })
    user_id = auth_response.user.id

    print(f"[OK] Authenticated as test@...")

    conversation_history = [
        {"role": "user", "content": "Tell me about the content in my document."}
    ]

    print("\n[TEST] Running chat with tool calling...")
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

    print(f"\n[RESULT] Response length: {len(full_response)} chars")
    print(f"[RESULT] Response: {full_response[:200]}...")

    if sources:
        print(f"\n[PASS] Tool returned {len(sources)} source(s)!")
        for idx, source in enumerate(sources):
            print(f"  {idx+1}. {source['document_name']} (similarity: {source['similarity']:.3f})")
        print("\n" + "=" * 70)
        print("[PASS] TEST PASSED - Retrieval is working!")
        print("=" * 70)
        return 0
    else:
        print("\n[FAIL] No sources returned")
        print("=" * 70)
        print("[FAIL] TEST FAILED")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test())
    sys.exit(exit_code)
