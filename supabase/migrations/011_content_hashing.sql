-- Migration 011: Content Hashing for Deduplication
-- Add SHA-256 hash columns and duplicate tracking to documents table

-- Add hash columns to documents table
ALTER TABLE documents
  ADD COLUMN file_content_hash TEXT,
  ADD COLUMN text_content_hash TEXT,
  ADD COLUMN duplicate_of UUID REFERENCES documents(id) ON DELETE SET NULL;

-- Update status constraint to include 'duplicate'
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_status_check;
ALTER TABLE documents ADD CONSTRAINT documents_status_check
  CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'duplicate'));

-- Create partial indexes for fast hash lookups
CREATE INDEX idx_documents_text_hash ON documents(user_id, text_content_hash)
  WHERE text_content_hash IS NOT NULL;

CREATE INDEX idx_documents_file_hash ON documents(user_id, file_content_hash)
  WHERE file_content_hash IS NOT NULL;

-- Add helpful comments
COMMENT ON COLUMN documents.file_content_hash IS 'SHA-256 hash of raw file bytes';
COMMENT ON COLUMN documents.text_content_hash IS 'SHA-256 hash of extracted text content';
COMMENT ON COLUMN documents.duplicate_of IS 'References original document if duplicate detected';
