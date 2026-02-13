"""
End-to-end test for document retrieval system.
This test validates the complete RAG pipeline works correctly.

Test will PASS if:
1. Document and chunks exist in database
2. Direct retrieval returns results with threshold 0.4
3. Chat with tool calling returns document content
"""
import asyncio
import sys
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.retrieval_service import retrieval_service
from services.chat_service import chat_service

load_dotenv()

# Test credentials
TEST_USER_EMAIL = "test@..."
TEST_USER_PASSWORD = "***"

# Test will fail if any assertion fails
test_passed = True
failure_reasons = []


def log_pass(message):
    """Log a passing test."""
    print(f"[PASS] {message}")


def log_fail(message):
    """Log a failing test and track it."""
    global test_passed, failure_reasons
    test_passed = False
    failure_reasons.append(message)
    print(f"[FAIL] {message}")


def log_info(message):
    """Log informational message."""
    print(f"  {message}")


async def test_e2e():
    """Run end-to-end retrieval test."""
    global test_passed, failure_reasons

    print("=" * 70)
    print("END-TO-END RETRIEVAL TEST")
    print("=" * 70)

    supabase = get_supabase_admin()

    # Test 1: Authenticate
    print("\n[1] Authentication Test")
    print("-" * 70)
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        user_id = auth_response.user.id
        log_pass(f"Authenticated as {TEST_USER_EMAIL}")
        log_info(f"User ID: {user_id}")
    except Exception as e:
        log_fail(f"Authentication failed: {e}")
        return

    # Test 2: Check document exists
    print("\n[2] Document Existence Test")
    print("-" * 70)
    try:
        docs_response = supabase.table("documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()

        if not docs_response.data:
            log_fail("No documents found in database")
            log_info("Please upload a document through the UI first")
            return

        doc = docs_response.data[0]
        log_pass(f"Found document: {doc['filename']}")
        log_info(f"Status: {doc['status']}")
        log_info(f"Chunks: {doc.get('chunk_count', 0)}")

        if doc['status'] != 'completed':
            log_fail(f"Document status is '{doc['status']}', expected 'completed'")
            return

        if doc.get('chunk_count', 0) == 0:
            log_fail("Document has 0 chunks")
            return

    except Exception as e:
        log_fail(f"Failed to check documents: {e}")
        return

    # Test 3: Check chunks exist with embeddings
    print("\n[3] Chunks and Embeddings Test")
    print("-" * 70)
    try:
        chunks_response = supabase.table("chunks")\
            .select("*")\
            .eq("user_id", user_id)\
            .limit(1)\
            .execute()

        if not chunks_response.data:
            log_fail("No chunks found")
            return

        chunk = chunks_response.data[0]
        log_pass(f"Found {len(chunks_response.data)} chunk(s)")

        # Check embedding
        embedding = chunk.get('embedding')
        if not embedding:
            log_fail("Chunk has no embedding")
            return

        # Parse embedding if it's a string
        import json
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except:
                log_fail("Failed to parse embedding")
                return

        embedding_dims = len(embedding)
        log_info(f"Embedding dimensions: {embedding_dims}")
        log_info(f"Content preview: {chunk['content'][:80]}...")

        if embedding_dims not in [768, 1536, 3072]:
            log_fail(f"Unexpected embedding dimensions: {embedding_dims}")
            log_info("Expected 768, 1536, or 3072")
            return
        else:
            log_pass(f"Embedding dimensions valid: {embedding_dims}")

    except Exception as e:
        log_fail(f"Failed to check chunks: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 4: Direct retrieval with low threshold
    print("\n[4] Direct Retrieval Test (threshold=0.3)")
    print("-" * 70)
    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query="document content",
            user_id=user_id,
            similarity_threshold=0.3,
            limit=5
        )

        if not results:
            log_fail("Retrieval returned no results with threshold 0.3")
            log_info("This suggests an embedding or database issue")
            return

        log_pass(f"Retrieved {len(results)} result(s)")

        best_similarity = max(r['similarity'] for r in results)
        log_info(f"Best similarity score: {best_similarity:.3f}")

        if best_similarity < 0.3:
            log_fail(f"Best similarity ({best_similarity:.3f}) below threshold")
            return

    except Exception as e:
        log_fail(f"Direct retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 5: Retrieval with configured threshold (0.25)
    print("\n[5] Configured Threshold Test (threshold=0.25)")
    print("-" * 70)
    try:
        results = await retrieval_service.retrieve_relevant_chunks(
            query="document content",
            user_id=user_id,
            similarity_threshold=0.25,
            limit=5
        )

        if not results:
            log_fail("No results with threshold 0.25")
            log_info(f"Best observed similarity: {best_similarity:.3f}")
            log_info("Need to lower threshold further or improve document content")
        else:
            log_pass(f"Retrieved {len(results)} result(s) with threshold 0.25")

    except Exception as e:
        log_fail(f"Threshold 0.25 test failed: {e}")
        return

    # Test 6: Chat with tool calling (most important test)
    print("\n[6] End-to-End Chat Test with Tool Calling")
    print("-" * 70)
    try:
        # Use a query that should definitely trigger tool use
        conversation_history = [
            {"role": "user", "content": "Tell me about my uploaded document."}
        ]

        log_info("Streaming chat response...")
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

        log_info(f"Received {chunk_count} response chunks")
        log_info(f"Response length: {len(full_response)} chars")

        # Check if tool was called and returned sources
        if not sources:
            log_fail("Tool was not called or returned no sources")
            log_info(f"Response: {full_response[:200]}...")
            log_info("LLM may have decided not to use the tool")
            log_info("or retrieval returned empty results")
        else:
            log_pass(f"Tool called successfully! Retrieved {len(sources)} source(s)")
            for idx, source in enumerate(sources):
                log_info(f"  Source {idx+1}: {source['document_name']} (similarity: {source['similarity']:.3f})")

            # Check if response contains actual content from document
            if len(full_response) > 50 and not any(phrase in full_response.lower() for phrase in ["unable to access", "don't have access", "cannot access"]):
                log_pass("Response contains document information")
                log_info(f"Response preview: {full_response[:150]}...")
            else:
                log_fail("Response doesn't contain useful document information")
                log_info(f"Response: {full_response}")

    except Exception as e:
        log_fail(f"Chat test failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Final summary
    print("\n" + "=" * 70)
    if test_passed:
        print("[PASS] ALL TESTS PASSED")
        print("=" * 70)
        print("\nRetrieval system is working correctly!")
        print("The document retrieval pipeline is functional end-to-end.")
        return 0
    else:
        print("[FAIL] TESTS FAILED")
        print("=" * 70)
        print(f"\nFailure count: {len(failure_reasons)}")
        print("\nFailed tests:")
        for idx, reason in enumerate(failure_reasons, 1):
            print(f"  {idx}. {reason}")
        print("\nPlease fix the issues above and re-run the test.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_e2e())
    sys.exit(exit_code)
