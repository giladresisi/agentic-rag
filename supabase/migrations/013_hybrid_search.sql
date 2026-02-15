-- Migration: Add hybrid search (vector + keyword) with Reciprocal Rank Fusion (RRF)
-- Combines PostgreSQL full-text search (tsvector/tsquery) with vector similarity search

-- Part 1: Add tsvector column for full-text search
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'chunks' AND column_name = 'content_tsv') THEN
        ALTER TABLE chunks ADD COLUMN content_tsv tsvector;
    END IF;
END $$;

-- Populate content_tsv for existing rows
UPDATE chunks SET content_tsv = to_tsvector('english', content) WHERE content_tsv IS NULL;

-- Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv ON chunks USING gin(content_tsv);

-- Create trigger to auto-update tsvector on insert/update
CREATE OR REPLACE FUNCTION chunks_content_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('english', NEW.content);
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chunks_content_tsv_update ON chunks;
CREATE TRIGGER chunks_content_tsv_update
    BEFORE INSERT OR UPDATE OF content
    ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION chunks_content_tsv_trigger();

-- Part 2: Keyword search RPC function
CREATE OR REPLACE FUNCTION keyword_search_chunks(
    query_text TEXT,
    user_id_filter UUID,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    rank REAL
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
        ts_rank(c.content_tsv, query) AS rank
    -- Note: websearch_to_tsquery safely handles user input by normalizing web-style queries
    -- It's designed for direct user input and provides built-in protection against injection
    FROM chunks c, websearch_to_tsquery('english', query_text) query
    WHERE
        -- RLS enforcement: filter by user_id
        (user_id_filter IS NULL OR c.user_id = user_id_filter)
        -- Full-text search match
        AND c.content_tsv @@ query
    ORDER BY
        rank DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION keyword_search_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION keyword_search_chunks TO anon;

-- Part 3: Hybrid search RPC function with Reciprocal Rank Fusion (RRF)
CREATE OR REPLACE FUNCTION hybrid_search_chunks(
    query_text TEXT,
    query_embedding VECTOR,
    user_id_filter UUID,
    match_count INT DEFAULT 10,
    vector_weight REAL DEFAULT 0.5,
    keyword_weight REAL DEFAULT 0.5,
    dimension_filter INT DEFAULT NULL,
    similarity_threshold REAL DEFAULT 0.0
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    chunk_index INTEGER,
    metadata JSONB,
    similarity FLOAT,
    keyword_rank REAL,
    hybrid_score FLOAT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    rrf_k CONSTANT REAL := 60; -- RRF constant
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.metadata,
            (1 - (c.embedding <=> query_embedding)) AS similarity,
            ROW_NUMBER() OVER (ORDER BY (1 - (c.embedding <=> query_embedding)) DESC) AS rank
        FROM chunks c
        WHERE
            -- Filter by embedding dimensions if specified
            (dimension_filter IS NULL OR c.embedding_dimensions = dimension_filter)
            -- RLS enforcement: filter by user_id
            AND (user_id_filter IS NULL OR c.user_id = user_id_filter)
            -- Filter by similarity threshold
            AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY similarity DESC
        LIMIT match_count * 3 -- Retrieve more for fusion
    ),
    keyword_search AS (
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.metadata,
            ts_rank(c.content_tsv, query) AS keyword_rank,
            ROW_NUMBER() OVER (ORDER BY ts_rank(c.content_tsv, query) DESC) AS rank
        -- Note: websearch_to_tsquery safely handles user input (see keyword_search_chunks comment)
        FROM chunks c, websearch_to_tsquery('english', query_text) query
        WHERE
            -- RLS enforcement: filter by user_id
            (user_id_filter IS NULL OR c.user_id = user_id_filter)
            -- Full-text search match
            AND c.content_tsv @@ query
        ORDER BY keyword_rank DESC
        LIMIT match_count * 3 -- Retrieve more for fusion
    ),
    rrf_fusion AS (
        SELECT
            COALESCE(v.id, k.id) AS id,
            COALESCE(v.document_id, k.document_id) AS document_id,
            COALESCE(v.content, k.content) AS content,
            COALESCE(v.chunk_index, k.chunk_index) AS chunk_index,
            COALESCE(v.metadata, k.metadata) AS metadata,
            COALESCE(v.similarity, 0.0) AS similarity,
            COALESCE(k.keyword_rank, 0.0) AS keyword_rank,
            (
                COALESCE(vector_weight / (rrf_k + COALESCE(v.rank, 999999)), 0.0) +
                COALESCE(keyword_weight / (rrf_k + COALESCE(k.rank, 999999)), 0.0)
            ) AS hybrid_score
        FROM vector_search v
        FULL OUTER JOIN keyword_search k ON v.id = k.id
    )
    SELECT
        f.id,
        f.document_id,
        f.content,
        f.chunk_index,
        f.metadata,
        f.similarity,
        f.keyword_rank,
        f.hybrid_score
    FROM rrf_fusion f
    ORDER BY f.hybrid_score DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION hybrid_search_chunks TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_chunks TO anon;

-- Add helpful comments
COMMENT ON COLUMN chunks.content_tsv IS 'Full-text search vector for keyword matching. Auto-updated via trigger when content changes.';
COMMENT ON FUNCTION keyword_search_chunks IS 'Full-text search on chunk content using PostgreSQL tsvector/tsquery. Returns chunks ranked by text relevance.';
COMMENT ON FUNCTION hybrid_search_chunks IS 'Hybrid search combining vector similarity and keyword matching via Reciprocal Rank Fusion (RRF). Returns unified ranked results.';
