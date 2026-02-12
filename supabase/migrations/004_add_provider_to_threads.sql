-- Add provider configuration columns to threads table
ALTER TABLE threads
ADD COLUMN provider TEXT,
ADD COLUMN model TEXT,
ADD COLUMN base_url TEXT;

-- Add comment explaining the columns
COMMENT ON COLUMN threads.provider IS 'LLM provider identifier (e.g., openai, openrouter, ollama)';
COMMENT ON COLUMN threads.model IS 'Model name for the provider';
COMMENT ON COLUMN threads.base_url IS 'Custom base URL for the provider API';
