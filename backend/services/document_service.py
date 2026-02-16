"""Service for retrieving and reading full document content."""

import os
import tempfile
from pathlib import Path

from fastapi import HTTPException

from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service


def get_document_by_id(document_id: str, user_id: str) -> dict:
    """Fetch a document record by ID, scoped to the given user.

    Args:
        document_id: UUID of the document
        user_id: UUID of the owning user (RLS enforcement)

    Returns:
        Document dict from the database

    Raises:
        HTTPException: 404 if not found, 500 on database error
    """
    supabase = get_supabase_admin()

    try:
        response = supabase.table("documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "no rows" in error_msg or "not found" in error_msg or "single" in error_msg:
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def read_full_document(document_id: str, user_id: str) -> str:
    """Download a document from storage and parse its full text content.

    Args:
        document_id: UUID of the document
        user_id: UUID of the owning user

    Returns:
        Full text content of the document

    Raises:
        HTTPException: 404 if document not found, 500 on storage/parse failure
    """
    document = get_document_by_id(document_id, user_id)

    supabase = get_supabase_admin()
    storage_path = document["storage_path"]
    filename = document["filename"]

    # Download file from storage
    try:
        file_bytes = supabase.storage.from_("documents").download(storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download document from storage: {str(e)}"
        )

    # Save to temp file and parse
    file_ext = os.path.splitext(filename)[1]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    try:
        temp_file.write(file_bytes)
        temp_file.close()

        text_content = await embedding_service.parse_document(temp_file.name)

        if not text_content or not text_content.strip():
            raise HTTPException(
                status_code=500,
                detail="No text content could be extracted from document"
            )

        return text_content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse document: {str(e)}"
        )
    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
