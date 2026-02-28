from pydantic import BaseModel
from typing import Optional, List


class SubAgentRequest(BaseModel):
    """Request model for sub-agent execution."""
    task_description: str
    document_id: str
    parent_depth: int = 0
    user_id: str
    document_name: Optional[str] = None  # Pass from caller to avoid redundant DB lookup


class ReasoningStep(BaseModel):
    """A single reasoning step produced during sub-agent execution."""
    step_number: int
    content: str
    timestamp: str


class SubAgentResult(BaseModel):
    """Result of a sub-agent execution."""
    status: str
    result: Optional[str] = None
    reasoning_steps: List[ReasoningStep] = []
    error: Optional[str] = None
    document_name: str
