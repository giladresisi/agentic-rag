-- Migration 015: Sub-Agent Metadata Support
-- Add JSONB column to messages table for storing sub-agent execution metadata

-- Add subagent_metadata column to messages table (nullable for backward compatibility)
ALTER TABLE messages ADD COLUMN IF NOT EXISTS subagent_metadata JSONB;

-- Comment explaining the field structure and purpose
COMMENT ON COLUMN messages.subagent_metadata IS 'Sub-agent execution metadata. Schema: {task_description: text, document_id: uuid, document_name: text, status: text, reasoning_steps: text[], result: text, error: text, depth: int}';
