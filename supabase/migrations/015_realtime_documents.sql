-- Enable Supabase Realtime for the documents table.
--
-- Without this, Postgres Changes subscriptions on the documents table
-- emit no events, so the frontend never receives status updates
-- (e.g., processing → completed) and the UI stays stuck.
--
-- REPLICA IDENTITY FULL is required for RLS-enabled tables so that
-- Realtime includes the full row in UPDATE payloads (needed to match
-- the row against the user's RLS policy before broadcasting).

ALTER TABLE documents REPLICA IDENTITY FULL;

ALTER PUBLICATION supabase_realtime ADD TABLE documents;
