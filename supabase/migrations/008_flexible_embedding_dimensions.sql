-- Migration: Add flexible embedding dimensions support
-- Allows storing embeddings with different vector dimensions (e.g., 1536 for text-embedding-3-small, 3072 for text-embedding-3-large)

-- Add embedding_dimensions column to documents table
ALTER TABLE documents ADD COLUMN embedding_dimensions INTEGER NOT NULL DEFAULT 1536;

-- Add embedding_dimensions column to chunks table
ALTER TABLE chunks ADD COLUMN embedding_dimensions INTEGER NOT NULL DEFAULT 1536;

-- Create index on chunks.embedding_dimensions for efficient filtering
CREATE INDEX idx_chunks_embedding_dimensions ON chunks(embedding_dimensions);

-- Mark original match_chunks as deprecated (kept for backward compatibility)
COMMENT ON FUNCTION match_chunks IS 'DEPRECATED: Use match_chunks_v2 which supports dimension filtering. This function does not filter by embedding dimensions and may return incorrect results when chunks with mixed dimensions exist.';

-- Create match_chunks_v2 function with dimension_filter parameter
CREATE OR REPLACE FUNCTION match_chunks_v2(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 10,
    user_id_filter uuid DEFAULT NULL,
    dimension_filter int DEFAULT 1536
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
        c.id,
        c.document_id,
        c.content,
        c.chunk_index,
        c.metadata,
        (1 - (c.embedding <=> query_embedding)) AS similarity
    FROM chunks c
    WHERE
        -- Filter by embedding dimensions to avoid mixing different vector sizes
        c.embedding_dimensions = dimension_filter
        -- RLS enforcement: filter by user_id
        AND (user_id_filter IS NULL OR c.user_id = user_id_filter)
        -- Filter by similarity threshold
        AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
    ORDER BY
        similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_chunks_v2 TO authenticated;

-- Rollback instructions:
-- DROP FUNCTION IF EXISTS match_chunks_v2;
-- ALTER TABLE chunks DROP COLUMN IF EXISTS embedding_dimensions;
-- ALTER TABLE documents DROP COLUMN IF EXISTS embedding_dimensions;
-- COMMENT ON FUNCTION match_chunks IS NULL;
