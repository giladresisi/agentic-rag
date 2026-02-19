"""
Test RAG retrieval functionality including:
- Retrieval service
- Tool calling integration
- Source metadata
- RLS enforcement
"""
import asyncio
import os
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.retrieval_service import retrieval_service
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin
import uuid

# Load environment variables
load_dotenv()

# Test credentials

# Test user ID (will be fetched from auth)
test_user_id = None


async def setup_test_user():
    """Get or create test user and return user_id."""
    global test_user_id

    supabase = get_supabase_admin()

    # Try to sign in
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        test_user_id = auth_response.user.id
        print(f"[PASS] Authenticated as test user: {test_user_id}")
        return test_user_id
    except Exception as e:
        print(f"[FAIL] Failed to authenticate test user: {e}")
        raise


async def cleanup_test_documents():
    """Clean up test documents from previous runs."""
    global test_user_id

    supabase = get_supabase_admin()

    try:
        # Delete test documents
        supabase.table("documents").delete().eq("user_id", test_user_id).execute()
        print("[PASS] Cleaned up test documents")
    except Exception as e:
        print(f"[WARN] Cleanup warning: {e}")


async def create_test_document(content: str, filename: str = "test_doc.txt"):
    """Create a test document with chunks and embeddings."""
    global test_user_id

    supabase = get_supabase_admin()

    # Create document record
    doc_response = supabase.table("documents").insert({
        "user_id": test_user_id,
        "filename": filename,
        "content_type": "text/plain",
        "file_size_bytes": len(content),
        "storage_path": f"{test_user_id}/{filename}",
        "status": "processing",
        "chunk_count": 0
    }).execute()

    document_id = doc_response.data[0]["id"]

    # Chunk the content
    chunks = embedding_service.chunk_text(content)

    # Generate embeddings
    embeddings = await embedding_service.generate_embeddings(chunks)

    # Save chunks
    chunk_records = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_records.append({
            "document_id": document_id,
            "user_id": test_user_id,
            "content": chunk_text,
            "embedding": embedding,
            "chunk_index": idx
        })

    supabase.table("chunks").insert(chunk_records).execute()

    # Update document status
    supabase.table("documents").update({
        "status": "completed",
        "chunk_count": len(chunks)
    }).eq("id", document_id).execute()

    print(f"[PASS] Created test document: {filename} ({len(chunks)} chunks)")
    return document_id, chunks


async def test_retrieval_service():
    """Test retrieval service returns relevant chunks."""
    print("\n=== Test: Retrieval Service ===")

    # Create test document about Python
    python_content = """
    Python is a high-level programming language known for its simplicity and readability.
    Python decorators are a powerful feature that allows you to modify or enhance functions.
    A decorator is a function that takes another function and extends its behavior without explicitly modifying it.
    Python was created by Guido van Rossum and first released in 1991.
    """

    doc_id, chunks = await create_test_document(python_content, "python_guide.txt")

    # Test 1: Relevant query should return chunks
    print("\nTest 1: Relevant query")
    results = await retrieval_service.retrieve_relevant_chunks(
        query="What are Python decorators?",
        user_id=test_user_id,
        limit=3,
        similarity_threshold=0.5
    )

    if results and len(results) > 0:
        print(f"[PASS] Retrieved {len(results)} chunks")
        for i, result in enumerate(results):
            print(f"  Chunk {i+1}: similarity={result.get('similarity', 0):.3f}")

            # Verify result has required fields
            assert 'content' in result, "Result missing 'content' field"
            assert 'similarity' in result, "Result missing 'similarity' field"
            assert result['similarity'] >= 0.5, f"Similarity {result['similarity']} below threshold"
    else:
        print("[FAIL] No results returned for relevant query")
        raise AssertionError("Expected results for relevant query")

    # Test 2: Unrelated query should return no/few chunks
    print("\nTest 2: Unrelated query")
    unrelated_results = await retrieval_service.retrieve_relevant_chunks(
        query="What is the capital of France?",
        user_id=test_user_id,
        limit=3,
        similarity_threshold=0.7
    )

    if unrelated_results:
        print(f"[WARN] Retrieved {len(unrelated_results)} chunks for unrelated query (expected 0 or low similarity)")
        for result in unrelated_results:
            print(f"  Similarity: {result.get('similarity', 0):.3f}")
    else:
        print("[PASS] No chunks retrieved for unrelated query (as expected)")

    print("\n[PASS] Retrieval service tests passed")


