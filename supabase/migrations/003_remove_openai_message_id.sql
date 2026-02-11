-- Remove remaining Assistants API field from messages table
ALTER TABLE messages DROP COLUMN IF EXISTS openai_message_id;
