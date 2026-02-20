-- ============================================================
-- Rollback: Revert all 13 migrations to a clean slate
-- Run this in the Supabase SQL Editor before re-running migrations
-- ============================================================

-- ----------------------------------------
-- Drop all tables
-- CASCADE handles indexes, triggers, RLS policies, and FK constraints
-- ----------------------------------------
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS threads;

-- ----------------------------------------
-- Drop all functions
-- ----------------------------------------
DROP FUNCTION IF EXISTS execute_books_query(TEXT);
DROP FUNCTION IF EXISTS hybrid_search_chunks(TEXT, VECTOR, UUID, INT, REAL, REAL, INT, REAL);
DROP FUNCTION IF EXISTS keyword_search_chunks(TEXT, UUID, INT);
DROP FUNCTION IF EXISTS chunks_content_tsv_trigger();
DROP FUNCTION IF EXISTS match_chunks_v2(VECTOR, FLOAT, INT, UUID, INT);
DROP FUNCTION IF EXISTS match_chunks(VECTOR, FLOAT, INT, UUID);
DROP FUNCTION IF EXISTS update_documents_updated_at();

-- ----------------------------------------
-- Drop sql_query_role
-- Revoke only the USAGE grant from 012_sql_tool.sql before dropping
-- ----------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'sql_query_role') THEN
        REVOKE USAGE ON SCHEMA public FROM sql_query_role;
        DROP ROLE sql_query_role;
    END IF;
END $$;

-- ----------------------------------------
-- Drop pgvector extension
-- Safe now that all tables using the vector type are dropped
-- ----------------------------------------
DROP EXTENSION IF EXISTS vector;
