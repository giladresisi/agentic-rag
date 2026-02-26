-- Migration: Replace production_incidents with deployments (change management log) for IR-Copilot demo.
-- Eliminates tool-routing ambiguity: retrieve_documents → postmortem narrative; query_deployments_database → deployment facts.

-- Part 1: Drop old artifacts
DROP TABLE IF EXISTS books CASCADE;
DROP FUNCTION IF EXISTS execute_books_query(TEXT);
DROP TABLE IF EXISTS production_incidents CASCADE;
DROP FUNCTION IF EXISTS execute_incidents_query(TEXT);

-- Part 2: Create deployments table
CREATE TABLE IF NOT EXISTS deployments (
    id                 SERIAL PRIMARY KEY,
    deploy_id          TEXT UNIQUE NOT NULL,
    service            TEXT NOT NULL,
    version            TEXT NOT NULL,
    environment        TEXT NOT NULL CHECK (environment IN ('production','staging','canary')),
    deployed_by        TEXT NOT NULL,
    team               TEXT NOT NULL,
    deploy_type        TEXT NOT NULL CHECK (deploy_type IN ('feature','hotfix','rollback','config','migration')),
    status             TEXT NOT NULL CHECK (status IN ('success','failed','rolled_back')),
    started_at         TIMESTAMPTZ NOT NULL,
    completed_at       TIMESTAMPTZ,
    duration_seconds   INTEGER,
    triggered_incident BOOLEAN DEFAULT FALSE,
    rollback_of        TEXT,
    notes              TEXT
);

-- Part 3: Seed 15 deployments
-- Services match postmortem docs; some rows correlate with incidents to enable cross-tool queries
INSERT INTO deployments
    (deploy_id, service, version, environment, deployed_by, team, deploy_type, status,
     started_at, completed_at, duration_seconds, triggered_incident, rollback_of, notes)
VALUES
    ('DEP-2024-001', 'auth-service',         'v2.13.0', 'production', 'alice.chen',   'backend',  'feature',   'success',     '2024-01-14 10:00:00+00', '2024-01-14 10:14:00+00', 840,  FALSE, NULL,           'SSO improvements and session management hardening'),
    ('DEP-2024-002', 'auth-service',         'v2.13.1', 'production', 'bob.kim',      'backend',  'config',    'success',     '2024-01-15 02:00:00+00', '2024-01-15 02:08:00+00', 480,  TRUE,  NULL,           'Redis TTL config change — caused INC-2024-003'),
    ('DEP-2024-003', 'auth-service',         'v2.13.0', 'production', 'alice.chen',   'backend',  'rollback',  'success',     '2024-01-15 03:05:00+00', '2024-01-15 03:12:00+00', 420,  FALSE, 'DEP-2024-002', 'Emergency rollback after INC-2024-003'),
    ('DEP-2024-004', 'payment-api',          'v4.1.5',  'production', 'carol.james',  'backend',  'feature',   'success',     '2024-02-05 08:00:00+00', '2024-02-05 08:22:00+00', 1320, FALSE, NULL,           'Apple Pay integration and checkout UX improvements'),
    ('DEP-2024-005', 'payment-api',          'v4.1.6',  'production', 'david.park',   'data',     'migration', 'failed',      '2024-02-08 09:00:00+00', '2024-02-08 09:18:00+00', 1080, TRUE,  NULL,           'Schema migration caused INC-2024-011 index corruption'),
    ('DEP-2024-006', 'payment-api',          'v4.1.5',  'production', 'carol.james',  'backend',  'rollback',  'success',     '2024-02-08 11:40:00+00', '2024-02-08 11:52:00+00', 720,  FALSE, 'DEP-2024-005', 'DB rollback after INC-2024-011'),
    ('DEP-2024-007', 'data-pipeline',        'v2.3.0',  'production', 'eve.nguyen',   'data',     'feature',   'success',     '2024-03-20 14:00:00+00', '2024-03-20 14:30:00+00', 1800, FALSE, NULL,           'PDF ingestion support added'),
    ('DEP-2024-008', 'data-pipeline',        'v2.3.1',  'production', 'eve.nguyen',   'data',     'hotfix',    'success',     '2024-03-22 08:00:00+00', '2024-03-22 08:25:00+00', 1500, FALSE, NULL,           'Memory leak fix in async task pool'),
    ('DEP-2024-009', 'api-gateway',          'v1.9.0',  'production', 'frank.liu',    'platform', 'feature',   'success',     '2024-05-01 09:00:00+00', '2024-05-01 09:20:00+00', 1200, FALSE, NULL,           'Rate limiting enhancements and circuit breaker improvements'),
    ('DEP-2024-010', 'api-gateway',          'v1.9.1',  'production', 'grace.taylor', 'platform', 'config',    'failed',      '2024-05-03 13:58:00+00', '2024-05-03 14:02:00+00', 240,  TRUE,  NULL,           'TLS cert rotation config — caused INC-2024-027'),
    ('DEP-2024-011', 'api-gateway',          'v1.9.0',  'production', 'frank.liu',    'platform', 'rollback',  'success',     '2024-05-03 14:45:00+00', '2024-05-03 14:52:00+00', 420,  FALSE, 'DEP-2024-010', 'TLS rollback after INC-2024-027'),
    ('DEP-2024-012', 'notification-service', 'v3.0.0',  'production', 'henry.smith',  'backend',  'feature',   'success',     '2024-06-09 11:00:00+00', '2024-06-09 11:35:00+00', 2100, FALSE, NULL,           'Email template engine upgrade to SendGrid v3'),
    ('DEP-2024-013', 'payment-api',          'v4.2.0',  'production', 'carol.james',  'backend',  'feature',   'success',     '2024-07-02 11:00:00+00', '2024-07-02 11:15:00+00', 900,  TRUE,  NULL,           'PDF receipts feature — nil pointer caused INC-2024-038'),
    ('DEP-2024-014', 'payment-api',          'v4.1.9',  'production', 'david.park',   'backend',  'rollback',  'rolled_back', '2024-07-02 11:20:00+00', '2024-07-02 11:30:00+00', 600,  FALSE, 'DEP-2024-013', 'Rollback failed — DB migration incompatible with v4.1.9'),
    ('DEP-2024-015', 'payment-api',          'v4.2.1',  'production', 'carol.james',  'backend',  'hotfix',    'success',     '2024-07-02 11:35:00+00', '2024-07-02 11:45:00+00', 600,  FALSE, NULL,           'Forward-fix: made DB column optional to unblock payments');

