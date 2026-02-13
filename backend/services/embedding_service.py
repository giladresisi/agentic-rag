from config import settings
from services.provider_service import provider_service
from typing import List, Optional
from pathlib import Path
import tempfile
import os


class EmbeddingService:
    """Service for document parsing, chunking, and embedding generation."""

    @staticmethod
    async def parse_document(file_path: str) -> str:
        """Parse document to extract text content.

        For simple text formats (.txt, .md, .html), reads directly.
        For complex formats (.pdf, .docx), uses docling.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content from the document

        Raises:
            Exception: If parsing fails
        """
        try:
            # Get file extension
            file_ext = Path(file_path).suffix.lower()

            # For simple text-based formats, read directly
            if file_ext in ['.txt', '.md', '.html']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            # For complex formats, use docling
            from docling.document_converter import DocumentConverter

            # Initialize converter
            converter = DocumentConverter()

            # Convert document
            result = converter.convert(file_path)

            # Extract markdown text
            text_content = result.document.export_to_markdown()

            return text_content

        except Exception as e:
            raise Exception(f"Failed to parse document: {str(e)}")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text content to chunk
            chunk_size: Size of each chunk in characters (default from config)
            chunk_overlap: Number of overlapping characters (default from config)

        Returns:
            List of text chunks
        """
        # Use config defaults if not provided
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # Handle empty text
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position
            end = start + chunk_size

            # Extract chunk
            chunk = text[start:end]

            # Only add non-empty chunks
            if chunk.strip():
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - chunk_overlap

            # Prevent infinite loop if overlap >= chunk_size
            if chunk_overlap >= chunk_size:
                break

        return chunks

    @staticmethod
    async def generate_embeddings(
        texts: List[str],
        provider: str = "openai",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts using the specified provider.

        Args:
            texts: List of text strings to embed
            provider: Provider identifier (default: openai)
            model: Embedding model name (default from config)
            base_url: Optional override base URL

        Returns:
            List of embedding vectors (each is a list of floats)

        Raises:
            Exception: If embedding generation fails
        """
        if not texts:
            return []

        model = model or settings.EMBEDDING_MODEL

        try:
            return await provider_service.create_embeddings(
                provider=provider,
                model=model,
                texts=texts,
                base_url=base_url,
            )
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")


embedding_service = EmbeddingService()
