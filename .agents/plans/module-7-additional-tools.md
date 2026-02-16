# Feature: Module 7 - Additional Tools (Text-to-SQL + Web Search)

**⚠️ CRITICAL - DO NOT COMMIT CHANGES:**
- Implement ALL changes required by this plan
- Delete any debug logs you added during execution (console.log, print, etc.) that were NOT explicitly requested
- Keep pre-existing debug logs that were already in the codebase
- Leave ALL changes UNSTAGED (do NOT run git add or git commit)
- User will review changes with `git diff` before committing

## Feature Description

Add two tools to create a multi-tool agent:
1. **Text-to-SQL**: Query document metadata via natural language (e.g., "How many PDFs?")
2. **Web Search**: Fallback for current info not in documents (e.g., "Latest AI news")

Transforms single-tool RAG → versatile multi-tool agent routing between document content, metadata, and web.

## User Story

As a user, I want the assistant to query document metadata AND search the web when needed, so I get comprehensive answers from both my knowledge base and external information.

## Solution Statement

**Text-to-SQL Tool:** LLM converts natural language → safe SQL queries against `books` table using dedicated read-only Postgres role. Database-level security enforces SELECT-only access to `books` table exclusively.

**Web Search Tool:** Tavily API integration for current information with source attribution.

**Multi-Tool Routing:** LLM selects appropriate tool(s), can sequence multiple tools, provides clear attribution.

## Feature Metadata

**Type**: New Capability | **Complexity**: Medium | **Dependencies**: Tavily API (free tier) | **Breaking**: No

---

## CONTEXT REFERENCES

### Relevant Files - MUST READ

- `backend/services/chat_service.py` (lines 29-46, 168-227) - Tool calling pattern, execution flow
- `backend/services/retrieval_service.py` - Service pattern reference
- `backend/config.py` - Settings pattern
- `backend/models/reranking.py` - Pydantic model pattern
- `backend/test_rag_tool_calling.py` - Testing pattern

### New Files

- `backend/services/sql_service.py` - Safe SQL execution
- `backend/services/web_search_service.py` - Tavily integration
- `backend/models/tool_response.py` - Tool response models
- `backend/test_sql_service.py` - SQL tests
- `backend/test_web_search_service.py` - Web search tests
- `backend/test_multi_tool_integration.py` - Integration tests
- `supabase/migrations/014_sql_tool.sql` - SQL execution function

### Documentation

- [Tavily API](https://docs.tavily.com/docs/python-sdk/tavily-search) - Web search integration
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) - Multi-tool patterns
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-prepare.html) - Safe SQL execution

### Patterns

**Services:** `class ServiceName` + `service_name` instance (e.g., `ChatService`, `chat_service`)
**Errors:** Try/except, meaningful messages, no print() in production
**Tools:** Follow `RETRIEVAL_TOOL` structure in `chat_service.py`

---

## PARALLEL EXECUTION STRATEGY

### Dependency Graph

```
WAVE 1 (Parallel): Config + Models [Tasks 1.1, 1.2]
          ↓
WAVE 2 (Parallel): SQL Service + Web Service [Tasks 2.1, 2.2]
          ↓
WAVE 3 (Sequential): Chat Integration [Task 3.1]
          ↓
WAVE 4 (Parallel): All Tests [Tasks 4.1-4.3]
```

**Speedup:** 2x with 2 parallel agents (Waves 1, 2, 4 concurrent)

### Interface Contracts

- Task 1.1 → Tasks 2.1, 2.2: `TAVILY_API_KEY`, `TEXT_TO_SQL_ENABLED` config
- Task 1.2 → Tasks 2.1, 2.2: `ToolResponse`, `SQLQueryResponse` models
- Tasks 2.1, 2.2 → Task 3.1: Service instances

### Checkpoints

**Wave 1:** `python -c "from config import settings; from models.tool_response import SQLQueryResponse"`
**Wave 2:** `python -c "from services.sql_service import sql_service; from services.web_search_service import web_search_service"`
**Wave 3:** `python test_multi_tool_integration.py`

---

## IMPLEMENTATION TASKS

### WAVE 1: Foundation

#### Task 1.1: ADD config for Tavily + tool flags + SQL role

- **WAVE**: 1 | **AGENT**: config-specialist | **DEPENDS**: [] | **BLOCKS**: [2.2]
- **IMPLEMENT**:
  - Add to `backend/config.py` Settings:
    ```python
    TAVILY_API_KEY: str | None = None
    TEXT_TO_SQL_ENABLED: bool = True
    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 5

    # SQL Query Role (read-only role for text-to-SQL)
    SQL_QUERY_ROLE_PASSWORD: str | None = None
    ```
  - Add to `backend/.env.example`:
    ```bash
    TAVILY_API_KEY=tvly-...
    TEXT_TO_SQL_ENABLED=true
    WEB_SEARCH_ENABLED=true

    # SQL Query Role (created by migration 014)
    SQL_QUERY_ROLE_PASSWORD=secure_password_here
    ```
