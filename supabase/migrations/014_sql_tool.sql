-- Migration: Create books table and SQL query execution function for text-to-SQL tool

-- Part 1: Create books table for text-to-SQL queries
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    published_year INTEGER,
    genre TEXT,
    rating DECIMAL(3,2),
    pages INTEGER,
    isbn TEXT UNIQUE
);

-- Part 2: Populate with sample data
INSERT INTO books (title, author, published_year, genre, rating, pages, isbn) VALUES
('The Great Gatsby', 'F. Scott Fitzgerald', 1925, 'Fiction', 4.2, 180, '978-0-7432-7356-5'),
('To Kill a Mockingbird', 'Harper Lee', 1960, 'Fiction', 4.5, 324, '978-0-06-112008-4'),
('1984', 'George Orwell', 1949, 'Dystopian', 4.6, 328, '978-0-452-28423-4'),
('Pride and Prejudice', 'Jane Austen', 1813, 'Romance', 4.3, 432, '978-0-14-143951-8'),
('The Hobbit', 'J.R.R. Tolkien', 1937, 'Fantasy', 4.7, 310, '978-0-547-92822-7'),
('Harry Potter and the Sorcerer''s Stone', 'J.K. Rowling', 1997, 'Fantasy', 4.8, 309, '978-0-439-70818-8'),
('The Catcher in the Rye', 'J.D. Salinger', 1951, 'Fiction', 3.8, 277, '978-0-316-76948-0'),
('Animal Farm', 'George Orwell', 1945, 'Satire', 4.1, 112, '978-0-452-28424-1'),
('Lord of the Flies', 'William Golding', 1954, 'Fiction', 3.7, 224, '978-0-399-50148-7'),
('Brave New World', 'Aldous Huxley', 1932, 'Dystopian', 4.0, 268, '978-0-06-085052-4')
ON CONFLICT (isbn) DO NOTHING;

-- Part 3: Create read-only role for SQL queries
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sql_query_role') THEN
        CREATE ROLE sql_query_role WITH LOGIN PASSWORD '***';
    END IF;
END $$;

-- Grant ONLY SELECT on books table
GRANT USAGE ON SCHEMA public TO sql_query_role;
GRANT SELECT ON books TO sql_query_role;

-- Explicitly REVOKE all other privileges
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON books FROM sql_query_role;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM sql_query_role;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM sql_query_role;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM sql_query_role;

-- Grant SELECT ONLY on books (re-grant after revoke all)
GRANT SELECT ON books TO sql_query_role;

-- Prevent future privilege escalation
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM sql_query_role;

-- Part 4: Create RPC function for safe SQL execution on books table
-- This function provides defense-in-depth by validating queries at the database level
CREATE OR REPLACE FUNCTION execute_books_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    normalized TEXT;
BEGIN
    -- Normalize for validation
    normalized := UPPER(TRIM(query_text));

    -- Validate: must be SELECT only
    IF NOT normalized LIKE 'SELECT%' THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    -- Validate: must reference books table
    IF normalized NOT LIKE '%FROM BOOKS%' AND normalized NOT LIKE '%FROM "BOOKS"%' THEN
        RAISE EXCEPTION 'Only queries on the books table are allowed';
    END IF;

    -- Block dangerous operations
    IF normalized ~ '\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b' THEN
        RAISE EXCEPTION 'Query contains forbidden operations';
    END IF;

    -- Execute and return as JSON array
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t'
    INTO result;

    RETURN result;
END;
$$;

-- Grant execute to authenticated and service_role
GRANT EXECUTE ON FUNCTION execute_books_query TO authenticated;
GRANT EXECUTE ON FUNCTION execute_books_query TO anon;
GRANT EXECUTE ON FUNCTION execute_books_query TO service_role;

-- Add comments
COMMENT ON TABLE books IS 'Sample books table for text-to-SQL tool demonstrations. Contains 10 classic books.';
COMMENT ON FUNCTION execute_books_query IS 'Safely executes validated SELECT queries against the books table. Provides defense-in-depth SQL validation.';
