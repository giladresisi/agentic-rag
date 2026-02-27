"""
Test suite for Module 3: Record Manager (Content Hashing & Deduplication)

Tests cover:
- Hash generation consistency and format
- Duplicate detection for same files
- Modified content re-processing
- Duplicate chunk prevention
- Database schema validation
"""

from fastapi.testclient import TestClient
from main import app
from test_utils import TEST_EMAIL, TEST_PASSWORD, cleanup_test_documents_and_storage
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service
from io import BytesIO
import time
import jwt

client = TestClient(app)


def get_auth_token():
    """Get authentication token for test user."""
    response = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


def get_user_id_from_token(token):
    """Extract user_id from auth token by decoding JWT."""
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded.get("sub")


def test_hash_generation_consistency():
    """Test that hash generation is deterministic and produces correct format."""
    print("\n[TEST] Hash Generation Consistency")

    # Test text hash consistency
    text1 = "This is test content for hashing"
    hash1 = embedding_service.compute_text_hash(text1)
    hash2 = embedding_service.compute_text_hash(text1)

    assert hash1 == hash2, "Same text should produce same hash"
    assert len(hash1) == 64, f"SHA-256 hash should be 64 characters, got {len(hash1)}"
    assert hash1.islower(), "Hash should be lowercase"
    assert all(c in '0123456789abcdef' for c in hash1), "Hash should be valid hex"

    # Test different text produces different hash
    text2 = "Different content"
    hash3 = embedding_service.compute_text_hash(text2)
    assert hash1 != hash3, "Different text should produce different hashes"

    print(f"  + Text hash 1: {hash1[:16]}...")
    print(f"  + Text hash 2: {hash2[:16]}... (matches hash 1)")
    print(f"  + Text hash 3: {hash3[:16]}... (different from hash 1)")
    print(f"  + Hash format: 64-char lowercase hex")
    print("[PASS] Hash generation is consistent and correct")


