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
            "description": "STEP 1: Search and retrieve relevant document chunks from the user's uploaded documents. ALWAYS use this tool FIRST when the user asks about their documents. This tool performs semantic search and returns chunk content AND document names. Use the returned document names for subsequent subagent analysis calls if deeper analysis is needed.",
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
            "name": "query_incidents_database",
            "description": "Query a database of production incidents using natural language. Use for questions about incidents, severity, affected services, resolution times, root causes. Examples: 'Show all P1 incidents', 'Which service had the most outages?', 'Average resolution time for database issues'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about production incidents"
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
            "description": "STEP 2: Delegate complex full-document analysis to a specialized sub-agent. ONLY use this AFTER calling retrieve_documents to discover relevant document names. Use the exact document filenames returned by retrieve_documents. This tool provides full document context (not just chunks) for deep analysis, summarization, or extraction tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Detailed description of the analysis task for the sub-agent. Be specific about what information to extract or how to analyze the document."
                    },
                    "document_name": {
                        "type": "string",
                        "description": "EXACT filename of the document to analyze as returned by retrieve_documents (e.g., 'prime.md', 'plan-feature.md', 'report.pdf'). NEVER guess or hallucinate filenames - only use names from retrieve_documents results."
                    }
                },
                "required": ["task_description", "document_name"]
            }
        }
    }

    @staticmethod
    def _trace_tool_call(
        parent_run_id: str,
        tool_name: str,
        inputs: Dict,
        outputs: Dict,
        metadata: Optional[Dict] = None
    ):
        """Create a child LangSmith run for a tool execution.

        Args:
            parent_run_id: ID of parent chat completion run
            tool_name: Name of the tool being executed
            inputs: Tool input parameters
            outputs: Tool execution results
            metadata: Optional additional metadata
        """
        if not langsmith_enabled or not langsmith_client:
            return

        try:
            import uuid
            from datetime import datetime, timezone

            child_run_id = uuid.uuid4()

            # Start the tool run
            langsmith_client.create_run(
                id=child_run_id,
                name=f"tool_{tool_name}",
                run_type="tool",
                inputs=inputs,
                outputs=outputs,
                parent_run_id=parent_run_id,
                project_name=os.getenv('LANGCHAIN_PROJECT'),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                extra=metadata or {}
            )
        except Exception:
            # Tracing failures should not break tool execution
            pass

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
        sources = None
        subagent_metadata = None
        tool_calls_summary = []  # Track all tool calls for tracing

        # Add system prompt if not present to encourage tool use and prevent hallucinations
        # Make a copy to avoid modifying the original list
        conversation_history = list(conversation_history)
        if not conversation_history or conversation_history[0].get("role") != "system":
            system_message = {
                "role": "system",
                "content": """You are a helpful assistant with access to multiple tools:

1. retrieve_documents: Search uploaded document content (semantic search, returns 5 relevant chunks)
2. query_incidents_database: Query a production incidents database with natural language (structured data queries)
3. search_web: Search web for current information (use for recent events, news)
4. analyze_document_with_subagent: Delegate complex full-document analysis to specialized sub-agent

STRATEGIC RETRIEVAL APPROACH:

Before answering the user's query, think step-by-step:

1. ANALYZE THE QUERY:
   - What information is needed to answer this question?
   - What are the key concepts, entities, or topics?
   - Does the user want CHUNKS (specific facts) or COMPREHENSIVE ANALYSIS (full document understanding)?

2. PLAN YOUR RETRIEVAL STRATEGY:

   **For CHUNK-BASED queries** (specific facts, quick lookups):
   - Use multiple retrieve_documents calls with different queries
   - Each call targets a different aspect or concept
   - Synthesize answers from the returned chunks

   **For COMPREHENSIVE ANALYSIS queries** (deep analysis, summaries, multi-aspect understanding):
   - STEP 1: Call retrieve_documents ONCE with a broad query to discover relevant documents
   - STEP 2: Extract document names from the retrieval results
   - STEP 3: Call analyze_document_with_subagent for EACH discovered document
   - Pass specific analysis tasks to each subagent call

   **Example pattern for comprehensive analysis:**
   ```
   User asks: "Analyze my documents - what are themes, specs, and conclusions?"

   1. retrieve_documents(query="project documentation and main content")
      → Returns chunks from: [doc1.pdf, doc2.md, doc3.txt]

   2. analyze_document_with_subagent(
        document_name="doc1.pdf",
        task="Extract main themes and topics"
      )

   3. analyze_document_with_subagent(
        document_name="doc2.md",
        task="Identify technical specifications"
      )

   4. analyze_document_with_subagent(
        document_name="doc3.txt",
        task="Summarize conclusions and recommendations"
      )
   ```

3. EXECUTE THE PLANNED STRATEGY:
   - Follow the pattern chosen above
   - For comprehensive analysis: ALWAYS do retrieval first, then subagents
   - Use EXACT document names from retrieval results - NEVER guess filenames

TOOL USAGE GUIDELINES:

**Document Queries - Choose the Right Pattern:**

PATTERN A - Multiple Retrieval Calls (for specific facts):
- Query: "What does the document say about X?" → retrieve_documents multiple times
- Query: "Find information about Y and Z" → retrieve_documents for Y, then for Z
- Use when: User wants specific facts, quotes, or chunk-based information

PATTERN B - Retrieval + Subagents (for comprehensive analysis):
- Query: "Analyze documents for themes, specs, conclusions" → Use TWO-STEP workflow below
- Query: "Summarize my documents" → Use TWO-STEP workflow below
- Query: "What are the main points across all documents?" → Use TWO-STEP workflow below
- TWO-STEP WORKFLOW:
  STEP 1: retrieve_documents(query="broad search to discover documents")
  STEP 2: For each unique document name in results:
          analyze_document_with_subagent(document_name="exact_filename.ext", task="...")
  NEVER guess document names - always use names from Step 1!

**Other Tools:**
- Questions about incidents/severity/services → query_incidents_database (can query multiple times)
- Current events/recent info → search_web (use after checking documents)
- Incomplete information? Make additional tool calls with refined queries

QUALITY STANDARDS:
- NEVER make up or fabricate information - only use data returned by tools
- NEVER guess or hallucinate document filenames - always use retrieve_documents to discover them
- If initial tool calls don't provide enough information, make additional calls
- Always attribute sources when using tools
- For subagent analysis, ONLY use document names returned by retrieve_documents
- If no tool results are relevant after multiple attempts, explain limitations to user
- Synthesize information from multiple tool calls into coherent answers"""
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

        error_occurred = None

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

                        # Track tool call for summary
                        tool_call_info = {
                            "tool": "retrieve_documents",
                            "inputs": {"query": query},
                            "outputs": {
                                "chunk_count": len(chunks),
                                "document_names": list(set(c["document_name"] for c in chunks)),
                                "top_similarity": chunks[0]["similarity"] if chunks else None,
                                "avg_similarity": sum(c["similarity"] for c in chunks) / len(chunks) if chunks else None
                            }
                        }
                        tool_calls_summary.append(tool_call_info)

                        # Add LangSmith tracing
                        ChatService._trace_tool_call(
                            parent_run_id=run_id,
                            tool_name="retrieve_documents",
                            inputs={"query": query, "user_id": user_id},
                            outputs=tool_call_info["outputs"],
                            metadata={
                                "sources": [
                                    {"doc": c["document_name"], "similarity": c["similarity"]}
                                    for c in chunks
                                ]
                            }
                        )

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

                    elif tool_name == "query_incidents_database":
                        query = args.get("query", "")
                        sql_response = await sql_service.natural_language_to_sql(query)

                        if sql_response.error:
                            context_text = f"SQL query failed: {sql_response.error}"

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "query_incidents_database",
                                "inputs": {"natural_language_query": query},
                                "outputs": {
                                    "error": sql_response.error,
                                    "sql_query": sql_response.query,
                                    "status": "failed"
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace failed SQL query
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="query_incidents_database",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={"status": "failed"}
                            )
                        else:
                            context_text = f"SQL Query: {sql_response.query}\n\nResults ({sql_response.row_count} incidents):\n"
                            context_text += "\n".join([str(r) for r in sql_response.results[:20]])

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "query_incidents_database",
                                "inputs": {"natural_language_query": query},
                                "outputs": {
                                    "sql_query": sql_response.query,
                                    "row_count": sql_response.row_count,
                                    "sample_results": sql_response.results[:3],
                                    "status": "success"
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace successful SQL query
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="query_incidents_database",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={
                                    "status": "success",
                                    "table": "production_incidents"
                                }
                            )

                        conversation_history.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": "query_incidents_database",
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

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "search_web",
                                "inputs": {"search_query": query},
                                "outputs": {
                                    "error": search_response.error,
                                    "result_count": 0,
                                    "status": "failed"
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace failed web search
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="search_web",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={"status": "failed"}
                            )
                        else:
                            context_text = f"Web search: {query}\n\n"
                            for i, r in enumerate(search_response.results, 1):
                                context_text += f"{i}. {r.title}\n{r.content}\nSource: {r.url}\n\n"

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "search_web",
                                "inputs": {"search_query": query},
                                "outputs": {
                                    "result_count": search_response.result_count,
                                    "top_urls": [r.url for r in search_response.results[:5]],
                                    "top_titles": [r.title for r in search_response.results[:5]],
                                    "status": "success"
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace successful web search
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="search_web",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={
                                    "status": "success",
                                    "max_results": settings.WEB_SEARCH_MAX_RESULTS
                                }
                            )

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

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "analyze_document_with_subagent",
                                "inputs": {
                                    "task_description": task_description,
                                    "document_name": document_name
                                },
                                "outputs": {
                                    "error": "Document not found",
                                    "status": "failed"
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace failed subagent call
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="analyze_document_with_subagent",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={"user_id": user_id}
                            )
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

                            # Track tool call for summary
                            tool_call_info = {
                                "tool": "analyze_document_with_subagent",
                                "inputs": {
                                    "task_description": task_description,
                                    "document_name": document_name,
                                    "document_id": doc_response.data[0]["id"]
                                },
                                "outputs": {
                                    "status": result.status,
                                    "result_preview": result.result[:200] if result.result else None,
                                    "reasoning_steps_count": len(result.reasoning_steps),
                                    "error": result.error
                                }
                            }
                            tool_calls_summary.append(tool_call_info)

                            # Trace subagent execution
                            ChatService._trace_tool_call(
                                parent_run_id=run_id,
                                tool_name="analyze_document_with_subagent",
                                inputs=tool_call_info["inputs"],
                                outputs=tool_call_info["outputs"],
                                metadata={
                                    "parent_depth": 0,
                                    "user_id": user_id
                                }
                            )

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

        except Exception as e:
            error_occurred = e
            raise Exception(f"Failed to stream response: {str(e)}")

        finally:
            # Always close LangSmith trace
            if langsmith_enabled and langsmith_client and run_id:
                try:
                    from datetime import datetime, timezone
                    if error_occurred:
                        # Close with error
                        langsmith_client.update_run(
                            run_id=run_id,
                            error=str(error_occurred),
                            end_time=datetime.now(timezone.utc),
                        )
                    else:
                        # Close with success - include tool calls summary
                        langsmith_client.update_run(
                            run_id=run_id,
                            outputs={
                                "content": full_response,
                                "sources": sources,
                                "subagent_metadata": subagent_metadata,
                                "tool_calls": tool_calls_summary,
                                "tool_calls_count": len(tool_calls_summary)
                            },
                            end_time=datetime.now(timezone.utc),
                        )
                except Exception:
                    # If trace closure fails, don't break the response
                    pass


chat_service = ChatService()
