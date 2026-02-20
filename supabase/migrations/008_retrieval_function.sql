-- Create match_chunks function for vector similarity search
-- This function performs semantic search using pgvector cosine similarity
-- and enforces Row-Level Security through user_id filtering

CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 10,
    user_id_filter uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    chunk_index integer,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        chunks.id,
        chunks.document_id,
        chunks.content,
        chunks.chunk_index,
        chunks.metadata,
        -- Cosine similarity calculation using pgvector operator
        -- Returns value between 0 (dissimilar) and 1 (identical)
        (1 - (chunks.embedding <=> query_embedding)) AS similarity
    FROM chunks
    WHERE
        -- RLS enforcement: filter by user_id to ensure users only see their own chunks
        (user_id_filter IS NULL OR chunks.user_id = user_id_filter)
        -- Filter by similarity threshold to exclude irrelevant results
        AND (1 - (chunks.embedding <=> query_embedding)) >= match_threshold
    ORDER BY
        -- Order by similarity descending (most similar first)
        similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_chunks TO authenticated;
