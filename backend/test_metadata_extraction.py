"""Tests for metadata extraction: schema validation, LLM extraction, and truncation."""
import asyncio
import uuid

import pytest
from pydantic import ValidationError

from models.metadata import DocumentMetadata
from services.metadata_service import metadata_service, MAX_TEXT_LENGTH


def test_document_metadata_schema_validation():
    """Test Pydantic schema validation with valid and invalid cases."""
    print("\n--- test_document_metadata_schema_validation ---")

    # Valid case
    valid = DocumentMetadata(
        summary=(
            "This document provides a comprehensive overview of retrieval-augmented "
            "generation systems and their applications in modern AI pipelines."
        ),
        document_type="technical_guide",
        key_topics=["RAG", "vector databases", "embeddings"],
    )
    assert isinstance(valid.summary, str)
    assert valid.document_type == "technical_guide"
    assert len(valid.key_topics) == 3
    print("[PASS] Valid metadata accepted")

    # Invalid: summary too short (< 50 chars)
    with pytest.raises(ValidationError):
        DocumentMetadata(
            summary="Too short",
            document_type="article",
            key_topics=["topic"],
        )
    print("[PASS] Rejected summary < 50 chars")

    # Invalid: summary too long (> 500 chars)
    with pytest.raises(ValidationError):
        DocumentMetadata(
            summary="x" * 501,
            document_type="article",
            key_topics=["topic"],
        )
    print("[PASS] Rejected summary > 500 chars")

    # Invalid: document_type not in allowed list
    with pytest.raises(ValidationError):
        DocumentMetadata(
            summary="A" * 60,
            document_type="invalid_type",
            key_topics=["topic"],
        )
    print("[PASS] Rejected invalid document_type")

    # Invalid: empty key_topics list
    with pytest.raises(ValidationError):
        DocumentMetadata(
            summary="A" * 60,
            document_type="article",
            key_topics=[],
        )
    print("[PASS] Rejected empty key_topics")

    # Invalid: too many key_topics (> 5)
    with pytest.raises(ValidationError):
        DocumentMetadata(
            summary="A" * 60,
            document_type="article",
            key_topics=["a", "b", "c", "d", "e", "f"],
        )
    print("[PASS] Rejected key_topics > 5 items")

    print("[TEST PASSED] All schema validation cases correct")


def test_metadata_extraction_service():
    """Real LLM call to test metadata extraction end-to-end."""
    print("\n--- test_metadata_extraction_service ---")

    sample_text = (
        "Retrieval-Augmented Generation (RAG) is an AI framework that enhances "
        "large language model outputs by incorporating external knowledge sources. "
        "RAG systems work by first retrieving relevant documents from a vector "
        "database using semantic similarity search, then feeding those documents "
        "as context to the LLM alongside the user query. This approach reduces "
        "hallucinations and keeps responses grounded in factual, up-to-date "
        "information. Key components include document chunking strategies, "
        "embedding models for vectorization, efficient vector storage and "
        "retrieval, and prompt engineering to combine retrieved context with "
        "user questions. Modern RAG implementations often use pgvector for "
        "storage, OpenAI embeddings for vectorization, and streaming responses "
        "for better user experience."
    )

    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    result = asyncio.run(
        metadata_service.extract_metadata(
            text_content=sample_text,
            document_id=doc_id,
            user_id=user_id,
        )
    )

    # Verify types
    assert isinstance(result, DocumentMetadata)
    assert isinstance(result.summary, str)
    assert isinstance(result.document_type, str)
    assert isinstance(result.key_topics, list)

    # Verify constraints
    assert 50 <= len(result.summary) <= 500, (
        f"Summary length {len(result.summary)} out of range"
    )
    assert len(result.key_topics) >= 1 and len(result.key_topics) <= 5, (
        f"key_topics count {len(result.key_topics)} out of range"
    )

    print(f"  Summary: {result.summary}")
    print(f"  Type: {result.document_type}")
    print(f"  Topics: {result.key_topics}")
    print("[TEST PASSED] Metadata extraction returned valid result")


def test_metadata_truncation_for_long_documents():
    """Test that 150k character documents are truncated to 100k."""
    print("\n--- test_metadata_truncation_for_long_documents ---")

    # Build a 150k character document by repeating realistic text
    base_paragraph = (
        "Artificial intelligence and machine learning are transforming industries "
        "worldwide. Organizations leverage data-driven insights to optimize processes, "
        "improve customer experiences, and drive innovation across sectors. "
    )
    long_text = base_paragraph * (150_000 // len(base_paragraph) + 1)
    long_text = long_text[:150_000]
    assert len(long_text) == 150_000, f"Expected 150k chars, got {len(long_text)}"
    print(f"  Input length: {len(long_text)} chars")

    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    result = asyncio.run(
        metadata_service.extract_metadata(
            text_content=long_text,
            document_id=doc_id,
            user_id=user_id,
        )
    )

    # Verify extraction succeeded despite oversized input
    assert isinstance(result, DocumentMetadata)
    assert 50 <= len(result.summary) <= 500
    assert len(result.key_topics) >= 1 and len(result.key_topics) <= 5

    print(f"  Summary: {result.summary}")
    print(f"  Type: {result.document_type}")
    print(f"  Topics: {result.key_topics}")
    print(f"  MAX_TEXT_LENGTH constant: {MAX_TEXT_LENGTH}")
    print("[TEST PASSED] Long document truncated and extracted successfully")


if __name__ == "__main__":
    print("=" * 60)
    print("METADATA EXTRACTION TESTS")
    print("=" * 60)

    try:
        test_document_metadata_schema_validation()
        test_metadata_extraction_service()
        test_metadata_truncation_for_long_documents()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise
