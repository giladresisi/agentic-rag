-- Migration: Replace books table with production_incidents for IR-Copilot demo

-- Part 1: Drop old artifacts
DROP TABLE IF EXISTS books CASCADE;
DROP FUNCTION IF EXISTS execute_books_query(TEXT);

-- Part 2: Create production_incidents table
CREATE TABLE IF NOT EXISTS production_incidents (
    id SERIAL PRIMARY KEY,
    incident_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('P1','P2','P3','P4')),
    service_affected TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'resolved' CHECK (status IN ('resolved','open','monitoring')),
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    duration_minutes INTEGER,
    root_cause_category TEXT CHECK (root_cause_category IN ('database','deployment','network','third-party','configuration')),
    description TEXT,
    postmortem_written BOOLEAN DEFAULT FALSE
);

-- Part 3: Seed 15 incidents
-- Severity spread: 3x P1, 4x P2, 5x P3, 3x P4
-- Services: auth-service(3), payment-api(4), data-pipeline(3), api-gateway(3), notification-service(2)
-- Status: 12 resolved, 2 monitoring, 1 open
-- Root causes: database(4), deployment(3), network(3), third-party(3), configuration(2)
-- postmortem_written=TRUE for INC-2024-003, -011, -019, -027, -031, -038

INSERT INTO production_incidents
    (incident_id, title, severity, service_affected, status, started_at, resolved_at, duration_minutes, root_cause_category, description, postmortem_written)
VALUES
    -- P1 incidents (3)
    ('INC-2024-003', 'Auth service JWT validation timeout cascade', 'P1', 'auth-service', 'resolved',
     '2024-01-15 02:14:00+00', '2024-01-15 03:01:00+00', 47,
     'database', 'Redis TTL misconfiguration caused token cache misses; all validation requests hit Postgres directly, exhausting connection pool.', TRUE),

    ('INC-2024-011', 'Payment DB B-tree index corruption', 'P1', 'payment-api', 'resolved',
     '2024-02-08 09:22:00+00', '2024-02-08 11:34:00+00', 132,
     'database', 'PostgreSQL 14.1 bug with partial page writes caused B-tree index corruption after unclean replica shutdown; payment writes rejected.', TRUE),

    ('INC-2024-027', 'API Gateway TLS handshake failures - 504 cascade', 'P1', 'api-gateway', 'resolved',
     '2024-05-03 14:05:00+00', '2024-05-03 14:43:00+00', 38,
     'network', 'Expired intermediate certificate on load balancer caused upstream TLS handshake failures; all API routes returning 504.', TRUE),

    -- P2 incidents (4)
    ('INC-2024-019', 'Data pipeline OOM crash loop - 6h batch delay', 'P2', 'data-pipeline', 'resolved',
     '2024-03-22 00:10:00+00', '2024-03-22 06:28:00+00', 378,
     'deployment', 'asyncio Task objects held in unbounded list caused OOM; pipeline workers crash-looped, delaying nightly batch by 6 hours.', TRUE),

    ('INC-2024-031', 'RabbitMQ queue saturation - notification delivery delay', 'P2', 'notification-service', 'resolved',
     '2024-06-11 10:30:00+00', '2024-06-11 14:47:00+00', 257,
     'configuration', 'Consumer group scaled down during maintenance window; queue depth alarm threshold too high to catch saturation early.', TRUE),

    ('INC-2024-044', 'Payment API latency spike - third-party processor degraded', 'P2', 'payment-api', 'monitoring',
     '2024-08-19 16:40:00+00', NULL, NULL,
     'third-party', 'Stripe payment processor experiencing elevated latency in eu-west-1; p99 payment checkout latency exceeded 8s SLA.', FALSE),

    ('INC-2024-052', 'Auth service login failures - LDAP sync timeout', 'P2', 'auth-service', 'resolved',
     '2024-09-04 07:15:00+00', '2024-09-04 09:53:00+00', 158,
     'third-party', 'Corporate LDAP provider unreachable during scheduled maintenance window; SSO login failures for enterprise users.', FALSE),

    -- P3 incidents (5)
    ('INC-2024-038', 'Nil pointer panic in payment-api deployment - 503s', 'P3', 'payment-api', 'resolved',
     '2024-07-02 11:18:00+00', '2024-07-02 11:40:00+00', 22,
     'deployment', 'Missing nil check on optional config field introduced in v2.14.1; canary deployment not enabled, full rollout triggered panic.', TRUE),

    ('INC-2024-007', 'Data pipeline Kafka consumer group lag accumulation', 'P3', 'data-pipeline', 'resolved',
     '2024-01-29 20:00:00+00', '2024-01-30 00:30:00+00', 270,
     'configuration', 'Consumer group rebalance triggered by rolling restart caused lag spike; no alerting on consumer group lag metric.', FALSE),

    ('INC-2024-023', 'API Gateway rate limiter misconfiguration after deploy', 'P3', 'api-gateway', 'resolved',
     '2024-04-17 13:00:00+00', '2024-04-17 17:15:00+00', 255,
     'deployment', 'Rate limiter config file had wrong burst value after automated deploy; legitimate traffic throttled for 4 hours.', FALSE),

    ('INC-2024-047', 'Notification service email template rendering failure', 'P3', 'notification-service', 'resolved',
     '2024-08-28 09:00:00+00', '2024-08-28 11:30:00+00', 150,
     'third-party', 'SendGrid template API returned deprecated field names after their v3 migration; email rendering failed for all transactional emails.', FALSE),

    ('INC-2024-059', 'Auth service session invalidation cache drift', 'P3', 'auth-service', 'monitoring',
     '2024-10-14 15:30:00+00', NULL, NULL,
     'database', 'Redis cluster shard rebalancing caused partial session cache drift; approximately 2% of active sessions invalidated unexpectedly.', FALSE),

    -- P4 incidents (3)
    ('INC-2024-014', 'Data pipeline schema migration timeout on large table', 'P4', 'data-pipeline', 'resolved',
     '2024-03-01 02:00:00+00', '2024-03-01 09:30:00+00', 450,
     'database', 'ALTER TABLE on 800M row events table acquired exclusive lock; long-running migration blocked writes during off-peak window.', FALSE),

    ('INC-2024-033', 'Payment API PDF receipt generation latency', 'P4', 'payment-api', 'resolved',
     '2024-06-20 10:00:00+00', '2024-06-20 14:20:00+00', 260,
     'third-party', 'PDF rendering microservice dependency (wkhtmltopdf) crashed due to font cache corruption; receipt generation p99 exceeded 30s.', FALSE),

    ('INC-2024-061', 'API Gateway health check endpoint false positives', 'P4', 'api-gateway', 'open',
     '2024-10-30 08:00:00+00', NULL, NULL,
     'network', 'Health check endpoint responding with 200 despite upstream database connection pool exhaustion; load balancer not routing away from degraded instance.', FALSE);

