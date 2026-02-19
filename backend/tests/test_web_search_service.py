"""
Test web search service functionality including:
- Basic search with valid query
- Max results parameter enforcement
- Error handling for empty query
- Missing API key behavior
"""
import asyncio
from unittest.mock import patch
from dotenv import load_dotenv
from services.web_search_service import WebSearchService, web_search_service
from config import settings

# Load environment variables
load_dotenv()

has_api_key = bool(settings.TAVILY_API_KEY and settings.WEB_SEARCH_ENABLED)


async def test_basic_search():
    """Basic search - 'Python programming' should return results or skip if no API key."""
    if not has_api_key:
        print("[SKIP] Basic search (no API key or web search disabled)")
        return

    response = await web_search_service.search("Python programming")
    if response.error:
        print(f"[FAIL] Basic search: {response.error}")
    elif response.result_count > 0:
        # Verify result structure
        first = response.results[0]
        ok = first.title and first.url and first.content and first.score is not None
        if ok:
            print(f"[PASS] Basic search: {response.result_count} results, first title='{first.title[:50]}'")
        else:
            print(f"[FAIL] Basic search: result missing required fields")
    else:
        print("[WARN] Basic search: 0 results returned")


async def test_max_results():
    """Query with max_results=3 should return at most 3 results."""
    if not has_api_key:
        print("[SKIP] Max results (no API key or web search disabled)")
        return

    response = await web_search_service.search("artificial intelligence news", max_results=3)
    if response.error:
        print(f"[FAIL] Max results: {response.error}")
    elif response.result_count <= 3:
        print(f"[PASS] Max results: got {response.result_count} results (limit 3)")
    else:
        print(f"[FAIL] Max results: got {response.result_count} results, expected <= 3")


async def test_error_handling_empty_query():
    """Empty query should be handled gracefully (error or empty results, no crash)."""
    if not has_api_key:
        print("[SKIP] Error handling - empty query (no API key or web search disabled)")
        return

    try:
        response = await web_search_service.search("")
        # Either an error message or zero results is acceptable
        if response.error:
            print(f"[PASS] Error handling - empty query: error returned '{response.error[:60]}'")
        else:
            print(f"[PASS] Error handling - empty query: {response.result_count} results (no crash)")
    except Exception as e:
        print(f"[FAIL] Error handling - empty query: unhandled exception: {e}")


async def test_missing_api_key():
    """Service with no API key should return error message, not crash."""
    # Create a fresh service instance with no API key
    with patch.object(settings, 'TAVILY_API_KEY', None):
        service = WebSearchService()
        response = await service.search("test query")

        if response.error and response.result_count == 0:
            print(f"[PASS] Missing API key: error='{response.error}'")
        elif response.error is None:
            print("[FAIL] Missing API key: expected error but got none")
        else:
            print(f"[FAIL] Missing API key: unexpected state - error={response.error}, count={response.result_count}")


async def main():
    print("=" * 60)
    print("WEB SEARCH SERVICE TESTS")
    print("=" * 60)

    await test_basic_search()
    await test_max_results()
    await test_error_handling_empty_query()
    await test_missing_api_key()

    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
