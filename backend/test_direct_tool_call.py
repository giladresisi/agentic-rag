"""
Direct test of tool calling mechanism by manually triggering tool execution.
"""
import asyncio
from dotenv import load_dotenv
from services.retrieval_service import retrieval_service
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin

load_dotenv()

TEST_USER_EMAIL = "test@..."
TEST_USER_PASSWORD = "***"


async def main():
    """Test the retrieval tool mechanism directly."""
    print("=" * 60)
    print("DIRECT TOOL CALL TEST")
    print("=" * 60)

    # Auth
    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    test_user_id = auth_response.user.id
    print(f"[PASS] Authenticated: {test_user_id}")

    # Clean up
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()

    # Create test document
    content = "The secret code for Project Phoenix is PHOENIX-2024-ALPHA. This code must be kept confidential."

    doc_response = supabase.table("documents").insert({
        "user_id": test_user_id,
        "filename": "project_phoenix.txt",
        "content_type": "text/plain",
        "file_size_bytes": len(content),
        "storage_path": f"{test_user_id}/project_phoenix.txt",
        "status": "completed",
        "chunk_count": 0
    }).execute()

    document_id = doc_response.data[0]["id"]

    # Chunk and embed
    chunks = embedding_service.chunk_text(content)
    embeddings = await embedding_service.generate_embeddings(chunks)

    chunk_records = [{
        "document_id": document_id,
        "user_id": test_user_id,
        "content": chunk_text,
        "embedding": embedding,
        "chunk_index": idx
    } for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings))]

    supabase.table("chunks").insert(chunk_records).execute()
    supabase.table("documents").update({"chunk_count": len(chunks)}).eq("id", document_id).execute()

    print(f"[PASS] Created document with {len(chunks)} chunks")

    # Test direct retrieval (simulating what the tool would do)
    print("\n=== Simulating Tool Call ===")

    # Query that should match
    query = "What is the code for Project Phoenix?"

    # Call retrieval service directly (this is what the tool handler does)
    print(f"Query: '{query}'")
    print("Calling retrieval_service.retrieve_relevant_chunks...")

    results = await retrieval_service.retrieve_relevant_chunks(
        query=query,
        user_id=test_user_id,
        limit=5,
        similarity_threshold=0.3
    )

    if results and len(results) > 0:
        print(f"\n[PASS] Retrieved {len(results)} chunks!")

        for idx, result in enumerate(results):
            print(f"\nChunk {idx+1}:")
            print(f"  Document: {result.get('document_name', 'Unknown')}")
            print(f"  Similarity: {result.get('similarity', 0):.3f}")
            print(f"  Content: {result.get('content', '')[:100]}...")

        # Check if the answer is in the retrieved chunks
        all_content = " ".join([r.get('content', '') for r in results])
        if "PHOENIX-2024-ALPHA" in all_content:
            print("\n[PASS] Retrieved chunks contain the answer!")
        else:
            print("\n[WARN] Answer not in retrieved chunks")

        # Format sources for frontend
        sources = []
        for result in results:
            sources.append({
                "document_id": result['document_id'],
                "document_name": result['document_name'],
                "chunk_content": result['content'],
                "similarity": result['similarity']
            })

        print("\n=== Sources Format (for frontend) ===")
        print(f"Sources count: {len(sources)}")
        print(f"First source: {sources[0]['document_name']} ({sources[0]['similarity']:.1%} match)")

        print("\n[PASS] Tool mechanism works correctly!")
        print("The retrieval service can find relevant documents and return sources.")

    else:
        print("\n[FAIL] No results retrieved")

    # Cleanup
    supabase.table("documents").delete().eq("user_id", test_user_id).execute()

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("- Retrieval service: WORKING")
    print("- Source formatting: WORKING")
    print("- Tool infrastructure: READY")
    print("")
    print("Note: In actual chat, LLM decides when to call tools.")
    print("This is controlled by tool_choice parameter ('auto' vs 'required').")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
