from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal


class MessageBase(BaseModel):
    """Base message model."""
    content: str


class MessageCreate(MessageBase):
    """Model for creating a new message."""
    pass


class Message(MessageBase):
    """Full message model from database."""
    id: UUID
    thread_id: UUID
    user_id: UUID
    role: Literal["user", "assistant"]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response model."""
    id: str
    thread_id: str
    role: str
    content: str
    created_at: str
