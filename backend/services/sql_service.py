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
BOOKS_SCHEMA = """books table columns:
- id (INTEGER PRIMARY KEY)
- title (TEXT)
- author (TEXT)
- published_year (INTEGER)
- genre (TEXT)
- rating (DECIMAL)
- pages (INTEGER)
- isbn (TEXT)"""


class SQLService:
    """Service for converting natural language queries to SQL and executing them."""

    @staticmethod
    def _get_sql_query_client():
        """Get Supabase admin client for executing validated SQL queries.

        The books table is public reference data. Safety is enforced by:
        1. Application-level validation (_validate_query)
        2. Database-level RPC function (execute_books_query) restricts to books table
        """
        from services.supabase_service import get_supabase_admin
        return get_supabase_admin()

    @staticmethod
    def _validate_query(sql: str) -> tuple[bool, str]:
        """Validate SQL query for safety.

        Only allows SELECT queries on the books table with max 100 rows.

        Args:
            sql: The SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        normalized = sql.strip().upper()

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

        # Only allow books table - check FROM clause
        from_match = re.search(r'\bFROM\s+(\w+)', normalized)
        if from_match:
            table_name = from_match.group(1)
            if table_name != "BOOKS":
                return False, f"Only the 'books' table is allowed, got: {table_name.lower()}"

        # Check for JOIN on other tables
        join_matches = re.findall(r'\bJOIN\s+(\w+)', normalized)
        for table in join_matches:
            if table != "BOOKS":
                return False, f"JOIN with table '{table.lower()}' is not allowed"

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
            query: Natural language question about the books table

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
                        f"{BOOKS_SCHEMA}\n\n"
                        "Rules:\n"
                        "- ONLY generate SELECT queries\n"
                        "- ONLY query the 'books' table\n"
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
                'execute_books_query',
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
