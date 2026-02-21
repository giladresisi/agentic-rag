"""
Test hybrid search and reranking functionality including:
- Keyword search RPC
- Hybrid search RPC with RRF
- Local reranking (cross-encoder)
- Cohere reranking API
- E2E hybrid retrieval with reranking
- Vector-only fallback
- Edge cases
"""
import asyncio
import os
from dotenv import load_dotenv
from test_utils import TEST_EMAIL, TEST_PASSWORD
from services.retrieval_service import retrieval_service
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin
from services import reranking_service
from models.reranking import RerankDocument, RerankRequest
from config import settings

# Load environment variables
load_dotenv()

# Test user ID (will be fetched from auth)
test_user_id = None


async def setup_test_user():
    """Get test user and return user_id."""
    global test_user_id

    supabase = get_supabase_admin()

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        test_user_id = auth_response.user.id
        print(f"[+] Authenticated as test user: {test_user_id}")
        return test_user_id
    except Exception as e:
        print(f"[-] Failed to authenticate test user: {e}")
        raise


async def create_test_document(content: str, filename: str = "hybrid_test.txt"):
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
        "chunk_count": 0,
        "embedding_dimensions": 1536
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
            "chunk_index": idx,
            "embedding_dimensions": len(embedding)
        })

    supabase.table("chunks").insert(chunk_records).execute()

    # Update document status
    supabase.table("documents").update({
        "status": "completed",
        "chunk_count": len(chunks)
    }).eq("id", document_id).execute()

    print(f"[+] Created test document: {document_id} with {len(chunks)} chunks")
    return document_id


async def cleanup_test_documents():
    """Clean up test documents from previous runs."""
    global test_user_id

    supabase = get_supabase_admin()

    try:
        supabase.table("documents").delete().eq("user_id", test_user_id).execute()
        print("[+] Cleaned up test documents")
    except Exception as e:
        print(f"[!] Cleanup warning: {e}")


async def test_keyword_search_rpc():
    """Test keyword_search_chunks RPC function."""
    print("\n=== Test: Keyword Search RPC ===")

    supabase = get_supabase_admin()

    try:
        # Test keyword search
        response = supabase.rpc(
            'keyword_search_chunks',
            {
                'query_text': 'Paris Agreement',
                'user_id_filter': test_user_id,
                'match_count': 5
            }
        ).execute()

        results = response.data if response.data else []
        print(f"[+] Keyword search returned {len(results)} results")

        if results:
            print(f"[+] Top result rank: {results[0]['rank']:.4f}")
            print(f"[+] Top result preview: {results[0]['content'][:100]}...")

        print("[PASS] Keyword search RPC works")
        return True

    except Exception as e:
        print(f"[-] Keyword search RPC failed: {e}")
        return False


async def test_hybrid_search_rpc():
    """Test hybrid_search_chunks RPC function with RRF."""
    print("\n=== Test: Hybrid Search RPC with RRF ===")

    supabase = get_supabase_admin()

    try:
        # Generate query embedding
        query = "What is the Paris Agreement?"
        embeddings = await embedding_service.generate_embeddings([query])
        query_embedding = embeddings[0]

        # Test hybrid search
        response = supabase.rpc(
            'hybrid_search_chunks',
            {
                'query_text': 'Paris Agreement',
                'query_embedding': query_embedding,
                'user_id_filter': test_user_id,
                'match_count': 5,
                'vector_weight': 0.5,
                'keyword_weight': 0.5,
                'dimension_filter': len(query_embedding),
                'similarity_threshold': 0.0
            }
        ).execute()

        results = response.data if response.data else []
        print(f"[+] Hybrid search returned {len(results)} results")

        if results:
            result = results[0]
            print(f"[+] Top result scores:")
            print(f"    - Similarity: {result.get('similarity', 0):.4f}")
            print(f"    - Keyword rank: {result.get('keyword_rank', 0):.4f}")
            print(f"    - Hybrid score: {result.get('hybrid_score', 0):.4f}")
            print(f"[+] Preview: {result['content'][:100]}...")

        print("[PASS] Hybrid search RPC works")
        return True

    except Exception as e:
        print(f"[-] Hybrid search RPC failed: {e}")
        return False


