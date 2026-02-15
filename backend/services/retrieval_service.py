from typing import List, Dict
from config import settings
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin
from services import reranking_service
from models.reranking import RerankDocument, RerankRequest


class RetrievalService:
    """Service for retrieving relevant document chunks using vector similarity search."""

    @staticmethod
    async def retrieve_relevant_chunks(
        query: str,
        user_id: str,
        limit: int = None,
        similarity_threshold: float = None,
        enable_reranking: bool = None
    ) -> List[Dict]:
        """Retrieve relevant document chunks for a given query.

        Args:
            query: The search query text
            user_id: User ID for RLS filtering
            limit: Maximum number of chunks to retrieve (default from config)
            similarity_threshold: Minimum similarity score 0-1 (default from config)
            enable_reranking: Whether to rerank results (default from config)

        Returns:
            List of dictionaries containing chunk data and metadata:
            [
                {
                    "id": "uuid",
                    "content": "chunk text",
                    "document_id": "uuid",
                    "document_name": "file.pdf",
                    "similarity": 0.85,
                    "keyword_rank": 0.5,  # if hybrid search
                    "hybrid_score": 0.92,  # if hybrid search
                    "rerank_score": 0.95  # if reranking enabled
                },
                ...
            ]

        Raises:
            Exception: If retrieval fails
        """
        # Use config defaults if not provided
        limit = limit or settings.RETRIEVAL_LIMIT
        similarity_threshold = similarity_threshold or settings.RETRIEVAL_SIMILARITY_THRESHOLD
        enable_reranking = enable_reranking if enable_reranking is not None else settings.RERANKING_ENABLED

        try:
            # Generate embedding for the query
            embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = embeddings[0]

            # Get embedding dimensions
            embedding_dimensions = len(query_embedding)

            # Use admin client to bypass RLS - function enforces user_id filtering
            supabase = get_supabase_admin()

            # Determine retrieval count (more if reranking to allow better filtering)
            # Add bounds checking to prevent excessive database queries
            retrieval_count = limit * settings.RERANKING_RETRIEVAL_MULTIPLIER if enable_reranking else limit
            MAX_RETRIEVAL_COUNT = 100  # Maximum to prevent performance issues
            retrieval_count = min(retrieval_count, MAX_RETRIEVAL_COUNT)

            # Choose retrieval method: hybrid vs vector-only
            if settings.HYBRID_SEARCH_ENABLED:
                # Use hybrid search (vector + keyword with RRF)
                response = supabase.rpc(
                    'hybrid_search_chunks',
                    {
                        'query_text': query,
                        'query_embedding': query_embedding,
                        'user_id_filter': user_id,
                        'match_count': retrieval_count,
                        'vector_weight': settings.HYBRID_VECTOR_WEIGHT,
                        'keyword_weight': settings.HYBRID_KEYWORD_WEIGHT,
                        'dimension_filter': embedding_dimensions,
                        'similarity_threshold': similarity_threshold
                    }
                ).execute()
            else:
                # Fallback to vector-only search (backward compatibility)
                response = supabase.rpc(
                    'match_chunks_v2',
                    {
                        'query_embedding': query_embedding,
                        'match_threshold': similarity_threshold,
                        'match_count': retrieval_count,
                        'user_id_filter': user_id,
                        'dimension_filter': embedding_dimensions
                    }
                ).execute()

            chunks = response.data if response.data else []

            # If no chunks, return empty list
            if not chunks:
                return []

            # Rerank chunks if enabled
            if enable_reranking and chunks:
                # Prepare documents for reranking
                rerank_docs = [
                    RerankDocument(id=chunk['id'], text=chunk['content'])
                    for chunk in chunks
                ]

                # Call reranking service
                rerank_request = RerankRequest(
                    query=query,
                    documents=rerank_docs,
                    top_n=min(limit, len(chunks))
                )

                rerank_response = reranking_service.rerank(
                    request=rerank_request,
                    provider=settings.RERANKING_PROVIDER
                )

                # Create mapping of chunk_id -> rerank_score
                rerank_scores = {
                    result.id: result.relevance_score
                    for result in rerank_response.results
                }

                # Filter and reorder chunks by rerank results
                reranked_chunk_ids = [result.id for result in rerank_response.results]
                chunks = [
                    chunk for chunk in chunks
                    if chunk['id'] in reranked_chunk_ids
                ]
                # Sort by rerank order
                chunks.sort(key=lambda c: reranked_chunk_ids.index(c['id']))

                # Add rerank scores to chunks
                for chunk in chunks:
                    chunk['rerank_score'] = rerank_scores.get(chunk['id'])

            # Fetch document names for each chunk
            document_ids = list(set(chunk['document_id'] for chunk in chunks))
            docs_response = supabase.table("documents").select("id, filename").in_("id", document_ids).execute()

            # Create a mapping of document_id -> filename
            doc_map = {doc['id']: doc['filename'] for doc in docs_response.data}

            # Enrich chunks with document names
            enriched_chunks = []
            for chunk in chunks:
                enriched_chunk = {
                    "id": chunk['id'],
                    "content": chunk['content'],
                    "document_id": chunk['document_id'],
                    "document_name": doc_map.get(chunk['document_id'], "Unknown"),
                    "similarity": chunk.get('similarity', 0.0)
                }

                # Add hybrid search scores if available
                if 'keyword_rank' in chunk:
                    enriched_chunk['keyword_rank'] = chunk['keyword_rank']
                if 'hybrid_score' in chunk:
                    enriched_chunk['hybrid_score'] = chunk['hybrid_score']

                # Add rerank score if available
                if 'rerank_score' in chunk:
                    enriched_chunk['rerank_score'] = chunk['rerank_score']

                enriched_chunks.append(enriched_chunk)

            return enriched_chunks

        except Exception as e:
            raise Exception(f"Failed to retrieve relevant chunks: {str(e)}")


retrieval_service = RetrievalService()
