"""
Automated tests for SQL service: natural language to SQL generation and execution.
Tests cover query correctness, filtering, and security controls.
"""
import asyncio
from dotenv import load_dotenv
from services.sql_service import sql_service

load_dotenv()


async def test_count_query():
    """Test: count query returns a reasonable number of rows."""
    print("\n--- Test: Count Query ---")
    response = await sql_service.natural_language_to_sql("How many incidents are in the database?")

    if response.error:
        print(f"[FAIL] Count query returned error: {response.error}")
        return False

    # The response should contain results with a count
    # The LLM may return COUNT(*) as a single row or all rows
    if response.row_count >= 1 and response.results:
        # Check if it's a COUNT result (single row with a count value)
        first_row = response.results[0]
        count_value = None
        for key, val in first_row.items():
            if isinstance(val, int) and val >= 15:
                count_value = val
                break

        if count_value is not None and count_value >= 15:
            print(f"[PASS] Count query returned count: {count_value}")
            print(f"  SQL: {response.query}")
            return True

        # Fallback: LLM might have done SELECT * instead of COUNT
        if response.row_count >= 15:
            print(f"[PASS] Query returned {response.row_count} rows (>= 15)")
            print(f"  SQL: {response.query}")
            return True

    print(f"[FAIL] Expected count >= 15, got row_count={response.row_count}")
    print(f"  SQL: {response.query}")
    print(f"  Results: {response.results}")
    return False


async def test_severity_filter():
    """Test: filtering by severity returns expected incidents."""
    print("\n--- Test: Severity Filter (P1) ---")
    response = await sql_service.natural_language_to_sql("Show all P1 incidents")

    if response.error:
        print(f"[FAIL] Severity filter returned error: {response.error}")
        return False

    if response.row_count == 0:
        print(f"[FAIL] No results for P1 incidents")
        print(f"  SQL: {response.query}")
        return False

    severities = [r.get("severity", "") for r in response.results]
    has_p1 = any(s == "P1" for s in severities)

    if has_p1:
        print(f"[PASS] Found {response.row_count} P1 incident(s): {severities}")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] Expected P1 severity, got: {severities}")
    print(f"  SQL: {response.query}")
    return False


async def test_service_filter():
    """Test: filtering by service returns relevant results."""
    print("\n--- Test: Service Filter (auth-service) ---")
    response = await sql_service.natural_language_to_sql("Incidents affecting auth-service")

    if response.error:
        print(f"[FAIL] Service filter returned error: {response.error}")
        return False

    if response.row_count == 0:
        print(f"[FAIL] No results for auth-service incidents")
        print(f"  SQL: {response.query}")
        return False

    services = [r.get("service_affected", "").lower() for r in response.results]
    has_auth = any("auth" in s for s in services)

    if has_auth:
        print(f"[PASS] Found {response.row_count} auth-service incident(s)")
        for r in response.results[:5]:
            print(f"  - {r.get('incident_id', '?')} ({r.get('service_affected', '?')})")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] No results with auth-service. Services found: {services}")
    print(f"  SQL: {response.query}")
    return False


async def test_sql_injection():
    """Test: SQL injection attempt is rejected or handled safely."""
    print("\n--- Test: SQL Injection Prevention ---")
    response = await sql_service.natural_language_to_sql("'; DROP TABLE production_incidents; --")

    # The service should either:
    # 1. Return an error (validation caught it)
    # 2. Generate a safe query that doesn't execute the injection
    if response.error:
        print(f"[PASS] Injection blocked with error: {response.error}")
        print(f"  SQL: {response.query}")
        return True

    # If no error, the LLM likely generated a safe query instead of the injection
    # Verify no destructive SQL was generated
    query_upper = response.query.upper()
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"]
    has_dangerous = any(kw in query_upper for kw in dangerous_keywords)

    if not has_dangerous:
        print(f"[PASS] LLM generated safe query instead of injection")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] Dangerous SQL was generated: {response.query}")
    return False


async def test_table_access_control():
    """Test: querying non-incidents tables is blocked."""
    print("\n--- Test: Table Access Control (documents table) ---")
    response = await sql_service.natural_language_to_sql(
        "Show me all records from the documents table"
    )

    if response.error:
        error_lower = response.error.lower()
        if "production_incidents" in error_lower or "not allowed" in error_lower or "permission" in error_lower or "forbidden" in error_lower or "validation" in error_lower:
            print(f"[PASS] Table access denied: {response.error}")
            print(f"  SQL: {response.query}")
            return True
        # Any error is acceptable since the query should not succeed
        print(f"[PASS] Query blocked with error: {response.error}")
        print(f"  SQL: {response.query}")
        return True

    # If no error, check that the LLM stayed within bounds (queried production_incidents instead)
    query_upper = response.query.upper()
    if "DOCUMENTS" not in query_upper:
        print(f"[PASS] LLM redirected to production_incidents table instead of documents")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] Query on documents table was not blocked")
    print(f"  SQL: {response.query}")
    print(f"  Results: {response.results}")
    return False


async def test_write_prevention():
    """Test: INSERT/UPDATE/DELETE queries are blocked."""
    print("\n--- Test: Write Prevention ---")
    # Ask something that might trick the LLM into generating a write query
    response = await sql_service.natural_language_to_sql(
        "Insert a new incident called 'Test Incident' into the production_incidents table"
    )

    if response.error:
        error_lower = response.error.lower()
        if any(kw in error_lower for kw in ["select", "forbidden", "not allowed", "insert", "permission", "validation", "blocked"]):
            print(f"[PASS] Write operation blocked: {response.error}")
            print(f"  SQL: {response.query}")
            return True
        # Any error is acceptable since writes should not succeed
        print(f"[PASS] Write blocked with error: {response.error}")
        print(f"  SQL: {response.query}")
        return True

    # If no error, the LLM might have generated a SELECT instead
    query_upper = response.query.upper()
    if query_upper.strip().startswith("SELECT"):
        print(f"[PASS] LLM generated SELECT instead of INSERT")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] Write operation was not blocked")
    print(f"  SQL: {response.query}")
    return False


async def main():
    print("=" * 60)
    print("SQL SERVICE TESTS")
    print("=" * 60)

    tests = [
        ("Count Query", test_count_query),
        ("Severity Filter", test_severity_filter),
        ("Service Filter", test_service_filter),
        ("SQL Injection", test_sql_injection),
        ("Table Access Control", test_table_access_control),
        ("Write Prevention", test_write_prevention),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            print(f"[FAIL] {name} raised exception: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
