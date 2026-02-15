"""Service for extracting structured metadata from documents via LLM."""

from datetime import datetime, timezone
from typing import Optional

from models.metadata import DocumentMetadata
from services.provider_service import provider_service

# Maximum text length to send for metadata extraction (~25k tokens)
MAX_TEXT_LENGTH = 100_000


class MetadataService:
    """Service for LLM-based document metadata extraction."""

    @staticmethod
    async def extract_metadata(
        text_content: str,
        document_id: str,
        user_id: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ) -> DocumentMetadata:
        """Extract structured metadata from document text using an LLM.

        Args:
            text_content: The document text to analyze
            document_id: Document ID for logging
            user_id: User ID (for logging/context)
            provider: LLM provider identifier
            model: Chat model name
            base_url: Optional override base URL

        Returns:
            DocumentMetadata instance with extracted fields

        Raises:
            RuntimeError: If extraction fails
        """
        try:
            # Truncate long texts to control cost
            if len(text_content) > MAX_TEXT_LENGTH:
                text_content = text_content[:MAX_TEXT_LENGTH]

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a document analysis expert. "
                        "Extract structured metadata from the document. "
                        "Be concise and accurate."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract metadata from this document:\n\n{text_content}",
                },
            ]

            result = await provider_service.create_structured_completion(
                provider=provider,
                model=model,
                messages=messages,
                response_schema=DocumentMetadata,
                base_url=base_url,
            )

            return result

        except Exception as e:
            raise RuntimeError(f"Metadata extraction failed: {e}")

    @staticmethod
    async def update_document_metadata(
        document_id: str,
        metadata: DocumentMetadata,
        supabase,
        user_id: str,
    ) -> None:
        """Persist extracted metadata to the documents table.

        Args:
            document_id: Document ID to update
            metadata: Extracted DocumentMetadata instance
            supabase: Supabase client
            user_id: User ID for RLS filtering

        Raises:
            RuntimeError: If the database update fails
        """
        try:
            update_data = {
                "summary": metadata.summary,
                "document_type": metadata.document_type,
                "key_topics": metadata.key_topics,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "metadata_status": "completed",
            }

            supabase.table("documents").update(update_data).eq(
                "id", document_id
            ).eq("user_id", user_id).execute()

        except Exception as e:
            raise RuntimeError(f"Failed to update document metadata: {e}")


metadata_service = MetadataService()
