from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Literal, List, Dict, Any


class MessageBase(BaseModel):
    """Base message model."""
    content: str


class MessageCreate(MessageBase):
    """Model for creating a new message."""
    # Provider configuration (optional - uses defaults if not provided)
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None


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
    sources: Optional[List[Dict[str, Any]]] = None
    subagent_metadata: Optional[Dict[str, Any]] = None