-- Part 4: Permissions — sql_query_role can only read deployments
GRANT SELECT ON deployments TO sql_query_role;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON deployments FROM sql_query_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM sql_query_role;

-- Part 5: Enable RLS on deployments (project policy: all tables need RLS)
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read all deployments (shared reference data)
CREATE POLICY "authenticated_read_deployments" ON deployments
    FOR SELECT TO authenticated USING (true);

-- sql_query_role needs an explicit policy to see rows when RLS is enabled
CREATE POLICY "sql_query_role_read_deployments" ON deployments
    FOR SELECT TO sql_query_role USING (true);

-- Part 6: RPC function for safe SQL execution on deployments table
-- SECURITY DEFINER + fixed search_path prevents schema injection attacks
CREATE OR REPLACE FUNCTION execute_deployments_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    result JSONB;
    normalized TEXT;
BEGIN
    -- Normalize for validation
    normalized := UPPER(TRIM(query_text));

    -- Block semicolons — prevents statement chaining before any other check
    IF POSITION(';' IN query_text) > 0 THEN
        RAISE EXCEPTION 'Semicolons are not allowed in queries';
    END IF;

    -- Validate: must be SELECT only
    IF NOT normalized LIKE 'SELECT%' THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    -- Validate: must reference deployments table
    IF normalized NOT LIKE '%FROM DEPLOYMENTS%' AND normalized NOT LIKE '%FROM "DEPLOYMENTS"%' THEN
        RAISE EXCEPTION 'Only queries on the deployments table are allowed';
    END IF;

    -- Block dangerous operations (expanded: includes COPY, CALL, DO, SET, EXECUTE)
    IF normalized ~ '\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|SET|EXECUTE)\b' THEN
        RAISE EXCEPTION 'Query contains forbidden operations';
    END IF;

    -- Execute and return as JSON array
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || query_text || ') t'
    INTO result;

    RETURN result;
END;
$$;

-- Grant execute to authenticated and service_role only — no anonymous access
GRANT EXECUTE ON FUNCTION execute_deployments_query TO authenticated;
GRANT EXECUTE ON FUNCTION execute_deployments_query TO service_role;

-- Comments
COMMENT ON TABLE deployments IS 'Deployment and change management log for IR-Copilot text-to-SQL tool. Contains 15 realistic deployment records spanning 2024, correlated with postmortem incidents.';
COMMENT ON FUNCTION execute_deployments_query IS 'Safely executes validated SELECT queries against the deployments table. Provides defense-in-depth SQL validation.';
