"""
Diagnostic script to check retrieval pipeline.
"""
import asyncio
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.retrieval_service import retrieval_service
from services.chat_service import chat_service

load_dotenv()

TEST_USER_EMAIL = "test@test.com"
TEST_USER_PASSWORD = "123456"


async def diagnose():
    """Run diagnostics on the retrieval system."""
    print("=" * 60)
    print("RETRIEVAL DIAGNOSTIC")
    print("=" * 60)

    supabase = get_supabase_admin()

    # Step 1: Get test user
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        user_id = auth_response.user.id
        print(f"\n[OK] Authenticated as: {TEST_USER_EMAIL}")
        print(f"  User ID: {user_id}")
    except Exception as e:
        print(f"\n[ERROR] Failed to authenticate: {e}")
        return

    # Step 2: Check documents
    try:
        docs_response = supabase.table("documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()

        documents = docs_response.data
        print(f"\n[OK] Found {len(documents)} document(s)")

        if documents:
            for doc in documents:
                print(f"  - {doc['filename']} (ID: {doc['id']})")
                print(f"    Status: {doc['status']}, Chunks: {doc['chunk_count']}")
        else:
            print("\n[WARN] No documents found!")
            print("  This is likely why retrieval isn't working.")
            print("  Upload a document first through the UI.")
            return

    except Exception as e:
        print(f"\n[ERROR] Failed to fetch documents: {e}")
        return

    # Step 3: Check chunks
    try:
        chunks_response = supabase.table("chunks")\
            .select("id, document_id, chunk_index, content")\
            .eq("user_id", user_id)\
            .execute()

        chunks = chunks_response.data
        print(f"\n[OK] Found {len(chunks)} chunk(s)")

        if chunks:
            # Show first chunk as sample
            print(f"  Sample chunk content: {chunks[0]['content'][:100]}...")
        else:
            print("\n[WARN] No chunks found!")
            print("  Documents exist but have no chunks.")
            print("  This means ingestion didn't complete properly.")
            return

    except Exception as e:
        print(f"\n[ERROR] Failed to fetch chunks: {e}")
        return

    # Step 4: Test retrieval
    print("\n" + "-" * 60)
    print("Testing retrieval with sample query...")
    print("-" * 60)

    test_query = "What's in the document?"

    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query=test_query,
            user_id=user_id
        )

        print(f"\n[OK] Retrieval returned {len(results)} result(s)")

        if results:
            for idx, result in enumerate(results):
                print(f"\n  Result {idx + 1}:")
                print(f"    Document: {result.get('document_name', 'Unknown')}")
                print(f"    Similarity: {result.get('similarity', 0):.3f}")
                print(f"    Content: {result['content'][:100]}...")
        else:
            print("\n[WARN] Retrieval returned no results!")
            print("  Possible causes:")
            print("  1. Query doesn't match document content (similarity too low)")
            print("  2. Similarity threshold (0.7) is too high")
            print("  3. Embedding mismatch")

    except Exception as e:
        print(f"\n[ERROR] Retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 5: Test tool calling (simulate what chat does)
    print("\n" + "-" * 60)
    print("Testing simulated chat with tool...")
    print("-" * 60)

    try:
        conversation_history = [
            {"role": "user", "content": "What's written in the 1st line of the document?"}
        ]

        print("\nStreaming response...")
        full_response = ""
        sources = None
        chunk_count = 0

        async for delta, chunk_sources in chat_service.stream_response(
            conversation_history=conversation_history,
            user_id=user_id,
            model="gpt-4o-mini",
            provider="openai"
        ):
            if delta:
                full_response += delta
                chunk_count += 1

            if chunk_sources:
                sources = chunk_sources

        print(f"\n[OK] Received {chunk_count} chunks")
        print(f"  Response length: {len(full_response)} chars")
        print(f"  Response: {full_response[:200]}...")

        if sources:
            print(f"\n[OK] Tool was called! Retrieved {len(sources)} source(s)")
            for idx, source in enumerate(sources):
                print(f"  {idx + 1}. {source['document_name']} (similarity: {source['similarity']:.3f})")
        else:
            print("\n[WARN] No sources returned!")
            print("  This means the LLM did NOT call the retrieval tool.")
            print("  Possible causes:")
            print("  1. LLM decided not to use the tool")
            print("  2. Tool definition not compelling enough")
            print("  3. Missing system prompt to encourage tool use")

    except Exception as e:
        print(f"\n[ERROR] Chat test failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(diagnose())
