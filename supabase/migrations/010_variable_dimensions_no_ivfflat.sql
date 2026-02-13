-- Migration: Support variable embedding dimensions without ivfflat indexes
-- Trade-off: More flexible (any dimension) but slower similarity search (no specialized indexes)

-- Part 1: Add embedding_dimensions columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'documents' AND column_name = 'embedding_dimensions') THEN
        ALTER TABLE documents ADD COLUMN embedding_dimensions INTEGER NOT NULL DEFAULT 1536;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'chunks' AND column_name = 'embedding_dimensions') THEN
        ALTER TABLE chunks ADD COLUMN embedding_dimensions INTEGER NOT NULL DEFAULT 1536;
    END IF;
END $$;

-- Create index on embedding_dimensions for filtering
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_dimensions ON chunks(embedding_dimensions);

-- Part 2: Convert embedding column to variable dimensions

-- Drop any existing indexes
DROP INDEX IF EXISTS idx_chunks_embedding;
DROP INDEX IF EXISTS idx_chunks_embedding_1536;
DROP INDEX IF EXISTS idx_chunks_embedding_3072;

-- Check current embedding column type
DO $$
DECLARE
    current_type TEXT;
BEGIN
    SELECT data_type INTO current_type
    FROM information_schema.columns
    WHERE table_name = 'chunks' AND column_name = 'embedding';

    RAISE NOTICE 'Current embedding column type: %', current_type;
END $$;

-- Convert to variable-dimension vector
-- Add temporary column
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_temp vector;

-- Copy existing embeddings (if any)
UPDATE chunks SET embedding_temp = embedding::vector WHERE embedding IS NOT NULL;

-- Drop old column
ALTER TABLE chunks DROP COLUMN embedding;

-- Rename temp column
ALTER TABLE chunks RENAME COLUMN embedding_temp TO embedding;

-- Set NOT NULL constraint
ALTER TABLE chunks ALTER COLUMN embedding SET NOT NULL;

-- Part 3: Update match_chunks_v2 function to work without ivfflat
-- Note: Without ivfflat index, this will use sequential scan - slower but works with any dimension

CREATE OR REPLACE FUNCTION match_chunks_v2(
    query_embedding vector,
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 10,
    user_id_filter uuid DEFAULT NULL,
    dimension_filter int DEFAULT NULL
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
        -- Filter by embedding dimensions if specified (important for accuracy)
        (dimension_filter IS NULL OR c.embedding_dimensions = dimension_filter)
        -- RLS enforcement: filter by user_id
        AND (user_id_filter IS NULL OR c.user_id = user_id_filter)
        -- Filter by similarity threshold
        AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
    ORDER BY
        similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION match_chunks_v2 TO authenticated;
GRANT EXECUTE ON FUNCTION match_chunks_v2 TO anon;

-- Add helpful comments
COMMENT ON COLUMN chunks.embedding IS 'Variable-dimension embedding vector. No ivfflat index - uses sequential scan for similarity search. Actual dimension stored in embedding_dimensions column.';
COMMENT ON COLUMN chunks.embedding_dimensions IS 'Dimension of the embedding vector (e.g., 1536, 3072, 768). Must match query dimension for accurate similarity search.';
COMMENT ON FUNCTION match_chunks_v2 IS 'Similarity search supporting variable dimensions. No ivfflat index - uses sequential scan. Filter by dimension_filter for accuracy.';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ Migration complete: chunks.embedding now supports variable dimensions';
    RAISE NOTICE '✓ match_chunks_v2 updated to handle any dimension';
    RAISE NOTICE '⚠ Note: No ivfflat index - similarity search will be slower but more flexible';
END $$;
