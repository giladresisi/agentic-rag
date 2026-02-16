from config import settings
from services.provider_service import provider_service
from services.sql_service import sql_service
from services.web_search_service import web_search_service
from typing import AsyncGenerator, List, Dict, Tuple, Optional
import os
import json

# Initialize LangSmith tracing
langsmith_enabled = False
langsmith_client = None

try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import traceable as ls_traceable

    langsmith_client = LangSmithClient()
    langsmith_enabled = True

except ImportError:
    # No-op decorator when LangSmith is not available
    def ls_traceable(*args, **kwargs):
        def decorator(f):
            return f
        return decorator


class ChatService:
    """Provider-agnostic service for chat completions with tool calling support."""

    # Tool definition for document retrieval
    RETRIEVAL_TOOL = {
        "type": "function",
        "function": {
            "name": "retrieve_documents",
            "description": "Search and retrieve relevant document chunks from the user's uploaded documents. ALWAYS use this tool when the user asks about their documents or specific information. This tool performs semantic search across the user's knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A detailed search query describing what to find. Be specific and include key terms from the user's question. Examples: 'document content and main topics', 'specifications and features', 'introduction and overview'. Avoid single generic words like 'summary' or 'overview'."
                    }
                },
                "required": ["query"]
            }
        }
    }

    # Tool definition for text-to-SQL queries
    TEXT_TO_SQL_TOOL = {
        "type": "function",
        "function": {
            "name": "query_books_database",
            "description": "Query a database of books using natural language. Use for questions about books, authors, genres, ratings. Examples: 'Books by George Orwell', 'Fantasy books with high ratings', 'Books published after 1950'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about books"
                    }
                },
                "required": ["query"]
            }
        }
    }

    # Tool definition for web search
    WEB_SEARCH_TOOL = {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search web for current info not in documents. Use ONLY when documents lack answer or for current events. Try document retrieval first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query"
                    }
                },
                "required": ["query"]
            }
        }
    }

    # Tool definition for sub-agent document analysis
    ANALYZE_DOCUMENT_TOOL = {
        "type": "function",
        "function": {
            "name": "analyze_document_with_subagent",
            "description": "Delegate complex document analysis tasks to a specialized sub-agent with full document context. Use this for tasks requiring deep analysis, summarization, or extraction from entire documents (not just chunks).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Detailed description of the analysis task for the sub-agent. Be specific about what information to extract or how to analyze the document."
                    },
                    "document_name": {
                        "type": "string",
                        "description": "Name of the document to analyze (e.g., 'report.pdf', 'policy.docx')"
                    }
                },
                "required": ["task_description", "document_name"]
            }
        }
    }

    @staticmethod
    def build_conversation_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Build conversation history in Chat Completions format.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            List of message dicts in OpenAI format
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

    @staticmethod
    async def stream_response(
        conversation_history: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        base_url: str | None = None,
        user_id: str | None = None
    ) -> AsyncGenerator[Tuple[str, Optional[List[Dict]], Optional[Dict]], None]:
        """Stream a response using the specified provider with tool calling support.

        Args:
            conversation_history: Full conversation history (list of messages)
            model: Model to use for generation
            provider: Provider identifier
            base_url: Optional custom base URL for provider
            user_id: Optional user ID for retrieval RLS filtering

        Yields:
            Tuples of (text_delta, sources, subagent_metadata) where sources/metadata populated on final yield
        """
        full_response = ""
        trace_closed = False
        sources = None
        subagent_metadata = None

        # Add system prompt if not present to encourage tool use and prevent hallucinations
        # Make a copy to avoid modifying the original list
        conversation_history = list(conversation_history)
        if not conversation_history or conversation_history[0].get("role") != "system":
            system_message = {
                "role": "system",
                "content": """You are a helpful assistant with access to multiple tools:

1. retrieve_documents: Search uploaded document content (semantic search, returns 5 relevant chunks)
2. query_books_database: Query a books database with natural language (structured data queries)
3. search_web: Search web for current information (use for recent events, news)
4. analyze_document_with_subagent: Delegate complex full-document analysis to specialized sub-agent

IMPORTANT RULES:
- User's uploaded documents → retrieve_documents for semantic search
- Questions about books/authors/genres → query_books_database
- Current events/recent info not in documents → search_web
- Complex document analysis (summarization, deep extraction, entire document review) → analyze_document_with_subagent
- If no results from any tool, explain to user and ask for clarification
- NEVER make up or fabricate information - only use data returned by tools
- Always attribute sources when using tools
- For simple document queries, use retrieve_documents; for complex analysis, use analyze_document_with_subagent"""
            }
            conversation_history.insert(0, system_message)

        # Create LangSmith run if tracing is enabled
        run_id = None
        if langsmith_enabled and langsmith_client:
            try:
                import uuid
                from datetime import datetime, timezone
                run_id = uuid.uuid4()
                langsmith_client.create_run(
                    id=run_id,
                    name="chat_completions_stream",
                    run_type="llm",
                    inputs={
                        "messages": conversation_history,
                        "model": model,
                        "provider": provider,
                        "base_url": base_url,
                    },
                    project_name=os.getenv('LANGCHAIN_PROJECT'),
                    start_time=datetime.now(timezone.utc),
                )
            except Exception:
                run_id = None

        try:
            # Build tools list dynamically based on enabled features
            tools = [ChatService.RETRIEVAL_TOOL, ChatService.ANALYZE_DOCUMENT_TOOL]
            if settings.TEXT_TO_SQL_ENABLED:
                tools.append(ChatService.TEXT_TO_SQL_TOOL)
            if settings.WEB_SEARCH_ENABLED:
                tools.append(ChatService.WEB_SEARCH_TOOL)

            # Stream from provider with tools
            tool_calls = []
            current_tool_call = None

            async for chunk in provider_service.stream_chat_completion(
                provider=provider,
                model=model,
                messages=conversation_history,
                base_url=base_url,
                tools=tools,
            ):
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # Handle content delta
                    if delta.content:
                        full_response += delta.content
                        yield (delta.content, None, None)

                    # Handle tool call deltas
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            if tool_call_delta.index is not None:
                                while len(tool_calls) <= tool_call_delta.index:
                                    tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                current_tool_call = tool_calls[tool_call_delta.index]

                            if tool_call_delta.id:
                                current_tool_call["id"] = tool_call_delta.id
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    current_tool_call["function"]["name"] = tool_call_delta.function.name
                                if tool_call_delta.function.arguments:
                                    current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments

            # If tool calls were detected, execute them and continue
            if tool_calls and user_id:
                from services.retrieval_service import retrieval_service

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                    context_text = ""

                    if tool_name == "retrieve_documents":
                        query = args.get("query", "")

                        chunks = await retrieval_service.retrieve_relevant_chunks(
                            query=query,
                            user_id=user_id
                        )

                        context_text = "\n\n".join([
                            f"Document: {chunk['document_name']}\n{chunk['content']}"
                            for chunk in chunks
                        ])

                        sources = [
                            {
                                "document_id": chunk["document_id"],
                                "document_name": chunk["document_name"],
                                "chunk_id": chunk["id"],
                                "content": chunk["content"],
                                "similarity": chunk["similarity"]
                            }
                            for chunk in chunks
                        ]

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "retrieve_documents",
                                    "arguments": tool_call["function"]["arguments"]
                                }
                            }]
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": context_text
                        })

                    elif tool_name == "query_books_database":
                        query = args.get("query", "")
                        sql_response = await sql_service.natural_language_to_sql(query)
                        if sql_response.error:
                            context_text = f"SQL query failed: {sql_response.error}"
                        else:
                            context_text = f"SQL Query: {sql_response.query}\n\nResults ({sql_response.row_count} books):\n"
                            context_text += "\n".join([str(r) for r in sql_response.results[:20]])

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "query_books_database",
                                    "arguments": tool_call["function"]["arguments"]
                                }
                            }]
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": context_text
                        })

                    elif tool_name == "search_web":
                        query = args.get("query", "")
                        search_response = await web_search_service.search(query)
                        if search_response.error:
                            context_text = f"Web search failed: {search_response.error}"
                        else:
                            context_text = f"Web search: {query}\n\n"
                            for i, r in enumerate(search_response.results, 1):
                                context_text += f"{i}. {r.title}\n{r.content}\nSource: {r.url}\n\n"

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "search_web",
                                    "arguments": tool_call["function"]["arguments"]
                                }
                            }]
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": context_text
                        })

                    elif tool_name == "analyze_document_with_subagent":
                        task_description = args.get("task_description", "")
                        document_name = args.get("document_name", "")

                        # Look up document by filename
                        from services.supabase_service import get_supabase_admin
                        supabase = get_supabase_admin()
                        doc_response = supabase.table("documents")\
                            .select("id, filename")\
                            .eq("user_id", user_id)\
                            .eq("filename", document_name)\
                            .eq("status", "completed")\
                            .execute()

                        if not doc_response.data:
                            # Document not found - add error to conversation
                            context_text = f"Error: Document '{document_name}' not found. Please verify the document name and ensure it has been fully processed."
                        else:
                            # Execute sub-agent
                            from services.subagent_service import execute_subagent
                            from models.subagent import SubAgentRequest

                            request = SubAgentRequest(
                                task_description=task_description,
                                document_id=doc_response.data[0]["id"],
                                parent_depth=0,
                                user_id=user_id
                            )
                            result = await execute_subagent(request, user_id)

                            subagent_metadata = {
                                "task_description": task_description,
                                "document_id": doc_response.data[0]["id"],
                                "document_name": document_name,
                                "status": result.status,
                                "reasoning_steps": [step.dict() for step in result.reasoning_steps],
                                "result": result.result,
                                "error": result.error
                            }

                            context_text = result.result if result.status == "completed" else f"Error: {result.error}"

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "analyze_document_with_subagent",
                                    "arguments": tool_call["function"]["arguments"]
                                }
                            }]
                        })
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": context_text
                        })

                # Follow-up stream without tools after all tool calls
                async for chunk in provider_service.stream_chat_completion(
                    provider=provider,
                    model=model,
                    messages=conversation_history,
                    base_url=base_url,
                ):
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            full_response += delta.content
                            yield (delta.content, None, None)

            # Yield sources and/or subagent_metadata on final message
            if sources or subagent_metadata:
                yield ("", sources, subagent_metadata)

            # Close LangSmith trace on success
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        outputs={"content": full_response, "sources": sources, "subagent_metadata": subagent_metadata},
                        end_time=datetime.now(timezone.utc),
                    )
                    trace_closed = True
                except Exception:
                    pass

        except Exception as e:
            # Close trace with error
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    langsmith_client.update_run(
                        run_id=run_id,
                        error=str(e),
                        end_time=datetime.now(timezone.utc),
                    )
                except Exception:
                    pass

            raise Exception(f"Failed to stream response: {str(e)}")


chat_service = ChatService()
