from openai import AsyncOpenAI
from config import settings
from typing import List
from pathlib import Path
import tempfile
import os

# Initialize OpenAI client for embeddings
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


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
                print(f"[PARSE] Using direct text parsing for {file_ext} file")
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            # For complex formats, use docling
            print(f"[PARSE] Using docling for {file_ext} file")
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
    async def generate_embeddings(texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using OpenAI.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)

        Raises:
            Exception: If embedding generation fails
        """
        if not texts:
            return []

        try:
            # Call OpenAI embeddings API
            response = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts
            )

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            return embeddings

        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")


embedding_service = EmbeddingService()
