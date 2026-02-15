"""Reranking service for improving retrieval quality."""

from typing import List, Optional, Dict
from models.reranking import RerankDocument, RerankRequest, RerankResult, RerankResponse
from config import settings

# Lazy-loaded global model instance
_local_model = None


def get_providers() -> Dict[str, str]:
    """Get available reranking providers.

    Returns:
        Dictionary of provider ID to display name
    """
    providers = {
        "local": "Local Cross-Encoder"
    }

    # Only add Cohere if API key is configured and package is available
    if settings.COHERE_API_KEY:
        try:
            import cohere
            providers["cohere"] = "Cohere Rerank API"
        except ImportError:
            # Cohere package not installed, skip provider
            pass

    return providers


def rerank_local(
    query: str,
    documents: List[RerankDocument],
    top_n: int,
    model: Optional[str] = None
) -> RerankResponse:
    """Rerank documents using local cross-encoder model.

    Args:
        query: Search query
        documents: List of documents to rerank
        top_n: Number of top results to return
        model: Model name (optional, uses config default)

    Returns:
        RerankResponse with reranked results
    """
    global _local_model

    # Lazy load model on first use
    if _local_model is None:
        from sentence_transformers import CrossEncoder
        model_name = model or settings.LOCAL_RERANK_MODEL
        _local_model = CrossEncoder(model_name)

    # Prepare query-document pairs
    pairs = [(query, doc.text) for doc in documents]

    # Get relevance scores
    scores = _local_model.predict(pairs)

    # Create results with scores and original indices
    results = [
        RerankResult(
            id=doc.id,
            relevance_score=float(score),
            index=idx
        )
        for idx, (doc, score) in enumerate(zip(documents, scores))
    ]

    # Sort by relevance score (descending) and take top_n
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    results = results[:top_n]

    model_name = model or settings.LOCAL_RERANK_MODEL

    return RerankResponse(
        results=results,
        model=model_name,
        provider="local"
    )


def rerank_cohere(
    query: str,
    documents: List[RerankDocument],
    top_n: int,
    model: Optional[str] = None
) -> RerankResponse:
    """Rerank documents using Cohere Rerank API.

    Args:
        query: Search query
        documents: List of documents to rerank
        top_n: Number of top results to return
        model: Model name (optional, uses config default)

    Returns:
        RerankResponse with reranked results

    Raises:
        ImportError: If cohere package not installed
        ValueError: If COHERE_API_KEY not configured
    """
    try:
        import cohere
    except ImportError:
        raise ImportError("cohere package not installed. Run: pip install cohere")

    if not settings.COHERE_API_KEY:
        raise ValueError("COHERE_API_KEY not configured")

    # Create Cohere client
    client = cohere.Client(api_key=settings.COHERE_API_KEY)

    # Prepare documents for Cohere API (just text strings)
    doc_texts = [doc.text for doc in documents]

    # Call Cohere rerank API
    model_name = model or settings.COHERE_RERANK_MODEL
    response = client.rerank(
        query=query,
        documents=doc_texts,
        model=model_name,
        top_n=top_n
    )

    # Convert Cohere results to our format
    results = [
        RerankResult(
            id=documents[result.index].id,
            relevance_score=result.relevance_score,
            index=result.index
        )
        for result in response.results
    ]

    return RerankResponse(
        results=results,
        model=model_name,
        provider="cohere"
    )


def rerank(
    request: RerankRequest,
    provider: str = "local"
) -> RerankResponse:
    """Main entry point for reranking documents.

    Args:
        request: Reranking request with query, documents, top_n
        provider: Provider to use ("local" or "cohere")

    Returns:
        RerankResponse with reranked results

    Raises:
        ValueError: If provider is invalid
    """
    if provider == "local":
        return rerank_local(
            query=request.query,
            documents=request.documents,
            top_n=request.top_n,
            model=request.model
        )
    elif provider == "cohere":
        return rerank_cohere(
            query=request.query,
            documents=request.documents,
            top_n=request.top_n,
            model=request.model
        )
    else:
        available = ", ".join(get_providers().keys())
        raise ValueError(f"Invalid provider: {provider}. Available: {available}")
