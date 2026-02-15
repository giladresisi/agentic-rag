from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Structured metadata extracted from a document via LLM."""

    summary: str = Field(
        ...,
        description="2-3 sentence summary of the document's main content and purpose",
        min_length=50,
        max_length=500,
    )
    document_type: str = Field(
        ...,
        description="The type/category of the document",
        pattern=r"^(article|research_paper|technical_guide|report|tutorial|documentation|reference|other)$",
    )
    key_topics: list[str] = Field(
        ...,
        description="3-5 main topics or themes covered in the document",
        min_length=1,
        max_length=5,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "summary": (
                    "This document provides a comprehensive guide to building "
                    "retrieval-augmented generation systems using vector databases. "
                    "It covers embedding strategies, chunking approaches, and query optimization techniques."
                ),
                "document_type": "technical_guide",
                "key_topics": [
                    "RAG architecture",
                    "vector databases",
                    "text embeddings",
                    "chunking strategies",
                ],
            }
        }
