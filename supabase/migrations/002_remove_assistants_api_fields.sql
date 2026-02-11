-- Remove Assistants API specific fields

-- Drop openai_thread_id column from threads table
ALTER TABLE threads DROP COLUMN IF EXISTS openai_thread_id;

-- openai_message_id in messages table is already nullable and unused
-- We can optionally use it to store response_id from Responses API
-- No changes needed for now
