"""
Integration tests for Module 4: Metadata Extraction

Tests cover:
- End-to-end metadata extraction on document upload
- Metadata extraction disabled (extract_metadata=false)
- Metadata failure does not block ingestion
"""

from fastapi.testclient import TestClient
from main import app
from test_utils import TEST_EMAIL, TEST_PASSWORD, cleanup_test_documents_and_storage
from services.supabase_service import get_supabase_admin
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


def get_document_from_db(document_id, user_id):
    """Query document directly from database to get all fields including metadata."""
    supabase = get_supabase_admin()
    response = supabase.table("documents")\
        .select("*")\
        .eq("id", document_id)\
        .eq("user_id", user_id)\
        .single()\
        .execute()
    return response.data


# Substantial test content for reliable metadata extraction
TEST_MARKDOWN_CONTENT = b"""# Introduction to Machine Learning

Machine learning is a branch of artificial intelligence that focuses on building
systems that learn from data. Rather than being explicitly programmed, these
systems identify patterns in data and make decisions with minimal human
intervention.

## Supervised Learning

Supervised learning uses labeled training data to learn the mapping between
inputs and outputs. Common algorithms include linear regression, decision trees,
and neural networks. The model is trained on a dataset where the correct answers
are known, and it learns to predict outputs for new, unseen inputs.

## Unsupervised Learning

Unsupervised learning deals with unlabeled data. The algorithm tries to find
hidden patterns or intrinsic structures in the input data. Clustering and
dimensionality reduction are two common unsupervised learning tasks.
K-means clustering groups similar data points together, while principal
component analysis reduces the number of features in a dataset.

## Applications

Machine learning has numerous applications across industries:
- Healthcare: Disease prediction and medical image analysis
- Finance: Fraud detection and algorithmic trading
- Natural language processing: Chatbots and translation services
- Computer vision: Object detection and facial recognition

## Conclusion

Machine learning continues to advance rapidly, with new techniques and
applications emerging regularly. Understanding the fundamentals of supervised
and unsupervised learning provides a strong foundation for exploring more
advanced topics like deep learning and reinforcement learning.
"""