async def test_multiple_documents():
    """Test retrieval across multiple documents."""
    print("\n=== Test: Multiple Documents ===")

    # Create two documents
    doc1_content = "Python is excellent for data science and machine learning applications."
    doc2_content = "JavaScript is the language of the web, used for frontend and backend development."

    doc1_id, _ = await create_test_document(doc1_content, "python_info.txt")
    doc2_id, _ = await create_test_document(doc2_content, "javascript_info.txt")

    # Query that should match Python document
    results = await retrieval_service.retrieve_relevant_chunks(
        query="Tell me about Python for data science",
        user_id=test_user_id,
        limit=5,
        similarity_threshold=0.5
    )

    if results and len(results) > 0:
        print(f"[PASS] Retrieved {len(results)} chunks from multiple documents")

        # Check if results come from both documents (possible if both match)
        doc_ids = set(result['document_id'] for result in results)
        print(f"  Chunks from {len(doc_ids)} document(s)")
    else:
        print("[FAIL] No results from multiple documents")
        raise AssertionError("Expected results from documents")

    print("[PASS] Multiple documents test passed")


async def test_rls_enforcement():
    """Test that RLS prevents cross-user retrieval."""
    print("\n=== Test: RLS Enforcement ===")

    # Create a document for test user
    content = "This is a private document that should only be visible to the test user."
    doc_id, _ = await create_test_document(content, "private_doc.txt")

    # Try to retrieve with a different user_id (simulated)
    fake_user_id = str(uuid.uuid4())

    results = await retrieval_service.retrieve_relevant_chunks(
        query="private document",
        user_id=fake_user_id,  # Different user
        limit=5,
        similarity_threshold=0.3
    )

    if results and len(results) > 0:
        print(f"[FAIL] SECURITY ISSUE: Retrieved {len(results)} chunks with different user_id")
        raise AssertionError("RLS not enforced - cross-user retrieval succeeded")
    else:
        print("[PASS] RLS enforced - no cross-user retrieval")

    # Verify correct user can retrieve
    correct_results = await retrieval_service.retrieve_relevant_chunks(
        query="private document",
        user_id=test_user_id,  # Correct user
        limit=5,
        similarity_threshold=0.3
    )

    if correct_results and len(correct_results) > 0:
        print(f"[PASS] Correct user can retrieve their documents ({len(correct_results)} chunks)")
    else:
        print("[FAIL] Correct user cannot retrieve their own documents")
        raise AssertionError("User cannot retrieve own documents")

    print("[PASS] RLS enforcement test passed")


async def test_similarity_threshold():
    """Test that similarity threshold filtering works."""
    print("\n=== Test: Similarity Threshold ===")

    # Create document
    content = "Artificial intelligence and machine learning are transforming technology."
    doc_id, _ = await create_test_document(content, "ai_doc.txt")

    # Test with high threshold
    high_threshold_results = await retrieval_service.retrieve_relevant_chunks(
        query="artificial intelligence",
        user_id=test_user_id,
        limit=5,
        similarity_threshold=0.8
    )

    # Test with low threshold
    low_threshold_results = await retrieval_service.retrieve_relevant_chunks(
        query="artificial intelligence",
        user_id=test_user_id,
        limit=5,
        similarity_threshold=0.3
    )

    print(f"  High threshold (0.8): {len(high_threshold_results)} chunks")
    print(f"  Low threshold (0.3): {len(low_threshold_results)} chunks")

    # Low threshold should return same or more results
    if len(low_threshold_results) >= len(high_threshold_results):
        print("[PASS] Threshold filtering works correctly")
    else:
        print("[FAIL] Threshold filtering issue")
        raise AssertionError("Low threshold returned fewer results than high threshold")

    # Verify all results meet threshold
    for result in high_threshold_results:
        if result['similarity'] < 0.8:
            print(f"[FAIL] Result with similarity {result['similarity']} below threshold 0.8")
            raise AssertionError("Result below threshold returned")

    print("[PASS] Similarity threshold test passed")


async def main():
    """Run all RAG retrieval tests."""
    print("=" * 60)
    print("RAG RETRIEVAL TESTS")
    print("=" * 60)

    try:
        # Setup
        await setup_test_user()
        await cleanup_test_documents()

        # Run tests
        await test_retrieval_service()
        await test_multiple_documents()
        await test_rls_enforcement()
        await test_similarity_threshold()

        # Cleanup
        await cleanup_test_documents()

        print("\n" + "=" * 60)
        print("[PASS] ALL RAG RETRIEVAL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())