async def test_local_reranking():
    """Test local cross-encoder reranking."""
    print("\n=== Test: Local Reranking ===")

    try:
        # Prepare test documents
        documents = [
            RerankDocument(id="1", text="The Paris Agreement is a climate treaty."),
            RerankDocument(id="2", text="Paris is the capital of France."),
            RerankDocument(id="3", text="The 2015 Paris climate accord was historic."),
            RerankDocument(id="4", text="I love visiting Paris in the spring."),
        ]

        # Create rerank request
        request = RerankRequest(
            query="What is the Paris Agreement?",
            documents=documents,
            top_n=3
        )

        # Test local reranking
        response = reranking_service.rerank(request, provider="local")

        print(f"[+] Local reranking returned {len(response.results)} results")
        print(f"[+] Model used: {response.model}")
        print(f"[+] Provider: {response.provider}")

        # Display results
        for i, result in enumerate(response.results):
            doc = documents[result.index]
            print(f"[+] Rank {i+1}: Score {result.relevance_score:.4f} - {doc.text[:60]}...")

        print("[PASS] Local reranking works")
        return True

    except Exception as e:
        print(f"[-] Local reranking failed: {e}")
        return False


async def test_cohere_reranking():
    """Test Cohere Rerank API (if configured)."""
    print("\n=== Test: Cohere Reranking ===")

    if not settings.COHERE_API_KEY:
        print("[SKIP] Cohere not configured (optional)")
        return True

    try:
        # Prepare test documents
        documents = [
            RerankDocument(id="1", text="The Paris Agreement is a climate treaty."),
            RerankDocument(id="2", text="Paris is the capital of France."),
            RerankDocument(id="3", text="The 2015 Paris climate accord was historic."),
            RerankDocument(id="4", text="I love visiting Paris in the spring."),
        ]

        # Create rerank request
        request = RerankRequest(
            query="What is the Paris Agreement?",
            documents=documents,
            top_n=3
        )

        # Test Cohere reranking
        response = reranking_service.rerank(request, provider="cohere")

        print(f"[+] Cohere reranking returned {len(response.results)} results")
        print(f"[+] Model used: {response.model}")
        print(f"[+] Provider: {response.provider}")

        # Display results
        for i, result in enumerate(response.results):
            doc = documents[result.index]
            print(f"[+] Rank {i+1}: Score {result.relevance_score:.4f} - {doc.text[:60]}...")

        print("[PASS] Cohere reranking works")
        return True

    except Exception as e:
        print(f"[-] Cohere reranking failed: {e}")
        return False


async def test_hybrid_retrieval_with_reranking():
    """Test E2E hybrid retrieval pipeline with reranking."""
    print("\n=== Test: E2E Hybrid Retrieval with Reranking ===")

    try:
        # Test retrieval with hybrid search and reranking
        query = "What is the Paris Agreement about?"

        # Save original settings
        original_hybrid = settings.HYBRID_SEARCH_ENABLED
        original_rerank = settings.RERANKING_ENABLED

        # Enable hybrid search and reranking
        settings.HYBRID_SEARCH_ENABLED = True
        settings.RERANKING_ENABLED = True

        chunks = await retrieval_service.retrieve_relevant_chunks(
            query=query,
            user_id=test_user_id,
            limit=3,
            enable_reranking=True
        )

        # Restore settings
        settings.HYBRID_SEARCH_ENABLED = original_hybrid
        settings.RERANKING_ENABLED = original_rerank

        print(f"[+] Retrieved {len(chunks)} chunks")

        if chunks:
            chunk = chunks[0]
            print(f"[+] Top chunk scores:")
            print(f"    - Similarity: {chunk.get('similarity', 0):.4f}")
            print(f"    - Keyword rank: {chunk.get('keyword_rank', 0):.4f}")
            print(f"    - Hybrid score: {chunk.get('hybrid_score', 0):.4f}")
            print(f"    - Rerank score: {chunk.get('rerank_score', 0):.4f}")
            print(f"[+] Preview: {chunk['content'][:100]}...")

        print("[PASS] E2E hybrid retrieval with reranking works")
        return True

    except Exception as e:
        print(f"[-] E2E hybrid retrieval failed: {e}")
        return False


