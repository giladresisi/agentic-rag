"""Test retrieval with the actual document."""
import asyncio
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.supabase_service import get_supabase_admin
from services.retrieval_service import retrieval_service
from services.chat_service import chat_service

load_dotenv()

async def test_retrieval():
    print("=" * 60)
    print("TESTING ACTUAL RETRIEVAL")
    print("=" * 60)

    supabase = get_supabase_admin()

    # Auth
    auth_response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    user_id = auth_response.user.id
    print(f"\n[OK] User ID: {user_id}")

    # Get the document content to know what to search for
    doc_response = supabase.table("documents").select("*").eq("user_id", user_id).execute()
    doc = doc_response.data[0]
    print(f"\n[OK] Document: {doc['filename']}")
    print(f"     Status: {doc['status']}, Chunks: {doc['chunk_count']}")

    # Get the actual chunk content
    chunks_response = supabase.table("chunks").select("*").eq("user_id", user_id).execute()
    if chunks_response.data:
        chunk = chunks_response.data[0]
        print(f"\n[OK] Chunk content (first 200 chars):")
        print(f"     {chunk['content'][:200]}")
        print(f"     ...")

        # Show embedding info
        embedding = chunk.get('embedding')
        if embedding:
            print(f"\n[OK] Embedding dimensions: {len(embedding)}")
        else:
            print("\n[WARN] No embedding found!")

    # Test 1: Direct retrieval with low threshold
    print("\n" + "-" * 60)
    print("Test 1: Direct retrieval (threshold=0.3)")
    print("-" * 60)

    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query="What's in the document?",
            user_id=user_id,
            similarity_threshold=0.3
        )

        print(f"\n[OK] Retrieved {len(results)} result(s)")
        for idx, result in enumerate(results):
            print(f"\n  Result {idx + 1}:")
            print(f"    Document: {result.get('document_name', 'Unknown')}")
            print(f"    Similarity: {result.get('similarity', 0):.3f}")
            print(f"    Content: {result['content'][:100]}...")

    except Exception as e:
        print(f"\n[ERROR] Retrieval failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Retrieval with default threshold (0.7)
    print("\n" + "-" * 60)
    print("Test 2: Direct retrieval (threshold=0.7 - default)")
    print("-" * 60)

    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query="What's in the document?",
            user_id=user_id,
            similarity_threshold=0.7
        )

        print(f"\n[OK] Retrieved {len(results)} result(s)")
        if not results:
            print("  [WARN] No results with high threshold - try lowering it")

    except Exception as e:
        print(f"\n[ERROR] Retrieval failed: {e}")

    # Test 3: Query asking about first line (user's actual question)
    print("\n" + "-" * 60)
    print("Test 3: User's actual query - 'What's written in the 1st line?'")
    print("-" * 60)

    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query="What's written in the 1st line of the single uploaded document?",
            user_id=user_id,
            similarity_threshold=0.5
        )

        print(f"\n[OK] Retrieved {len(results)} result(s)")
        for idx, result in enumerate(results):
            print(f"  Result {idx + 1}: similarity={result.get('similarity', 0):.3f}")

    except Exception as e:
        print(f"\n[ERROR] Retrieval failed: {e}")

    # Test 4: Full chat with tool calling
    print("\n" + "-" * 60)
    print("Test 4: Chat with tool calling (user's exact scenario)")
    print("-" * 60)

    try:
        conversation_history = [
            {"role": "user", "content": "What's written in the 1st line of the single uploaded document?"}
        ]

        print("\nStreaming response...")
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

        print(f"\n[OK] Response: {full_response[:300]}...")

        if sources:
            print(f"\n[OK] TOOL WAS CALLED! {len(sources)} source(s)")
            for idx, source in enumerate(sources):
                print(f"  {idx + 1}. {source['document_name']} (similarity: {source['similarity']:.3f})")
        else:
            print("\n[PROBLEM] Tool was NOT called!")
            print("  The LLM decided not to use the retrieval tool.")
            print("  This is why you're getting 'I'm unable to access...'")

    except Exception as e:
        print(f"\n[ERROR] Chat failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_retrieval())
