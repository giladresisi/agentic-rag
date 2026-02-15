from pydantic import BaseModel
from typing import List, Optional


class RerankDocument(BaseModel):
    """Document to be reranked."""
    id: str
    text: str


class RerankRequest(BaseModel):
    """Request for reranking documents."""
    query: str
    documents: List[RerankDocument]
    top_n: int
    model: Optional[str] = None


class RerankResult(BaseModel):
    """Result from reranking a single document."""
    id: str
    relevance_score: float
    index: int


class RerankResponse(BaseModel):
    """Response from reranking service."""
    results: List[RerankResult]
    model: str
    provider: str