async def test_vector_only_fallback():
    """Test vector-only fallback (backward compatibility)."""
    print("\n=== Test: Vector-Only Fallback ===")

    try:
        # Save original setting
        original_hybrid = settings.HYBRID_SEARCH_ENABLED

        # Disable hybrid search
        settings.HYBRID_SEARCH_ENABLED = False

        chunks = await retrieval_service.retrieve_relevant_chunks(
            query="Paris Agreement",
            user_id=test_user_id,
            limit=3,
            enable_reranking=False
        )

        # Restore setting
        settings.HYBRID_SEARCH_ENABLED = original_hybrid

        print(f"[+] Vector-only retrieval returned {len(chunks)} chunks")

        if chunks:
            chunk = chunks[0]
            # Should only have similarity, not keyword_rank or hybrid_score
            has_similarity = 'similarity' in chunk
            has_keyword = 'keyword_rank' in chunk
            has_hybrid = 'hybrid_score' in chunk

            print(f"[+] Has similarity: {has_similarity}")
            print(f"[+] Has keyword_rank: {has_keyword}")
            print(f"[+] Has hybrid_score: {has_hybrid}")

            if has_similarity and not has_keyword and not has_hybrid:
                print("[PASS] Vector-only fallback works (backward compatible)")
                return True
            else:
                print("[-] Unexpected fields in vector-only mode")
                return False

        print("[PASS] Vector-only fallback works")
        return True

    except Exception as e:
        print(f"[-] Vector-only fallback failed: {e}")
        return False


async def test_edge_cases():
    """Test edge cases: empty query, no matches, special chars."""
    print("\n=== Test: Edge Cases ===")

    passed = 0
    total = 3

    # Test 1: Empty query
    try:
        chunks = await retrieval_service.retrieve_relevant_chunks(
            query="",
            user_id=test_user_id,
            limit=3
        )
        print(f"[+] Empty query handled: {len(chunks)} results")
        passed += 1
    except Exception as e:
        print(f"[-] Empty query failed: {e}")

    # Test 2: Query with no matches
    try:
        chunks = await retrieval_service.retrieve_relevant_chunks(
            query="ZZZNONEXISTENTQUERYZZZ",
            user_id=test_user_id,
            limit=3
        )
        print(f"[+] No matches handled: {len(chunks)} results")
        passed += 1
    except Exception as e:
        print(f"[-] No matches failed: {e}")

    # Test 3: Special characters
    try:
        chunks = await retrieval_service.retrieve_relevant_chunks(
            query="Paris & Agreement (2015) - climate!",
            user_id=test_user_id,
            limit=3
        )
        print(f"[+] Special chars handled: {len(chunks)} results")
        passed += 1
    except Exception as e:
        print(f"[-] Special chars failed: {e}")

    print(f"[+] Edge cases: {passed}/{total} passed")
    return passed == total


async def run_all_tests():
    """Run all hybrid search tests."""
    print("=" * 60)
    print("HYBRID SEARCH & RERANKING TEST SUITE")
    print("=" * 60)

    # Setup
    await setup_test_user()
    await cleanup_test_documents()

    # Create test document with relevant content
    test_content = """
    The Paris Agreement is an international treaty on climate change. It was adopted in 2015
    at the Paris Climate Conference (COP21). The agreement aims to limit global warming to
    well below 2 degrees Celsius compared to pre-industrial levels. Countries that have ratified
    the Paris Agreement commit to reducing greenhouse gas emissions and adapting to climate change
    impacts. The Paris Agreement entered into force in November 2016.
    """
    await create_test_document(test_content)

    # Run tests
    results = []
    results.append(await test_keyword_search_rpc())
    results.append(await test_hybrid_search_rpc())
    results.append(await test_local_reranking())
    results.append(await test_cohere_reranking())
    results.append(await test_hybrid_retrieval_with_reranking())
    results.append(await test_vector_only_fallback())
    results.append(await test_edge_cases())

    # Summary
    passed = sum(results)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("[PASS] All tests passed!")
        return 0
    else:
        print("[-] Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    exit(exit_code)
