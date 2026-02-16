from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from middleware.auth_middleware import get_current_user
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service
from services.metadata_service import metadata_service
from models.document import DocumentResponse, ChunkResponse
from typing import List, Optional
from pathlib import Path
from config import settings
import tempfile
import os
from datetime import datetime

router = APIRouter()


async def process_document(
    document_id: str,
    user_id: str,
    file_path: str,
    provider: str = "openai",
    model: Optional[str] = None,
    dimensions: int = 1536,
    base_url: Optional[str] = None,
    extract_metadata: bool = True,
    metadata_provider: Optional[str] = None,
    metadata_model: Optional[str] = None,
):
    """Background task to process uploaded document.

    Steps:
    1. Parse document to extract text
    2. Chunk text into segments
    3. Generate embeddings for chunks
    4. Save chunks to database
    5. Update document status
    """
    supabase = get_supabase_admin()

    try:
        # Parse document
        text_content = await embedding_service.parse_document(file_path)

        if not text_content or not text_content.strip():
            raise Exception("No text content extracted from document")

        # Compute text content hash
        text_content_hash = embedding_service.compute_text_hash(text_content)

        # Check for existing document with same text hash
        duplicate_check = supabase.table("documents")\
            .select("id, filename, created_at, chunk_count")\
            .eq("user_id", user_id)\
            .eq("text_content_hash", text_content_hash)\
            .eq("status", "completed")\
            .execute()

        if duplicate_check.data:
            # Duplicate found - skip processing
            original_doc = duplicate_check.data[0]

            # Update current document as duplicate
            supabase.table("documents").update({
                "status": "duplicate",
                "duplicate_of": original_doc["id"],
                "text_content_hash": text_content_hash,
                "chunk_count": original_doc["chunk_count"],
            }).eq("id", document_id).execute()

            # Clean up temp file and exit early
            if os.path.exists(file_path):
                os.remove(file_path)
            return

        # Not a duplicate - update hash and continue processing
        supabase.table("documents").update({
            "text_content_hash": text_content_hash
        }).eq("id", document_id).execute()

        # Metadata extraction (Module 4)
        if extract_metadata:
            try:
                # Mark as processing
                supabase.table("documents").update({
                    "metadata_status": "processing"
                }).eq("id", document_id).eq("user_id", user_id).execute()

                # Extract metadata
                metadata = await metadata_service.extract_metadata(
                    text_content=text_content,
                    document_id=document_id,
                    user_id=user_id,
                    provider=metadata_provider or provider,
                    model=metadata_model or "gpt-4o-mini",
                    base_url=base_url
                )

                # Update document with metadata
                await metadata_service.update_document_metadata(
                    document_id=document_id,
                    metadata=metadata,
                    supabase=supabase,
                    user_id=user_id
                )
            except Exception as e:
                # Mark as failed but continue ingestion
                # Error is captured in database field, silent production operation
                supabase.table("documents").update({
                    "metadata_status": "failed",
                    "error_message": f"Metadata extraction failed: {str(e)}"
                }).eq("id", document_id).eq("user_id", user_id).execute()
        else:
            # Mark as skipped
            supabase.table("documents").update({
                "metadata_status": "skipped"
            }).eq("id", document_id).eq("user_id", user_id).execute()

        # Chunk text
        chunks = embedding_service.chunk_text(text_content)

        if not chunks:
            raise Exception("No chunks created from text content")

        # Generate embeddings using specified provider
        embeddings = await embedding_service.generate_embeddings(
            chunks,
            provider=provider,
            model=model,
            base_url=base_url,
        )

        # Validate embeddings were generated
        if not embeddings or not embeddings[0]:
            raise Exception("No embeddings generated")

        # Get actual embedding dimensions from first embedding
        actual_dimensions = len(embeddings[0])

        # Update dimensions parameter to match actual embeddings
        dimensions = actual_dimensions

        # Save chunks to database
        chunk_records = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "document_id": document_id,
                "user_id": user_id,
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": idx,
                "embedding_dimensions": dimensions,
            })

        # Insert chunks
        supabase.table("chunks").insert(chunk_records).execute()

        # Update document status to completed
        supabase.table("documents").update({
            "status": "completed",
            "chunk_count": len(chunks),
            "embedding_dimensions": dimensions,
        }).eq("id", document_id).execute()

    except Exception as e:
        # Update document status to failed
        error_msg = str(e)
        supabase.table("documents").update({
            "status": "failed",
            "error_message": error_msg
        }).eq("id", document_id).execute()

    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    provider: str = Form("openai"),
    model: Optional[str] = Form(None),
    dimensions: int = Form(1536),
    base_url: Optional[str] = Form(None),
    extract_metadata: str = Form("true"),  # Changed to str to handle form data correctly
    metadata_provider: Optional[str] = Form(None),
    metadata_model: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process a document."""
    # Convert string form data to boolean
    extract_metadata_bool = extract_metadata.lower() in ('true', '1', 'yes')

    supabase = get_supabase_admin()

    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    # Parse supported types - handle various formats
    supported_types = []
    raw_value = settings.SUPPORTED_FILE_TYPES.strip()
    # Remove JSON array brackets if present
    raw_value = raw_value.strip('[').strip(']')
    for ext in raw_value.split(","):
        # Remove quotes, brackets, and whitespace
        ext = ext.strip().strip('"').strip("'").strip()
        # Ensure it starts with a dot
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        if ext:  # Only add non-empty extensions
            supported_types.append(ext)

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_ext not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}' for file '{file.filename}'. Supported: {', '.join(supported_types)}"
        )

    # Validate file size
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File '{file.filename}' is too large ({file_size / 1024 / 1024:.1f}MB). Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Create storage path (user_id/filename)
    storage_path = f"{current_user['id']}/{file.filename}"

    try:
        # Upload to Supabase Storage
        supabase.storage.from_("documents").upload(
            storage_path,
            content,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is due to duplicate path
        if "duplicate" in error_msg or "already exists" in error_msg:
            raise HTTPException(
                status_code=409,
                detail=f"File '{file.filename}' already exists. Please rename the file or delete the existing one."
            )
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Compute file content hash
    file_content_hash = None
    try:
        # Write content to temp file to compute hash
        temp_hash_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        temp_hash_file.write(content)
        temp_hash_file.close()
        file_content_hash = embedding_service.compute_file_hash(temp_hash_file.name)
        os.unlink(temp_hash_file.name)  # Clean up temp file
    except Exception:
        # Silently continue if hash computation fails
        pass

    # Create document record
    try:
        response = supabase.table("documents").insert({
            "user_id": current_user["id"],
            "filename": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "file_size_bytes": file_size,
            "storage_path": storage_path,
            "status": "processing",
            "chunk_count": 0,
            "file_content_hash": file_content_hash
        }).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create document record")

        document = response.data[0]

    except HTTPException:
        # Re-raise HTTP exceptions (from line 278) after attempting cleanup
        try:
            supabase.storage.from_("documents").remove([storage_path])
        except Exception as cleanup_error:
            # Storage cleanup failed - file will be orphaned
            # Re-raise original error with cleanup warning
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create document record. Storage cleanup also failed: {str(cleanup_error)}"
            )
        raise  # Re-raise original HTTPException
    except Exception as e:
        # Clean up storage if database insert fails
        cleanup_success = True
        try:
            supabase.storage.from_("documents").remove([storage_path])
        except Exception as cleanup_error:
            cleanup_success = False

        # Report both the original error and cleanup status
        error_msg = f"Failed to create document: {str(e)}"
        if not cleanup_success:
            error_msg += " (Warning: Storage file may be orphaned)"
        raise HTTPException(status_code=500, detail=error_msg)

    # Save file to temp location for processing
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_file.write(content)
    temp_file.close()

    # Start background processing
    background_tasks.add_task(
        process_document,
        document_id=str(document["id"]),
        user_id=current_user["id"],
        file_path=temp_file.name,
        provider=provider,
        model=model,
        dimensions=dimensions,
        base_url=base_url,
        extract_metadata=extract_metadata_bool,  # Use converted boolean
        metadata_provider=metadata_provider,
        metadata_model=metadata_model,
    )

    return DocumentResponse(
        id=str(document["id"]),
        filename=document["filename"],
        content_type=document["content_type"],
        file_size_bytes=document["file_size_bytes"],
        chunk_count=document["chunk_count"],
        status=document["status"],
        error_message=document.get("error_message"),
        duplicate_of=str(document["duplicate_of"]) if document.get("duplicate_of") else None,
        summary=document.get("summary"),
        document_type=document.get("document_type"),
        key_topics=document.get("key_topics"),
        extracted_at=document.get("extracted_at"),
        metadata_status=document.get("metadata_status"),
        created_at=str(document["created_at"]),
        updated_at=str(document["updated_at"])
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all documents for the current user."""
    supabase = get_supabase_admin()

    try:
        response = supabase.table("documents")\
            .select("*")\
            .eq("user_id", current_user["id"])\
            .order("created_at", desc=True)\
            .execute()

        documents = []
        for doc in response.data:
            documents.append(DocumentResponse(
                id=str(doc["id"]),
                filename=doc["filename"],
                content_type=doc["content_type"],
                file_size_bytes=doc["file_size_bytes"],
                chunk_count=doc.get("chunk_count", 0),
                status=doc["status"],
                error_message=doc.get("error_message"),
                duplicate_of=str(doc["duplicate_of"]) if doc.get("duplicate_of") else None,
                summary=doc.get("summary"),
                document_type=doc.get("document_type"),
                key_topics=doc.get("key_topics"),
                extracted_at=doc.get("extracted_at"),
                metadata_status=doc.get("metadata_status"),
                created_at=str(doc["created_at"]),
                updated_at=str(doc["updated_at"])
            ))

        return documents

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific document."""
    supabase = get_supabase_admin()

    try:
        response = supabase.table("documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc = response.data

        return DocumentResponse(
            id=str(doc["id"]),
            filename=doc["filename"],
            content_type=doc["content_type"],
            file_size_bytes=doc["file_size_bytes"],
            chunk_count=doc.get("chunk_count", 0),
            status=doc["status"],
            error_message=doc.get("error_message"),
            duplicate_of=str(doc["duplicate_of"]) if doc.get("duplicate_of") else None,
            summary=doc.get("summary"),
            document_type=doc.get("document_type"),
            key_topics=doc.get("key_topics"),
            extracted_at=doc.get("extracted_at"),
            metadata_status=doc.get("metadata_status"),
            created_at=str(doc["created_at"]),
            updated_at=str(doc["updated_at"])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all chunks for a document."""
    supabase = get_supabase_admin()

    # Verify document ownership
    try:
        doc_response = supabase.table("documents")\
            .select("id")\
            .eq("id", document_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()

        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        # Check if error is "no rows found" from Supabase
        error_msg = str(e).lower()
        if "no rows" in error_msg or "not found" in error_msg or "single" in error_msg:
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=f"Failed to verify document: {str(e)}")

    # Get chunks
    try:
        response = supabase.table("chunks")\
            .select("id, document_id, content, chunk_index, created_at")\
            .eq("document_id", document_id)\
            .order("chunk_index")\
            .execute()

        chunks = []
        for chunk in response.data:
            chunks.append(ChunkResponse(
                id=str(chunk["id"]),
                document_id=str(chunk["document_id"]),
                content=chunk["content"],
                chunk_index=chunk["chunk_index"],
                created_at=str(chunk["created_at"])
            ))

        return chunks

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document and all its chunks."""
    supabase = get_supabase_admin()

    # Get document to retrieve storage path
    try:
        response = supabase.table("documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = response.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

    # Delete from storage FIRST (before database)
    # If this fails, we want to know about it before modifying the database
    storage_error = None
    try:
        supabase.storage.from_("documents").remove([document["storage_path"]])
    except Exception as e:
        # Capture error but continue - file might already be deleted
        storage_error = str(e)

    # Chunks cascade deleted automatically via ON DELETE CASCADE constraint (migration 006, line 19)

    # Delete document record from database
    try:
        supabase.table("documents")\
            .delete()\
            .eq("id", document_id)\
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    # If storage deletion failed, include warning in response
    if storage_error:
        return {
            "message": "Document deleted successfully",
            "warning": f"Storage file may not have been deleted: {storage_error}"
        }

    return {"message": "Document deleted successfully"}


@router.get("/chunks/exists")
async def chunks_exist(current_user: dict = Depends(get_current_user)):
    """Check if any chunks exist for the current user."""
    supabase = get_supabase_admin()

    try:
        response = supabase.table("chunks")\
            .select("id", count="exact")\
            .eq("user_id", current_user["id"])\
            .limit(1)\
            .execute()

        return {"exists": response.count is not None and response.count > 0}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check chunks: {str(e)}")
