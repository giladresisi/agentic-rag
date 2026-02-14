from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class DocumentBase(BaseModel):
    """Base document model."""
    filename: str
    content_type: str
    file_size_bytes: int


class UploadDocumentRequest(DocumentBase):
    """Model for uploading a new document."""
    storage_path: str


class Document(DocumentBase):
    """Full document model from database."""
    id: UUID
    user_id: UUID
    storage_path: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Document response model."""
    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    duplicate_of: Optional[str] = None
    created_at: str
    updated_at: str


class ChunkBase(BaseModel):
    """Base chunk model."""
    content: str
    embedding: list[float]
    chunk_index: int


class Chunk(ChunkBase):
    """Full chunk model from database."""
    id: UUID
    document_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    """Chunk response model."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    created_at: str