- **VALIDATE**: `python -c "from config import settings; assert hasattr(settings, 'TAVILY_API_KEY'); assert hasattr(settings, 'SQL_QUERY_ROLE_PASSWORD')"`

#### Task 1.2: CREATE tool response models

- **WAVE**: 1 | **AGENT**: backend-dev | **DEPENDS**: [] | **BLOCKS**: [2.1, 2.2]
- **IMPLEMENT**: Create `backend/models/tool_response.py`:
  ```python
  from pydantic import BaseModel, Field
  from typing import List, Optional

  class SQLQueryResponse(BaseModel):
      query: str
      results: List[dict]
      row_count: int
      error: Optional[str] = None

  class WebSearchResult(BaseModel):
      title: str
      url: str
      content: str
      score: float

  class WebSearchResponse(BaseModel):
      query: str
      results: List[WebSearchResult]
      result_count: int
      error: Optional[str] = None
  ```
- **VALIDATE**: `python -c "from models.tool_response import SQLQueryResponse, WebSearchResponse"`

---

### WAVE 2: Services

#### Task 2.1: CREATE SQL service with read-only role

- **WAVE**: 2 | **AGENT**: backend-dev | **DEPENDS**: [1.1, 1.2] | **BLOCKS**: [3.1]
- **IMPLEMENT**: Create `backend/services/sql_service.py`:

  **Key Components:**
  1. Create dedicated Supabase client using `sql_query_role`:
     ```python
     def _get_sql_query_client():
         """Get Supabase client authenticated as sql_query_role (read-only)."""
         from supabase import create_client
         return create_client(
             settings.SUPABASE_URL,
             settings.SUPABASE_ANON_KEY,
             options={
                 "db": {
                     "schema": "public"
                 },
                 "auth": {
                     "autoRefreshToken": False,
                     "persistSession": False
                 },
                 "global": {
                     "headers": {
                         "apikey": settings.SUPABASE_ANON_KEY,
                         # Use SQL query role credentials
                         "Authorization": f"Bearer {settings.SQL_QUERY_ROLE_PASSWORD}"
                     }
                 }
             }
         )
     ```

  2. `natural_language_to_sql(query)` - Main method (no user_id needed - books table is shared)

  3. LLM generates SQL using structured output:
     ```python
     class SQLQuery(BaseModel):
         sql: str
         reasoning: str
     ```

  4. **Safety validation** `_validate_query()`:
     - ONLY SELECT queries (reject INSERT/UPDATE/DELETE/DROP)
     - ONLY `books` table (database enforces this too)
     - Limit 100 rows max
     - NO user_id filtering (books table is shared reference data)

  5. Execute directly: `client.from_('books').select('*').execute()` or use RPC if complex query

  **Schema context for LLM:**
  ```
  books table columns:
  - id (INTEGER PRIMARY KEY)
  - title (TEXT)
  - author (TEXT)
  - published_year (INTEGER)
  - genre (TEXT)
  - rating (DECIMAL)
  - pages (INTEGER)
  - isbn (TEXT)
  ```

  **Database-level security ensures:**
  - Role can ONLY SELECT from `books` table
  - Any attempt to query other tables → PERMISSION DENIED
  - Any attempt to INSERT/UPDATE/DELETE → PERMISSION DENIED