def test_duplicate_same_file():
    """Test that uploading the same file twice results in duplicate detection."""
    print("\n[TEST] Duplicate Detection - Same File")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)
    supabase = get_supabase_admin()

    # Create test file content
    content = b"This is a test document for duplicate detection.\n\nIt has multiple lines."

    # Upload first time
    files1 = {"file": ("test_duplicate.md", BytesIO(content), "text/markdown")}
    response1 = client.post("/ingestion/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    assert response1.status_code == 200, f"First upload failed: {response1.text}"
    doc1_id = response1.json()["id"]
    print(f"  + First upload successful: {doc1_id}")

    # Wait for processing
    time.sleep(3)

    # Verify first document completed
    doc1 = supabase.table("documents").select("*").eq("id", doc1_id).execute()
    assert doc1.data, "First document not found"
    assert doc1.data[0]["status"] == "completed", f"First document status: {doc1.data[0]['status']}"
    print(f"  + First document processed: status={doc1.data[0]['status']}, chunks={doc1.data[0]['chunk_count']}")

    # Upload same content with different filename
    files2 = {"file": ("test_duplicate_copy.md", BytesIO(content), "text/markdown")}
    response2 = client.post("/ingestion/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    assert response2.status_code == 200, f"Second upload failed: {response2.text}"
    doc2_id = response2.json()["id"]
    print(f"  + Second upload successful: {doc2_id}")

    # Wait for processing
    time.sleep(3)

    # Verify second document marked as duplicate
    doc2 = supabase.table("documents").select("*").eq("id", doc2_id).execute()
    assert doc2.data, "Second document not found"
    assert doc2.data[0]["status"] == "duplicate", f"Second document status should be 'duplicate', got: {doc2.data[0]['status']}"
    assert doc2.data[0]["duplicate_of"] == doc1_id, f"Second document should reference first: {doc2.data[0]['duplicate_of']} != {doc1_id}"
    assert doc2.data[0]["text_content_hash"] is not None, "Second document should have text_content_hash"
    print(f"  + Second document marked as duplicate: duplicate_of={doc2.data[0]['duplicate_of']}")

    # Verify hashes match
    assert doc1.data[0]["text_content_hash"] == doc2.data[0]["text_content_hash"], "Text hashes should match"
    print(f"  + Text hashes match: {doc1.data[0]['text_content_hash'][:16]}...")

    # Cleanup — only the documents this test created
    cleanup_test_documents_and_storage(user_id, doc_ids=[doc1_id, doc2_id])
    print("[PASS] Duplicate detection works for same file")


def test_modified_content_reprocesses():
    """Test that uploading modified content creates a new document, not a duplicate."""
    print("\n[TEST] Modified Content Re-processing")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)
    supabase = get_supabase_admin()

    # Upload first version
    content_v1 = b"Version 1 of the document content."
    files1 = {"file": ("test_modified.md", BytesIO(content_v1), "text/markdown")}
    response1 = client.post("/ingestion/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    assert response1.status_code == 200, f"First upload failed: {response1.text}"
    doc1_id = response1.json()["id"]
    print(f"  + Version 1 uploaded: {doc1_id}")

    # Wait for processing
    time.sleep(3)

    # Verify first document
    doc1 = supabase.table("documents").select("*").eq("id", doc1_id).execute()
    assert doc1.data[0]["status"] == "completed", "First document should be completed"
    hash1 = doc1.data[0]["text_content_hash"]
    print(f"  + Version 1 processed: hash={hash1[:16]}...")

    # Upload modified version with different filename
    content_v2 = b"Version 2 of the document content with significant changes."
    files2 = {"file": ("test_modified_v2.md", BytesIO(content_v2), "text/markdown")}
    response2 = client.post("/ingestion/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    assert response2.status_code == 200, f"Second upload failed: {response2.text}"
    doc2_id = response2.json()["id"]
    print(f"  + Version 2 uploaded: {doc2_id}")

    # Wait for processing
    time.sleep(3)

    # Verify second document is also completed (not duplicate)
    doc2 = supabase.table("documents").select("*").eq("id", doc2_id).execute()
    assert doc2.data[0]["status"] == "completed", f"Second document should be completed, got: {doc2.data[0]['status']}"
    hash2 = doc2.data[0]["text_content_hash"]
    print(f"  + Version 2 processed: hash={hash2[:16]}...")

    # Verify hashes are different
    assert hash1 != hash2, "Modified content should have different hash"
    print(f"  + Hashes differ (content changed)")

    # Verify both have chunks
    assert doc1.data[0]["chunk_count"] > 0, "Version 1 should have chunks"
    assert doc2.data[0]["chunk_count"] > 0, "Version 2 should have chunks"
    print(f"  + Both versions have chunks: v1={doc1.data[0]['chunk_count']}, v2={doc2.data[0]['chunk_count']}")

    # Cleanup — only the documents this test created
    cleanup_test_documents_and_storage(user_id, doc_ids=[doc1_id, doc2_id])
    print("[PASS] Modified content re-processes correctly")


def test_duplicate_no_chunks_created():
    """Test that duplicate documents don't create new chunks."""
    print("\n[TEST] Duplicate Documents - No Chunks Created")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)
    supabase = get_supabase_admin()

    # Upload original
    content = b"Content for chunk testing. This should create chunks only once."
    files1 = {"file": ("chunks_test.md", BytesIO(content), "text/markdown")}
    response1 = client.post("/ingestion/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    doc1_id = response1.json()["id"]
    time.sleep(3)

    # Count chunks for original
    chunks1 = supabase.table("chunks").select("id").eq("document_id", doc1_id).execute()
    original_chunk_count = len(chunks1.data)
    assert original_chunk_count > 0, "Original document should have chunks"
    print(f"  + Original document created {original_chunk_count} chunks")

    # Upload duplicate
    files2 = {"file": ("chunks_test_dup.md", BytesIO(content), "text/markdown")}
    response2 = client.post("/ingestion/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    doc2_id = response2.json()["id"]
    time.sleep(3)

    # Verify duplicate status
    doc2 = supabase.table("documents").select("*").eq("id", doc2_id).execute()
    assert doc2.data[0]["status"] == "duplicate", "Second upload should be duplicate"
    print(f"  + Duplicate document detected: {doc2_id}")

    # Verify NO chunks created for duplicate
    chunks2 = supabase.table("chunks").select("id").eq("document_id", doc2_id).execute()
    assert len(chunks2.data) == 0, f"Duplicate should have 0 chunks, found {len(chunks2.data)}"
    print(f"  + Duplicate created 0 chunks (as expected)")

    # Cleanup — only the documents this test created
    cleanup_test_documents_and_storage(user_id, doc_ids=[doc1_id, doc2_id])
    print("[PASS] Duplicate documents don't create chunks")


def test_duplicate_different_filename_same_content():
    """Test that same content with different filename is detected as duplicate."""
    print("\n[TEST] Duplicate Detection - Different Filenames")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)
    supabase = get_supabase_admin()

    # Upload with first filename
    content = b"Shared content across different filenames"
    files1 = {"file": ("filename_a.md", BytesIO(content), "text/markdown")}
    response1 = client.post("/ingestion/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    doc1_id = response1.json()["id"]
    time.sleep(3)

    # Verify first completed
    doc1 = supabase.table("documents").select("*").eq("id", doc1_id).execute()
    assert doc1.data[0]["status"] == "completed"
    print(f"  + First file (filename_a.md) processed")

    # Upload same content with different filename
    files2 = {"file": ("filename_b.md", BytesIO(content), "text/markdown")}
    response2 = client.post("/ingestion/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    doc2_id = response2.json()["id"]
    time.sleep(3)

    # Verify second marked as duplicate
    doc2 = supabase.table("documents").select("*").eq("id", doc2_id).execute()
    assert doc2.data[0]["status"] == "duplicate", "Different filename with same content should be duplicate"
    assert doc2.data[0]["duplicate_of"] == doc1_id
    print(f"  + Second file (filename_b.md) marked as duplicate")
    print(f"  + Duplicate detection works across filenames")

    # Cleanup — only the documents this test created
    cleanup_test_documents_and_storage(user_id, doc_ids=[doc1_id, doc2_id])
    print("[PASS] Duplicate detection works regardless of filename")


def test_database_constraints():
    """Test that database migration was applied correctly."""
    print("\n[TEST] Database Schema Validation")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)
    supabase = get_supabase_admin()

    # Create two documents to test duplicate_of foreign key
    content1 = b"Original document content"
    files1 = {"file": ("schema_test_1.md", BytesIO(content1), "text/markdown")}
    response1 = client.post("/ingestion/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    doc1_id = response1.json()["id"]
    time.sleep(2)

    content2 = b"Duplicate document content"
    files2 = {"file": ("schema_test_2.md", BytesIO(content2), "text/markdown")}
    response2 = client.post("/ingestion/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    doc2_id = response2.json()["id"]
    time.sleep(1)

    # Test that duplicate status is valid and duplicate_of FK works
    try:
        supabase.table("documents").update({
            "status": "duplicate",
            "duplicate_of": doc1_id,
            "text_content_hash": "test_hash_value"
        }).eq("id", doc2_id).execute()
        print("  + 'duplicate' status is valid (constraint allows it)")
        print("  + duplicate_of foreign key works")
    except Exception as e:
        raise AssertionError(f"Failed to set duplicate status/FK: {e}")

    # Verify the update worked
    doc2 = supabase.table("documents").select("*").eq("id", doc2_id).execute()
    assert doc2.data[0]["status"] == "duplicate", "Status should be duplicate"
    assert doc2.data[0]["duplicate_of"] == doc1_id, "duplicate_of should reference doc1"
    assert doc2.data[0]["text_content_hash"] == "test_hash_value", "text_content_hash should be set"
    print("  + All new columns are writable and readable")

    # Cleanup — only the documents this test created
    cleanup_test_documents_and_storage(user_id, doc_ids=[doc1_id, doc2_id])
    print("[PASS] Database schema supports duplicate tracking")


def run_all_tests():
    """Run all test functions."""
    print("\n" + "="*70)
    print("MODULE 3: RECORD MANAGER TEST SUITE")
    print("="*70)

    tests = [
        test_hash_generation_consistency,
        test_duplicate_same_file,
        test_modified_content_reprocesses,
        test_duplicate_no_chunks_created,
        test_duplicate_different_filename_same_content,
        test_database_constraints,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_func.__name__}: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*70)

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    run_all_tests()
