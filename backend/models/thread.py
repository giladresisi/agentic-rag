from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class ThreadBase(BaseModel):
    """Base thread model."""
    title: str


class ThreadCreate(ThreadBase):
    """Model for creating a new thread."""
    pass


class Thread(ThreadBase):
    """Full thread model from database."""
    id: UUID
    user_id: UUID
    openai_thread_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThreadResponse(BaseModel):
    """Thread response model."""
    id: str
    title: str
    openai_thread_id: str
    created_at: str
    updated_at: str
