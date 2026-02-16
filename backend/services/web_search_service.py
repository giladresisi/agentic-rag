from tavily import TavilyClient
from config import settings
from models.tool_response import WebSearchResponse, WebSearchResult


class WebSearchService:
    def __init__(self):
        self.client = None
        if settings.TAVILY_API_KEY:
            self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    async def search(self, query: str, max_results=None) -> WebSearchResponse:
        max_results = max_results or settings.WEB_SEARCH_MAX_RESULTS

        if not settings.WEB_SEARCH_ENABLED or not self.client:
            return WebSearchResponse(query=query, results=[],
                                    result_count=0, error="Web search not configured")

        try:
            response = self.client.search(
                query=query, max_results=max_results,
                search_depth="basic"
            )
            results = [WebSearchResult(**item) for item in response['results']]
            return WebSearchResponse(query=query, results=results,
                                    result_count=len(results), error=None)
        except Exception as e:
            return WebSearchResponse(query=query, results=[],
                                    result_count=0, error=str(e))


web_search_service = WebSearchService()