- **DATABASE MIGRATION** (`supabase/migrations/014_sql_tool.sql`):
  ```sql
  -- Create books table for text-to-SQL queries
  CREATE TABLE IF NOT EXISTS books (
      id SERIAL PRIMARY KEY,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      published_year INTEGER,
      genre TEXT,
      rating DECIMAL(3,2),
      pages INTEGER,
      isbn TEXT UNIQUE
  );

  -- Populate with sample data
  INSERT INTO books (title, author, published_year, genre, rating, pages, isbn) VALUES
  ('The Great Gatsby', 'F. Scott Fitzgerald', 1925, 'Fiction', 4.2, 180, '978-0-7432-7356-5'),
  ('To Kill a Mockingbird', 'Harper Lee', 1960, 'Fiction', 4.5, 324, '978-0-06-112008-4'),
  ('1984', 'George Orwell', 1949, 'Dystopian', 4.6, 328, '978-0-452-28423-4'),
  ('Pride and Prejudice', 'Jane Austen', 1813, 'Romance', 4.3, 432, '978-0-14-143951-8'),
  ('The Hobbit', 'J.R.R. Tolkien', 1937, 'Fantasy', 4.7, 310, '978-0-547-92822-7'),
  ('Harry Potter and the Sorcerer''s Stone', 'J.K. Rowling', 1997, 'Fantasy', 4.8, 309, '978-0-439-70818-8'),
  ('The Catcher in the Rye', 'J.D. Salinger', 1951, 'Fiction', 3.8, 277, '978-0-316-76948-0'),
  ('Animal Farm', 'George Orwell', 1945, 'Satire', 4.1, 112, '978-0-452-28424-1'),
  ('Lord of the Flies', 'William Golding', 1954, 'Fiction', 3.7, 224, '978-0-399-50148-7'),
  ('Brave New World', 'Aldous Huxley', 1932, 'Dystopian', 4.0, 268, '978-0-06-085052-4')
  ON CONFLICT (isbn) DO NOTHING;

  -- Create read-only role for SQL queries
  DO $$
  BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sql_query_role') THEN
          CREATE ROLE sql_query_role WITH LOGIN PASSWORD 'CHANGE_THIS_PASSWORD';
      END IF;
  END $$;

  -- Grant ONLY SELECT on books table
  GRANT USAGE ON SCHEMA public TO sql_query_role;
  GRANT SELECT ON books TO sql_query_role;

  -- Explicitly REVOKE all other privileges
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON books FROM sql_query_role;
  REVOKE ALL ON ALL TABLES IN SCHEMA public FROM sql_query_role;
  REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM sql_query_role;
  REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM sql_query_role;

  -- Grant SELECT ONLY on books (re-grant after revoke all)
  GRANT SELECT ON books TO sql_query_role;

  -- Prevent future privilege escalation
  ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM sql_query_role;
  ```

  **CRITICAL:** User must manually update migration with secure password before applying.

- **VALIDATE**: Create `backend/test_sql_service.py` (see Task 4.1)

#### Task 2.2: CREATE web search service

- **WAVE**: 2 | **AGENT**: backend-dev | **DEPENDS**: [1.1, 1.2] | **BLOCKS**: [3.1]
- **IMPLEMENT**:
  1. Add `tavily-python==0.3.0` to `requirements.txt`
  2. Create `backend/services/web_search_service.py`:
     ```python
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
     ```

- **VALIDATE**: Create `backend/test_web_search_service.py` (see Task 4.2)

---

### WAVE 3: Integration

#### Task 3.1: UPDATE chat_service for multi-tool support

