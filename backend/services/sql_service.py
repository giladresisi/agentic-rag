import re
from pydantic import BaseModel
from config import settings
from services.provider_service import provider_service
from models.tool_response import SQLQueryResponse


# Pydantic model for LLM structured output
class SQLQuery(BaseModel):
    sql: str
    reasoning: str


# Schema context provided to the LLM for SQL generation
INCIDENTS_SCHEMA = """production_incidents table columns:
- id (INTEGER PRIMARY KEY)
- incident_id (TEXT) -- e.g. 'INC-2024-003'
- title (TEXT)
- severity (TEXT) -- 'P1', 'P2', 'P3', or 'P4'
- service_affected (TEXT)
- status (TEXT) -- 'resolved', 'open', or 'monitoring'
- started_at (TIMESTAMPTZ) -- when the incident started
- resolved_at (TIMESTAMPTZ) -- when resolved, NULL if still active
- duration_minutes (INTEGER) -- total duration in minutes, NULL if still active
- root_cause_category (TEXT) -- 'database', 'deployment', 'network', 'third-party', or 'configuration'
- description (TEXT)
- postmortem_written (BOOLEAN)"""


class SQLService:
    """Service for converting natural language queries to SQL and executing them."""

    @staticmethod
    def _get_sql_query_client():
        """Get Supabase admin client for executing validated SQL queries.

        The production_incidents table is eval reference data. Safety is enforced by:
        1. Application-level validation (_validate_query)
        2. Database-level RPC function (execute_incidents_query) restricts to production_incidents table
        """
        from services.supabase_service import get_supabase_admin
        return get_supabase_admin()

    @staticmethod
    def _validate_query(sql: str) -> tuple[bool, str]:
        """Validate SQL query for safety.

        Only allows SELECT queries on the production_incidents table with max 100 rows.

        Args:
            sql: The SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        normalized = sql.strip().upper()

        # Block semicolons first — prevents statement chaining before any other check
        if ";" in sql:
            return False, "Semicolons are not allowed in queries"

        # Must start with SELECT
        if not normalized.startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        # Block dangerous keywords
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
                      "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"]
        for keyword in dangerous:
            # Match as whole word to avoid false positives (e.g., "SELECTED")
            if re.search(rf'\b{keyword}\b', normalized):
                return False, f"Query contains forbidden keyword: {keyword}"

        # Require FROM clause — queries without FROM are suspicious (e.g. SELECT version())
        # Handle both unquoted and quoted identifiers
        from_match = re.search(r'\bFROM\s+"?(\w+)"?', normalized)
        if not from_match:
            return False, "Query must contain a FROM clause referencing production_incidents"
        table_name = from_match.group(1)
        if table_name != "PRODUCTION_INCIDENTS":
            return False, f"Only the 'production_incidents' table is allowed, got: {table_name.lower()}"

        # Check for JOIN on other tables (explicit JOIN syntax)
        join_matches = re.findall(r'\bJOIN\s+(\w+)', normalized)
        for table in join_matches:
            if table != "PRODUCTION_INCIDENTS":
                return False, f"JOIN with table '{table.lower()}' is not allowed"

        # Block implicit comma-joins (e.g. FROM production_incidents, pg_shadow)
        # Extract everything between FROM and the first SQL clause keyword, then look for commas
        from_clause = re.search(
            r'\bFROM\b(.*?)(?:\bWHERE\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|\bHAVING\b|\bJOIN\b|\Z)',
            normalized,
            re.DOTALL,
        )
        if from_clause and ',' in from_clause.group(1):
            return False, "Multiple tables in FROM clause are not allowed"

        # Enforce max 100 rows
        limit_match = re.search(r'\bLIMIT\s+(\d+)', normalized)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 100:
                return False, "LIMIT cannot exceed 100 rows"

        return True, ""

    @staticmethod
    def _ensure_limit(sql: str) -> str:
        """Ensure query has a LIMIT clause, adding LIMIT 100 if missing."""
        normalized = sql.strip().upper()
        if "LIMIT" not in normalized:
            sql = sql.rstrip().rstrip(";")
            sql += " LIMIT 100"
        return sql

    @staticmethod
    async def natural_language_to_sql(query: str) -> SQLQueryResponse:
        """Convert a natural language query to SQL and execute it.

        Args:
            query: Natural language question about the production_incidents table

        Returns:
            SQLQueryResponse with query results or error
        """
        if not settings.TEXT_TO_SQL_ENABLED:
            return SQLQueryResponse(
                query="",
                results=[],
                row_count=0,
                error="Text-to-SQL is not enabled"
            )

        generated_sql = ""

        try:
            # Step 1: LLM generates SQL using structured output
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a SQL query generator. Given a natural language question, "
                        "generate a valid PostgreSQL SELECT query for the following schema:\n\n"
                        f"{INCIDENTS_SCHEMA}\n\n"
                        "Rules:\n"
                        "- ONLY generate SELECT queries\n"
                        "- ONLY query the 'production_incidents' table\n"
                        "- Always include a LIMIT clause (max 100)\n"
                        "- Use proper PostgreSQL syntax\n"
                        "- For text searches, use ILIKE for case-insensitive matching"
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]

            sql_query = await provider_service.create_structured_completion(
                provider=settings.DEFAULT_PROVIDER,
                model=settings.DEFAULT_MODEL,
                messages=messages,
                response_schema=SQLQuery,
                base_url=settings.DEFAULT_BASE_URL,
            )

            generated_sql = sql_query.sql.strip()

            # Step 2: Validate the generated SQL
            is_valid, error_msg = SQLService._validate_query(generated_sql)
            if not is_valid:
                return SQLQueryResponse(
                    query=generated_sql,
                    results=[],
                    row_count=0,
                    error=f"Query validation failed: {error_msg}"
                )

            # Ensure LIMIT clause exists
            generated_sql = SQLService._ensure_limit(generated_sql)

            # Strip trailing semicolon (RPC wraps query in subquery, semicolons cause syntax errors)
            generated_sql = generated_sql.rstrip().rstrip(';')

            # Step 3: Execute via Supabase RPC function (defense-in-depth)
            client = SQLService._get_sql_query_client()
            response = client.rpc(
                'execute_incidents_query',
                {'query_text': generated_sql}
            ).execute()

            results = response.data if response.data else []

            return SQLQueryResponse(
                query=generated_sql,
                results=results,
                row_count=len(results),
            )

        except Exception as e:
            return SQLQueryResponse(
                query=generated_sql,
                results=[],
                row_count=0,
                error=f"SQL query failed: {str(e)}"
            )


sql_service = SQLService()
