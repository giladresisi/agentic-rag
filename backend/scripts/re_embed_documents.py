"""Re-embed all documents with a new provider/model/dimensions configuration.

Usage:
    python -m scripts.re_embed_documents --provider openai --model text-embedding-3-large --dimensions 3072

This script:
1. Fetches all documents from Supabase
2. For each document: deletes old chunks, downloads file, re-embeds, updates dimensions
3. Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and provider API key in .env
"""

import argparse
import asyncio
import sys
import os
import tempfile

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service
from services.provider_service import provider_service


async def re_embed_document(supabase, document: dict, provider: str, model: str, dimensions: int):
    """Re-embed a single document with new provider/model/dimensions."""
    doc_id = document["id"]
    filename = document["filename"]
    storage_path = document["storage_path"]

    print(f"  Processing: {filename} (id={doc_id})")

    # Download file from storage
    try:
        file_bytes = supabase.storage.from_("documents").download(storage_path)
    except Exception as e:
        print(f"  ERROR: Failed to download {filename}: {e}")
        return False

    # Save to temp file for parsing
    file_ext = os.path.splitext(filename)[1]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    try:
        temp_file.write(file_bytes)
        temp_file.close()

        # Parse document
        text_content = await embedding_service.parse_document(temp_file.name)
        if not text_content or not text_content.strip():
            print(f"  WARNING: No text content extracted from {filename}, skipping")
            return False

        # Chunk text
        chunks = embedding_service.chunk_text(text_content)
        if not chunks:
            print(f"  WARNING: No chunks created from {filename}, skipping")
            return False

        # Generate embeddings using the specified provider and model
        print(f"  Generating embeddings with {provider}/{model}...")
        embeddings = await provider_service.create_embeddings(
            provider=provider,
            model=model,
            texts=chunks
        )

        # Verify actual dimensions match expected dimensions
        actual_dimensions = len(embeddings[0]) if embeddings else 0
        if actual_dimensions != dimensions:
            print(f"  WARNING: Expected {dimensions} dimensions but got {actual_dimensions}. Using actual dimensions.")
            dimensions = actual_dimensions

        # Delete old chunks
        supabase.table("chunks").delete().eq("document_id", doc_id).execute()

        # Insert new chunks with embedding_dimensions
        chunk_records = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "document_id": doc_id,
                "user_id": document["user_id"],
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": idx,
                "embedding_dimensions": dimensions
            })

        supabase.table("chunks").insert(chunk_records).execute()

        # Update document embedding_dimensions and chunk_count
        supabase.table("documents").update({
            "embedding_dimensions": dimensions,
            "chunk_count": len(chunks)
        }).eq("id", doc_id).execute()

        print(f"  OK: {len(chunks)} chunks embedded with {dimensions} dimensions")
        return True

    except Exception as e:
        print(f"  ERROR: Failed to re-embed {filename}: {e}")
        # Mark document as failed
        supabase.table("documents").update({
            "status": "failed",
            "error_message": f"Re-embedding failed: {str(e)}"
        }).eq("id", doc_id).execute()
        return False

    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)


async def main(provider: str, model: str, dimensions: int):
    """Re-embed all documents."""
    supabase = get_supabase_admin()

    print(f"Re-embedding all documents")
    print(f"  Provider: {provider}")
    print(f"  Model: {model}")
    print(f"  Dimensions: {dimensions}")
    print()

    # Fetch all documents
    response = supabase.table("documents").select("*").eq("status", "completed").execute()
    documents = response.data

    if not documents:
        print("No completed documents found. Nothing to re-embed.")
        return

    print(f"Found {len(documents)} document(s) to re-embed")
    print()

    success_count = 0
    fail_count = 0

    for doc in documents:
        result = await re_embed_document(supabase, doc, provider, model, dimensions)
        if result:
            success_count += 1
        else:
            fail_count += 1

    print()
    print(f"Re-embedding complete: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-embed all documents with a new model/dimensions")
    parser.add_argument("--provider", required=True, choices=["openai", "openrouter", "lmstudio"],
                        help="Embedding provider to use")
    parser.add_argument("--model", required=True,
                        help="Embedding model name (e.g., text-embedding-3-large)")
    parser.add_argument("--dimensions", required=True, type=int,
                        help="Embedding vector dimensions (e.g., 1536, 3072)")

    args = parser.parse_args()
    asyncio.run(main(args.provider, args.model, args.dimensions))
