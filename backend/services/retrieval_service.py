from typing import List, Dict
from config import settings
from services.embedding_service import embedding_service
from services.supabase_service import get_supabase_admin


class RetrievalService:
    """Service for retrieving relevant document chunks using vector similarity search."""

    @staticmethod
    async def retrieve_relevant_chunks(
        query: str,
        user_id: str,
        limit: int = None,
        similarity_threshold: float = None
    ) -> List[Dict]:
        """Retrieve relevant document chunks for a given query.

        Args:
            query: The search query text
            user_id: User ID for RLS filtering
            limit: Maximum number of chunks to retrieve (default from config)
            similarity_threshold: Minimum similarity score 0-1 (default from config)

        Returns:
            List of dictionaries containing chunk data and metadata:
            [
                {
                    "id": "uuid",
                    "content": "chunk text",
                    "document_id": "uuid",
                    "document_name": "file.pdf",
                    "similarity": 0.85
                },
                ...
            ]

        Raises:
            Exception: If retrieval fails
        """
        # Use config defaults if not provided
        limit = limit or settings.RETRIEVAL_LIMIT
        similarity_threshold = similarity_threshold or settings.RETRIEVAL_SIMILARITY_THRESHOLD

        try:
            # Generate embedding for the query
            embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = embeddings[0]

            # Get embedding dimensions
            embedding_dimensions = len(query_embedding)

            # Call match_chunks_v2 RPC function via Supabase
            # Use admin client to bypass RLS - function enforces user_id filtering
            supabase = get_supabase_admin()

            response = supabase.rpc(
                'match_chunks_v2',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': similarity_threshold,
                    'match_count': limit,
                    'user_id_filter': user_id,
                    'dimension_filter': embedding_dimensions
                }
            ).execute()

            chunks = response.data if response.data else []

            # If no chunks, return empty list
            if not chunks:
                return []

            # Fetch document names for each chunk
            document_ids = list(set(chunk['document_id'] for chunk in chunks))
            docs_response = supabase.table("documents").select("id, filename").in_("id", document_ids).execute()

            # Create a mapping of document_id -> filename
            doc_map = {doc['id']: doc['filename'] for doc in docs_response.data}

            # Enrich chunks with document names
            enriched_chunks = []
            for chunk in chunks:
                enriched_chunks.append({
                    "id": chunk['id'],
                    "content": chunk['content'],
                    "document_id": chunk['document_id'],
                    "document_name": doc_map.get(chunk['document_id'], "Unknown"),
                    "similarity": chunk['similarity']
                })

            return enriched_chunks

        except Exception as e:
            raise Exception(f"Failed to retrieve relevant chunks: {str(e)}")


retrieval_service = RetrievalService()