- **WAVE**: 3 | **AGENT**: integration-specialist | **DEPENDS**: [2.1, 2.2] | **BLOCKS**: [4.1-4.3]
- **IMPLEMENT** (`backend/services/chat_service.py`):

  1. **Add imports:**
     ```python
     from services.sql_service import sql_service
     from services.web_search_service import web_search_service
     ```

  2. **Add tool definitions** (after line 46):
     ```python
     TEXT_TO_SQL_TOOL = {
         "type": "function",
         "function": {
             "name": "query_books_database",
             "description": "Query a database of books using natural language. Use for questions about books, authors, genres, ratings. Examples: 'Books by George Orwell', 'Fantasy books with high ratings', 'Books published after 1950'",
             "parameters": {
                 "type": "object",
                 "properties": {
                     "query": {"type": "string", "description": "Natural language query about books"}
                 },
                 "required": ["query"]
             }
         }
     }

     WEB_SEARCH_TOOL = {
         "type": "function",
         "function": {
             "name": "search_web",
             "description": "Search web for current info not in documents. Use ONLY when documents lack answer or for current events. Try document retrieval first.",
             "parameters": {
                 "type": "object",
                 "properties": {
                     "query": {"type": "string", "description": "Specific search query"}
                 },
                 "required": ["query"]
             }
         }
     }
     ```

  3. **Build tools list dynamically** (in `stream_response`, before line 137):
     ```python
     tools = [ChatService.RETRIEVAL_TOOL]
     if settings.TEXT_TO_SQL_ENABLED:
         tools.append(ChatService.TEXT_TO_SQL_TOOL)
     if settings.WEB_SEARCH_ENABLED:
         tools.append(ChatService.WEB_SEARCH_TOOL)
     ```

  4. **Update tool execution** (replace lines 168-227):
     ```python
     for tool_call in tool_calls:
         tool_name = tool_call["function"]["name"]
         args = json.loads(tool_call["function"]["arguments"])

         if tool_name == "retrieve_documents":
             # Existing retrieval logic (keep as-is)
             query = args.get("query", "")
             chunks = await retrieval_service.retrieve_relevant_chunks(query=query, user_id=user_id)
             context_text = "\n\n".join([f"Document: {c['document_name']}\n{c['content']}" for c in chunks])
             sources = [{"document_id": c["document_id"], "document_name": c["document_name"],
                        "chunk_id": c["id"], "content": c["content"], "similarity": c["similarity"]} for c in chunks]

         elif tool_name == "query_books_database":
             query = args.get("query", "")
             sql_response = await sql_service.natural_language_to_sql(query)
             if sql_response.error:
                 context_text = f"SQL query failed: {sql_response.error}"
             else:
                 context_text = f"SQL Query: {sql_response.query}\n\nResults ({sql_response.row_count} books):\n"
                 context_text += "\n".join([str(r) for r in sql_response.results[:20]])
             sources = None

         elif tool_name == "search_web":
             query = args.get("query", "")
             search_response = await web_search_service.search(query)
             if search_response.error:
                 context_text = f"Web search failed: {search_response.error}"
             else:
                 context_text = f"Web search: {query}\n\n"
                 for i, r in enumerate(search_response.results, 1):
                     context_text += f"{i}. {r.title}\n{r.content}\nSource: {r.url}\n\n"
             sources = None

         # Append to conversation history (existing pattern)
         conversation_history.append({
             "role": "assistant", "content": None,
             "tool_calls": [{"id": tool_call["id"], "type": "function",
                            "function": {"name": tool_name, "arguments": tool_call["function"]["arguments"]}}]
         })
         conversation_history.append({
             "role": "tool", "tool_call_id": tool_call["id"], "content": context_text
         })
     ```

  5. **Update system message** (line 93):
     ```python
     system_message = {
         "role": "system",
         "content": """You are a helpful assistant with tools:

     1. retrieve_documents: Search uploaded document content
     2. query_books_database: Query a books database with natural language
     3. search_web: Search web for current information

     RULES:
     - User's uploaded documents → retrieve_documents
     - Questions about books/authors/genres → query_books_database
     - Current events/recent info → search_web
     - No results → explain to user
     - NEVER fabricate - only use tool data
     - Always attribute sources"""
     }
     ```

- **VALIDATE**: `python test_multi_tool_integration.py`

---

### WAVE 4: Testing

#### Task 4.1: CREATE SQL service tests

- **WAVE**: 4 | **AGENT**: test-engineer | **DEPENDS**: [3.1] | **BLOCKS**: []
- **IMPLEMENT** `backend/test_sql_service.py`:
  - **Test 1**: Count query - "How many books are in the database?" → verify row_count ≥ 10
  - **Test 2**: Author filter - "Books by George Orwell" → verify results contain Orwell books
  - **Test 3**: Genre filter - "Fantasy books" → verify genre filtering works
  - **Test 4**: SQL injection - "'; DROP TABLE books; --" → verify rejected or permission denied
  - **Test 5**: Table access control - Try querying `documents` table → verify PERMISSION DENIED
  - **Test 6**: Write prevention - Try INSERT/UPDATE/DELETE → verify PERMISSION DENIED or blocked
- **VALIDATE**: `python test_sql_service.py` → all tests pass

#### Task 4.2: CREATE web search tests

- **WAVE**: 4 | **AGENT**: test-engineer | **DEPENDS**: [3.1] | **BLOCKS**: []
- **IMPLEMENT** `backend/test_web_search_service.py`:
  - **Test 1**: Basic search - "Python programming" → verify results or skip if no API key
  - **Test 2**: Max results - query with `max_results=3` → verify ≤ 3 results
  - **Test 3**: Error handling - empty query → verify graceful handling
- **VALIDATE**: `python test_web_search_service.py` → all tests pass or skip

#### Task 4.3: CREATE integration tests

- **WAVE**: 4 | **AGENT**: test-engineer | **DEPENDS**: [3.1] | **BLOCKS**: []
- **IMPLEMENT** `backend/test_multi_tool_integration.py`:
  - **Setup**: Create test document with chunks
  - **Test 1**: Books query - "Books by J.K. Rowling?" → verify SQL tool used, returns Harry Potter
  - **Test 2**: Document retrieval - "What does my document say about X?" → verify retrieval tool used
  - **Test 3**: Web search - "Current weather London?" → verify web tool used or graceful failure
  - **Test 4**: Multi-tool sequence - Ask about document, then books, then web search
  - **Cleanup**: Delete test document
- **VALIDATE**: `python test_multi_tool_integration.py` → all tests pass

---

## TESTING STRATEGY

### Test Automation