-- Part 4: Permissions
GRANT SELECT ON production_incidents TO sql_query_role;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON production_incidents FROM sql_query_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM sql_query_role;

-- Part 5: Enable RLS on production_incidents (project policy: all tables need RLS)
ALTER TABLE production_incidents ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read all incidents (shared reference data, no per-user filtering)
CREATE POLICY "authenticated_read_incidents" ON production_incidents
    FOR SELECT TO authenticated USING (true);

-- Part 6: RPC function for safe SQL execution on production_incidents table
CREATE OR REPLACE FUNCTION execute_incidents_query(query_text TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public  -- Required for SECURITY DEFINER: prevents schema injection attacks
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

    -- Validate: must reference production_incidents table
    IF normalized NOT LIKE '%FROM PRODUCTION_INCIDENTS%' AND normalized NOT LIKE '%FROM "PRODUCTION_INCIDENTS"%' THEN
        RAISE EXCEPTION 'Only queries on the production_incidents table are allowed';
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

-- Transfer ownership to sql_query_role so SECURITY DEFINER runs with minimal privileges
-- (sql_query_role has SELECT on production_incidents only — no other table access)
ALTER FUNCTION execute_incidents_query(TEXT) OWNER TO sql_query_role;

-- Grant execute to authenticated and service_role only — no anonymous access to incident data
GRANT EXECUTE ON FUNCTION execute_incidents_query TO authenticated;
GRANT EXECUTE ON FUNCTION execute_incidents_query TO service_role;

-- Add comments
COMMENT ON TABLE production_incidents IS 'Production incidents table for IR-Copilot text-to-SQL tool. Contains 15 realistic incident records spanning 2024.';
COMMENT ON FUNCTION execute_incidents_query IS 'Safely executes validated SELECT queries against the production_incidents table. Provides defense-in-depth SQL validation.';
