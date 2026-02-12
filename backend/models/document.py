from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class DocumentBase(BaseModel):
    """Base document model."""
    filename: str
    file_type: str
    file_size: int


class UploadDocumentRequest(DocumentBase):
    """Model for uploading a new document."""
    storage_path: str


class Document(DocumentBase):
    """Full document model from database."""
    id: UUID
    user_id: UUID
    storage_path: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Document response model."""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: str
    processed_at: Optional[str] = None


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