**Total**: 14 tests (100% automated)
- **Unit**: 10 (SQL: 6, Web: 4)
- **Integration**: 4 (multi-tool routing)

**Tools**: pytest, asyncio
**Execution**: `python test_sql_service.py && python test_web_search_service.py && python test_multi_tool_integration.py`

### Test Cases

**SQL Service (6):**
1. Count books - NL → SQL → results
2. Filter by author - author filtering
3. Filter by genre - genre filtering
4. SQL injection - security validation (blocked or rejected)
5. Table access control - attempt documents query → PERMISSION DENIED
6. Write prevention - attempt INSERT/UPDATE/DELETE → PERMISSION DENIED

**Web Search (4):**
1. Basic search - query → results
2. Max results - limit enforcement
3. Error handling - graceful degradation
4. Missing API key - config validation

**Integration (4):**
1. Books routing - LLM selects SQL tool for book queries
2. Document routing - LLM selects retrieval tool for user docs
3. Web search routing - LLM selects web tool for current info
4. Multi-tool sequence - multiple tools in conversation

**Manual**: None

---

## VALIDATION COMMANDS

### Level 1: Imports

```bash
cd backend
python -c "from services.sql_service import sql_service"
python -c "from services.web_search_service import web_search_service"
python -c "from models.tool_response import SQLQueryResponse"
```

### Level 2: Unit Tests

```bash
cd backend
python test_sql_service.py
python test_web_search_service.py
```

### Level 3: Integration

```bash
cd backend
python test_multi_tool_integration.py
```

### Level 4: Manual E2E

1. Start: `cd backend && python -m uvicorn main:app --reload`
2. Frontend: `cd frontend && npm run dev`
3. Test:
   - SQL: "What fantasy books are in the database?"
   - SQL: "Books by George Orwell?"
   - Web: "Latest AI news?"
   - Docs: "What does my document say about X?"
4. Verify: Tool selection, attribution, streaming, no errors

---

## ACCEPTANCE CRITERIA

- [ ] **Config**: Tavily API key, SQL role password, feature flags work
- [ ] **SQL Tool**: NL → SQL, books table only, SELECT only enforced at DB level
- [ ] **SQL Security**: Role cannot query other tables, cannot INSERT/UPDATE/DELETE
- [ ] **Books Table**: Created with 10+ sample books, queryable
- [ ] **Web Tool**: Tavily integration, attribution, graceful degradation
- [ ] **Multi-Tool**: 3 tools available, correct routing, attribution
- [ ] **Tests**: 14/14 automated passing (100%)
- [ ] **Code**: No print(), robust errors, minimal privileges

---

## COMPLETION CHECKLIST

- [ ] All waves completed and validated
- [ ] 14/14 automated tests passing
- [ ] All validation commands pass
- [ ] Manual E2E complete
- [ ] Migration 014 applied with secure password set
- [ ] SQL role password added to `.env`
- [ ] Verified: sql_query_role can ONLY SELECT from books table
- [ ] Verified: sql_query_role CANNOT access documents/chunks/other tables
- [ ] Verified: sql_query_role CANNOT INSERT/UPDATE/DELETE
- [ ] `tavily-python==0.3.0` installed
- [ ] `.env.example` updated
- [ ] **⚠️ Debug logs REMOVED**
- [ ] **⚠️ Changes UNSTAGED**

---

## NOTES

**Design Decisions:**
- Tavily over SerpAPI (LLM-optimized)
- SQL via LLM generation (flexible, natural language)
- **Database-level security** (dedicated read-only role vs. application-level validation only)
- Books table instead of documents (separation of concerns, safer for demo)
- Optional web search (graceful degradation)

**Trade-offs:**
- **Pro**: Defense in depth (DB + app validation), impossible for LLM to bypass DB restrictions
- **Pro**: Multi-tool routing, fast SQL queries, real-time web info, no RLS overhead
- **Con**: Extra Postgres role to manage, additional setup step
- **Con**: Complex routing, external API dependency
- **Mitigation**: Migration automates role creation, feature flags, graceful degradation

**Security Architecture:**
```
LLM generates SQL
    ↓
Application validates (SELECT only, books table)
    ↓
Database enforces (sql_query_role permissions)
    ↓
- ✅ Can SELECT from books
- ❌ Cannot SELECT from documents/chunks/threads/messages
- ❌ Cannot INSERT/UPDATE/DELETE on any table
```

**Future Enhancements:**
- Add more reference tables (movies, recipes, etc.) for SQL queries
- Tool analytics (which tools used most)
- Web search caching
- Multi-turn tool conversations
- Expand sql_query_role to more tables (with careful consideration)