def test_end_to_end_metadata_extraction():
    """Test that uploading a document with extract_metadata=true produces metadata."""
    print("\n[TEST] End-to-End Metadata Extraction")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)

    # Clean up before test
    cleanup_test_documents_and_storage(user_id)

    # Upload document with metadata extraction enabled
    timestamp = int(time.time() * 1000)
    filename = f"test_metadata_e2e_{timestamp}.md"

    files = {"file": (filename, BytesIO(TEST_MARKDOWN_CONTENT), "text/markdown")}
    data = {"extract_metadata": "true"}

    response = client.post(
        "/ingestion/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    doc_id = response.json()["id"]
    print(f"  Uploaded document: {doc_id}")

    # Wait for background processing (embedding + metadata extraction)
    print("  Waiting for background processing...")
    time.sleep(8)

    # Query document directly from DB to check metadata fields
    doc = get_document_from_db(doc_id, user_id)
    assert doc is not None, "Document not found in database"

    print(f"  Document status: {doc['status']}")
    print(f"  Metadata status: {doc.get('metadata_status')}")

    # Verify ingestion completed
    assert doc["status"] == "completed", \
        f"Expected status='completed', got '{doc['status']}'. Error: {doc.get('error_message')}"

    # Verify metadata was extracted
    assert doc.get("metadata_status") == "completed", \
        f"Expected metadata_status='completed', got '{doc.get('metadata_status')}'"

    # Verify summary
    summary = doc.get("summary")
    assert summary is not None, "Summary should not be None"
    assert len(summary) > 50, f"Summary too short ({len(summary)} chars): {summary}"
    print(f"  Summary: {summary[:100]}...")

    # Verify document_type
    doc_type = doc.get("document_type")
    assert doc_type is not None, "document_type should not be None"
    assert len(doc_type) > 0, "document_type should not be empty"
    print(f"  Document type: {doc_type}")

    # Verify key_topics
    topics = doc.get("key_topics")
    assert topics is not None, "key_topics should not be None"
    assert isinstance(topics, list), f"key_topics should be a list, got {type(topics)}"
    assert 1 <= len(topics) <= 5, f"Expected 1-5 topics, got {len(topics)}"
    print(f"  Key topics: {topics}")

    # Verify extracted_at
    extracted_at = doc.get("extracted_at")
    assert extracted_at is not None, "extracted_at should not be None"
    print(f"  Extracted at: {extracted_at}")

    # Clean up
    cleanup_test_documents_and_storage(user_id)
    print("[PASS] End-to-end metadata extraction works correctly")


def test_metadata_extraction_disabled():
    """Test that extract_metadata=false skips metadata extraction."""
    print("\n[TEST] Metadata Extraction Disabled")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)

    # Clean up before test
    cleanup_test_documents_and_storage(user_id)

    # Upload document with metadata extraction disabled
    timestamp = int(time.time() * 1000)
    filename = f"test_metadata_disabled_{timestamp}.md"

    files = {"file": (filename, BytesIO(TEST_MARKDOWN_CONTENT), "text/markdown")}
    data = {"extract_metadata": "false"}

    response = client.post(
        "/ingestion/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    doc_id = response.json()["id"]
    print(f"  Uploaded document: {doc_id}")

    # Wait for background processing
    print("  Waiting for background processing...")
    time.sleep(5)

    # Query document directly from DB
    doc = get_document_from_db(doc_id, user_id)
    assert doc is not None, "Document not found in database"

    print(f"  Document status: {doc['status']}")
    print(f"  Metadata status: {doc.get('metadata_status')}")

    # Verify ingestion completed
    assert doc["status"] == "completed", \
        f"Expected status='completed', got '{doc['status']}'. Error: {doc.get('error_message')}"

    # Verify metadata was skipped
    assert doc.get("metadata_status") == "skipped", \
        f"Expected metadata_status='skipped', got '{doc.get('metadata_status')}'"

    # Verify metadata fields are not populated
    assert doc.get("summary") is None, \
        f"Summary should be None when extraction disabled, got: {doc.get('summary')}"
    assert doc.get("document_type") is None, \
        f"document_type should be None when extraction disabled, got: {doc.get('document_type')}"
    assert doc.get("key_topics") in (None, []), \
        f"key_topics should be None or [] when extraction disabled, got: {doc.get('key_topics')}"

    print("  Confirmed: summary, document_type are None, key_topics is None or []")

    # Clean up
    cleanup_test_documents_and_storage(user_id)
    print("[PASS] Metadata extraction correctly skipped when disabled")


def test_metadata_failure_does_not_block_ingestion():
    """Test that metadata extraction failure does not block document ingestion."""
    print("\n[TEST] Metadata Failure Does Not Block Ingestion")

    token = get_auth_token()
    user_id = get_user_id_from_token(token)

    # Clean up before test
    cleanup_test_documents_and_storage(user_id)

    # Upload a very small document (may fail metadata extraction due to
    # insufficient content, or may succeed with minimal output)
    timestamp = int(time.time() * 1000)
    filename = f"test_metadata_small_{timestamp}.md"

    small_content = b"Short note.\n"

    files = {"file": (filename, BytesIO(small_content), "text/markdown")}
    data = {"extract_metadata": "true"}

    response = client.post(
        "/ingestion/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    doc_id = response.json()["id"]
    print(f"  Uploaded small document: {doc_id}")

    # Wait for background processing
    print("  Waiting for background processing...")
    time.sleep(8)

    # Query document directly from DB
    doc = get_document_from_db(doc_id, user_id)
    assert doc is not None, "Document not found in database"

    print(f"  Document status: {doc['status']}")
    print(f"  Metadata status: {doc.get('metadata_status')}")
    print(f"  Chunk count: {doc.get('chunk_count')}")

    # Key assertion: ingestion must succeed regardless of metadata outcome
    assert doc["status"] == "completed", \
        f"Ingestion should complete even if metadata fails. Status: '{doc['status']}', Error: {doc.get('error_message')}"

    # Verify chunks were created
    assert doc.get("chunk_count", 0) > 0, \
        f"Expected chunks to be created, got chunk_count={doc.get('chunk_count')}"

    # Metadata can be either completed or failed - both are acceptable
    metadata_status = doc.get("metadata_status")
    assert metadata_status in ("completed", "failed"), \
        f"Expected metadata_status 'completed' or 'failed', got '{metadata_status}'"

    if metadata_status == "completed":
        print("  Metadata extraction succeeded even on small document")
    else:
        print("  Metadata extraction failed as expected for small document")

    print(f"  Ingestion status: {doc['status']} (chunks: {doc.get('chunk_count')})")

    # Clean up
    cleanup_test_documents_and_storage(user_id)
    print("[PASS] Ingestion succeeded regardless of metadata extraction outcome")


if __name__ == "__main__":
    print("=" * 60)
    print("METADATA INTEGRATION TESTS")
    print("=" * 60)

    try:
        test_end_to_end_metadata_extraction()
        test_metadata_extraction_disabled()
        test_metadata_failure_does_not_block_ingestion()

        print("\n" + "=" * 60)
        print("ALL METADATA INTEGRATION TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise
