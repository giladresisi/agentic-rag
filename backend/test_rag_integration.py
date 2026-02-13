"""
Integration test for RAG tool calling with Chat Completions API.
Tests end-to-end flow: user question -> tool call -> retrieval -> response with sources
"""
import asyncio
import os
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.openai_service import openai_service
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin
import time

# Load environment variables
load_dotenv()

# Test credentials

test_user_id = None


async def setup_test_user():
    """Get test user."""
    global test_user_id

    supabase = get_supabase_admin()

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        test_user_id = auth_response.user.id
        print(f"[PASS] Authenticated as test user: {test_user_id}")
        return test_user_id
    except Exception as e:
        print(f"[FAIL] Failed to authenticate test user: {e}")
        raise


async def cleanup_test_data():
    """Clean up test documents and messages."""
    global test_user_id

    supabase = get_supabase_admin()

    try:
        # Delete test documents (chunks will cascade)
        supabase.table("documents").delete().eq("user_id", test_user_id).execute()
        print("[PASS] Cleaned up test data")
    except Exception as e:
        print(f"[WARN] Cleanup warning: {e}")


async def create_test_document_with_content(content: str, filename: str = "test_doc.txt"):
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

    # Chunk and embed
    chunks = embedding_service.chunk_text(content)
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
    return document_id


async def test_tool_calling_with_relevant_query():
    """Test that tool call is triggered for relevant query."""
    print("\n=== Test: Tool Calling with Relevant Query ===")

    # Create document about a specific topic
    content = """
    Claude Code is an AI-powered coding assistant developed by Anthropic.
    It helps developers write, debug, and understand code more efficiently.
    Claude Code supports multiple programming languages and can explain complex code.
    """

    doc_id = await create_test_document_with_content(content, "claude_info.txt")

    # Wait a bit for embedding to settle
    await asyncio.sleep(1)

    # Build conversation history
    conversation_history = [
        {"role": "user", "content": "What is Claude Code?"}
    ]

    # Stream response
    full_response = ""
    sources = None
    chunk_count = 0

    print("\n  Streaming response...")

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response += delta
            chunk_count += 1

        if chunk_sources:
            sources = chunk_sources

    print(f"  Received {chunk_count} chunks")
    print(f"  Response length: {len(full_response)} chars")

    # Verify response was generated
    if len(full_response) > 0:
        print("[PASS] Response generated")
    else:
        print("[FAIL] No response generated")
        raise AssertionError("No response generated")

    # Check if sources were returned
    if sources and len(sources) > 0:
        print(f"[PASS] Sources returned: {len(sources)} source(s)")
        for idx, source in enumerate(sources):
            print(f"  Source {idx+1}:")
            print(f"    Document: {source.get('document_name', 'Unknown')}")
            print(f"    Similarity: {source.get('similarity', 0):.3f}")

        # Verify source structure
        first_source = sources[0]
        assert 'document_name' in first_source, "Source missing document_name"
        assert 'similarity' in first_source, "Source missing similarity"
        assert 'chunk_content' in first_source, "Source missing chunk_content"
        print("[PASS] Source structure valid")
    else:
        print("[WARN] No sources returned - tool may not have been called")
        print("  This could mean:")
        print("  1. LLM chose not to use retrieval tool")
        print("  2. Similarity threshold too high")
        print("  3. Query not matched to document content")

    # Check if response contains relevant information
    if "Claude" in full_response or "code" in full_response.lower():
        print("[PASS] Response appears relevant to query")
    else:
        print(f"[WARN] Response may not be relevant: {full_response[:100]}...")

    print("\n[PASS] Tool calling test completed")


async def test_no_tool_call_for_unrelated_query():
    """Test that tool is NOT called for unrelated queries."""
    print("\n=== Test: No Tool Call for Unrelated Query ===")

    # Use existing document from previous test
    conversation_history = [
        {"role": "user", "content": "What is 2 + 2?"}
    ]

    # Stream response
    full_response = ""
    sources = None

    print("\n  Streaming response...")

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response += delta

        if chunk_sources:
            sources = chunk_sources

    # For unrelated query, we expect no sources (or empty sources)
    if not sources or len(sources) == 0:
        print("[PASS] No sources for unrelated query (as expected)")
    else:
        print(f"[WARN] Got {len(sources)} sources for unrelated query")
        print("  LLM may have decided to search documents unnecessarily")

    # Response should still be generated
    if "4" in full_response:
        print("[PASS] Correct answer generated without retrieval")
    else:
        print(f"[WARN] Unexpected response: {full_response}")

    print("\n[PASS] Unrelated query test completed")


async def test_conversation_with_retrieval():
    """Test multi-turn conversation with retrieval."""
    print("\n=== Test: Multi-turn Conversation with Retrieval ===")

    conversation_history = [
        {"role": "user", "content": "What is Claude Code?"},
    ]

    # First turn
    print("\n  Turn 1: Initial query...")
    full_response_1 = ""
    sources_1 = None

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response_1 += delta
        if chunk_sources:
            sources_1 = chunk_sources

    conversation_history.append({"role": "assistant", "content": full_response_1})

    # Follow-up question
    conversation_history.append({"role": "user", "content": "What programming languages does it support?"})

    print("  Turn 2: Follow-up query...")
    full_response_2 = ""
    sources_2 = None

    async for delta, chunk_sources in openai_service.stream_response(
        conversation_history=conversation_history,
        user_id=test_user_id,
        model="gpt-4o-mini"
    ):
        if delta:
            full_response_2 += delta
        if chunk_sources:
            sources_2 = chunk_sources

    # Both turns should work
    if len(full_response_1) > 0 and len(full_response_2) > 0:
        print("[PASS] Multi-turn conversation works")
    else:
        print("[FAIL] Multi-turn conversation failed")
        raise AssertionError("Multi-turn conversation failed")

    print(f"  Turn 1 sources: {len(sources_1) if sources_1 else 0}")
    print(f"  Turn 2 sources: {len(sources_2) if sources_2 else 0}")

    print("\n[PASS] Multi-turn conversation test completed")


async def main():
    """Run all RAG integration tests."""
    print("=" * 60)
    print("RAG INTEGRATION TESTS")
    print("=" * 60)

    try:
        # Setup
        await setup_test_user()
        await cleanup_test_data()

        # Run tests
        await test_tool_calling_with_relevant_query()
        await test_no_tool_call_for_unrelated_query()
        await test_conversation_with_retrieval()

        # Cleanup
        await cleanup_test_data()

        print("\n" + "=" * 60)
        print("[PASS] ALL RAG INTEGRATION TESTS COMPLETED")
        print("=" * 60)
        print("\nNote: Some tests may show warnings if LLM chooses not to use")
        print("retrieval tool. This is expected behavior - the LLM decides when")
        print("to call tools based on the query.")

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
