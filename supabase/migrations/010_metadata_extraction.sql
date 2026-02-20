-- Migration 010: Metadata Extraction
-- Add LLM-extracted metadata columns to documents table

-- Add metadata columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS key_topics TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata_status TEXT DEFAULT 'pending'
  CHECK (metadata_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

-- Create indexes for future filtering
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type)
  WHERE document_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_key_topics ON documents USING GIN(key_topics)
  WHERE key_topics IS NOT NULL AND array_length(key_topics, 1) > 0;
CREATE INDEX IF NOT EXISTS idx_documents_metadata_status ON documents(metadata_status);

-- Comments
COMMENT ON COLUMN documents.summary IS 'LLM-extracted 2-3 sentence summary';
COMMENT ON COLUMN documents.document_type IS 'Document type (article, report, guide, etc.)';
COMMENT ON COLUMN documents.key_topics IS 'Array of main topics/themes (3-5 items)';
COMMENT ON COLUMN documents.metadata_status IS 'Metadata extraction status - independent from document status';
