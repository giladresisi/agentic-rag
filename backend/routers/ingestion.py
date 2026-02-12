from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from middleware.auth_middleware import get_current_user
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service
from models.document import DocumentResponse, ChunkResponse
from typing import List
from pathlib import Path
from config import settings
import tempfile
import os
from datetime import datetime

router = APIRouter()


async def process_document(document_id: str, user_id: str, file_path: str):
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
        print(f"[PROCESS] Starting processing for document {document_id}")

        # Parse document
        print(f"[PROCESS] Step 1/5: Parsing document from {file_path}")
        text_content = await embedding_service.parse_document(file_path)

        if not text_content or not text_content.strip():
            raise Exception("No text content extracted from document")

        print(f"[PROCESS] Step 2/5: Extracted {len(text_content)} characters")

        # Chunk text
        print(f"[PROCESS] Step 3/5: Chunking text")
        chunks = embedding_service.chunk_text(text_content)

        if not chunks:
            raise Exception("No chunks created from text content")

        print(f"[PROCESS] Step 4/5: Created {len(chunks)} chunks, generating embeddings")

        # Generate embeddings
        embeddings = await embedding_service.generate_embeddings(chunks)

        print(f"[PROCESS] Step 5/5: Generated {len(embeddings)} embeddings, saving to database")

        # Save chunks to database
        chunk_records = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_records.append({
                "document_id": document_id,
                "user_id": user_id,
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": idx
            })

        # Insert chunks
        supabase.table("chunks").insert(chunk_records).execute()

        print(f"[PROCESS] Saved {len(chunk_records)} chunks to database")

        # Update document status to completed
        supabase.table("documents").update({
            "status": "completed",
            "chunk_count": len(chunks)
        }).eq("id", document_id).execute()

        print(f"[PROCESS] Document {document_id} completed successfully")

    except Exception as e:
        # Log error for debugging
        error_msg = str(e)
        print(f"[ERROR] Document processing failed for {document_id}: {error_msg}")
        import traceback
        print(traceback.format_exc())

        # Update document status to failed
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
    current_user: dict = Depends(get_current_user)
):
    """Upload and process a document."""
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

    # Log upload attempt
    print(f"[UPLOAD] Received file: {file.filename}, content_type: {file.content_type}, size: {file_size} bytes, extension: {file_ext}")

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
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Create document record
    try:
        response = supabase.table("documents").insert({
            "user_id": current_user["id"],
            "filename": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "file_size_bytes": file_size,
            "storage_path": storage_path,
            "status": "processing",
            "chunk_count": 0
        }).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create document record")

        document = response.data[0]

    except Exception as e:
        # Clean up storage if database insert fails
        try:
            supabase.storage.from_("documents").remove([storage_path])
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")

    # Save file to temp location for processing
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_file.write(content)
    temp_file.close()

    # Start background processing
    background_tasks.add_task(
        process_document,
        document_id=str(document["id"]),
        user_id=current_user["id"],
        file_path=temp_file.name
    )

    return DocumentResponse(
        id=str(document["id"]),
        filename=document["filename"],
        content_type=document["content_type"],
        file_size_bytes=document["file_size_bytes"],
        chunk_count=document["chunk_count"],
        status=document["status"],
        error_message=document.get("error_message"),
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

    # Delete chunks (will cascade due to foreign key)
    try:
        supabase.table("chunks")\
            .delete()\
            .eq("document_id", document_id)\
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chunks: {str(e)}")

    # Delete document record
    try:
        supabase.table("documents")\
            .delete()\
            .eq("id", document_id)\
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    # Delete from storage
    try:
        supabase.storage.from_("documents").remove([document["storage_path"]])
    except Exception:
        # Log but don't fail if storage deletion fails
        pass

    return {"message": "Document deleted successfully"}
