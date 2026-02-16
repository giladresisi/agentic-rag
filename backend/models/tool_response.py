from pydantic import BaseModel, Field
from typing import List, Optional


class SQLQueryResponse(BaseModel):
    """Response from a SQL query execution."""
    query: str
    results: List[dict]
    row_count: int
    error: Optional[str] = None


class WebSearchResult(BaseModel):
    """A single web search result."""
    title: str
    url: str
    content: str
    score: float


class WebSearchResponse(BaseModel):
    """Response from a web search query."""
    query: str
    results: List[WebSearchResult]
    result_count: int
    error: Optional[str] = None
