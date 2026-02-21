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
    response = await sql_service.natural_language_to_sql("How many books are in the database?")

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
            if isinstance(val, int) and val >= 10:
                count_value = val
                break

        if count_value is not None and count_value >= 10:
            print(f"[PASS] Count query returned count: {count_value}")
            print(f"  SQL: {response.query}")
            return True

        # Fallback: LLM might have done SELECT * instead of COUNT
        if response.row_count >= 10:
            print(f"[PASS] Query returned {response.row_count} rows (>= 10)")
            print(f"  SQL: {response.query}")
            return True

    print(f"[FAIL] Expected count >= 10, got row_count={response.row_count}")
    print(f"  SQL: {response.query}")
    print(f"  Results: {response.results}")
    return False


async def test_author_filter():
    """Test: filtering by author returns expected books."""
    print("\n--- Test: Author Filter (George Orwell) ---")
    response = await sql_service.natural_language_to_sql("Books by George Orwell")

    if response.error:
        print(f"[FAIL] Author filter returned error: {response.error}")
        return False

    if response.row_count == 0:
        print(f"[FAIL] No results for George Orwell")
        print(f"  SQL: {response.query}")
        return False

    titles = [r.get("title", "") for r in response.results]
    titles_lower = [t.lower() for t in titles]

    has_1984 = any("1984" in t for t in titles_lower)
    has_animal_farm = any("animal farm" in t for t in titles_lower)

    if has_1984 or has_animal_farm:
        print(f"[PASS] Found Orwell books: {titles}")
        print(f"  SQL: {response.query}")
        return True

    # Check if results at least have Orwell as author
    authors = [r.get("author", "") for r in response.results]
    if any("orwell" in a.lower() for a in authors):
        print(f"[PASS] Found books by Orwell: {titles}")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] Expected Orwell books, got: {titles}")
    print(f"  SQL: {response.query}")
    return False


async def test_genre_filter():
    """Test: filtering by genre returns relevant results."""
    print("\n--- Test: Genre Filter (Fantasy) ---")
    response = await sql_service.natural_language_to_sql("Fantasy books")

    if response.error:
        print(f"[FAIL] Genre filter returned error: {response.error}")
        return False

    if response.row_count == 0:
        print(f"[FAIL] No fantasy books found")
        print(f"  SQL: {response.query}")
        return False

    # Verify at least some results have fantasy genre
    genres = [r.get("genre", "").lower() for r in response.results]
    has_fantasy = any("fantasy" in g for g in genres)

    if has_fantasy:
        print(f"[PASS] Found {response.row_count} fantasy book(s)")
        for r in response.results[:5]:
            print(f"  - {r.get('title', '?')} ({r.get('genre', '?')})")
        print(f"  SQL: {response.query}")
        return True

    print(f"[FAIL] No results with fantasy genre. Genres found: {genres}")
    print(f"  SQL: {response.query}")
    return False


async def test_sql_injection():
    """Test: SQL injection attempt is rejected or handled safely."""
    print("\n--- Test: SQL Injection Prevention ---")
    response = await sql_service.natural_language_to_sql("'; DROP TABLE books; --")

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
    """Test: querying non-books tables is blocked."""
    print("\n--- Test: Table Access Control (documents table) ---")
    response = await sql_service.natural_language_to_sql(
        "Show me all records from the documents table"
    )

    if response.error:
        error_lower = response.error.lower()
        if "books" in error_lower or "not allowed" in error_lower or "permission" in error_lower or "forbidden" in error_lower or "validation" in error_lower:
            print(f"[PASS] Table access denied: {response.error}")
            print(f"  SQL: {response.query}")
            return True
        # Any error is acceptable since the query should not succeed
        print(f"[PASS] Query blocked with error: {response.error}")
        print(f"  SQL: {response.query}")
        return True

    # If no error, check that the LLM stayed within bounds (queried books instead)
    query_upper = response.query.upper()
    if "DOCUMENTS" not in query_upper:
        print(f"[PASS] LLM redirected to books table instead of documents")
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
        "Insert a new book called 'Test Book' by 'Test Author' into the books table"
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
        ("Author Filter", test_author_filter),
        ("Genre Filter", test_genre_filter),
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
