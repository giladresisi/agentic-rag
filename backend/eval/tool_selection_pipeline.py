# backend/eval/tool_selection_pipeline.py
# Tool selection evaluation pipeline.
# Sends questions to the LLM with all 4 tools and captures which tool(s) the model calls.
# Single-turn: captures first tool call for routing accuracy scoring.
# Multi-turn: executes the full retrieve->analyze sequence with a real retrieval call.
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import settings
from services.provider_service import provider_service
from services.chat_service import ChatService

# RAGAS multi-turn message types for AgentGoalAccuracy scoring
from ragas.messages import HumanMessage, AIMessage, ToolMessage, ToolCall
from ragas.dataset_schema import MultiTurnSample

async def _stream_tool_calls(messages: list[dict]) -> list[dict]:
    """Stream one LLM call and accumulate tool_call deltas into a buffer.

    Returns a list of {name: str, args_str: str} dicts, one per tool call.
    Guards against OpenAI streaming quirks where tc_delta.function can be None.
    """
    buffer: list[dict] = []
    async for chunk in provider_service.stream_chat_completion(
        provider=settings.DEFAULT_PROVIDER,
        model=settings.DEFAULT_MODEL,
        messages=messages,
        base_url=settings.DEFAULT_BASE_URL,
        tools=ALL_TOOLS,
    ):
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                if tc_delta.function is None:
                    continue  # Guard: OpenAI can emit tool_call deltas before function is populated
                while len(buffer) <= tc_delta.index:
                    buffer.append({"name": "", "args_str": ""})
                buf = buffer[tc_delta.index]
                if tc_delta.function.name:
                    buf["name"] += tc_delta.function.name
                if tc_delta.function.arguments:
                    buf["args_str"] += tc_delta.function.arguments
        if chunk.choices[0].finish_reason in ("tool_calls", "stop"):
            break
    return buffer


def _parse_ragas_tool_calls(buffer: list[dict]) -> list[ToolCall]:
    """Convert accumulated delta buffer into RAGAS ToolCall objects."""
    result = []
    for buf in buffer:
        try:
            args = json.loads(buf["args_str"]) if buf["args_str"] else {}
        except json.JSONDecodeError:
            args = {}
        result.append(ToolCall(name=buf["name"], args=args))
    return result


# Copy system prompt verbatim from chat_service so eval uses production routing instructions
TOOL_SELECTION_SYSTEM_PROMPT = """You are a helpful assistant with access to multiple tools:

1. retrieve_documents: Search uploaded document content (semantic search, returns 5 relevant chunks)
2. query_deployments_database: Query a deployment and change management database with natural language (structured data queries)
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
      -> Returns chunks from: [doc1.pdf, doc2.md, doc3.txt]

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
- Query: "What does the document say about X?" -> retrieve_documents multiple times
- Query: "Find information about Y and Z" -> retrieve_documents for Y, then for Z
- Use when: User wants specific facts, quotes, or chunk-based information

PATTERN B - Retrieval + Subagents (for comprehensive analysis):
- Query: "Analyze documents for themes, specs, conclusions" -> Use TWO-STEP workflow below
- Query: "Summarize my documents" -> Use TWO-STEP workflow below
- Query: "What are the main points across all documents?" -> Use TWO-STEP workflow below
- TWO-STEP WORKFLOW:
  STEP 1: retrieve_documents(query="broad search to discover documents")
  STEP 2: For each unique document name in results:
          analyze_document_with_subagent(document_name="exact_filename.ext", task="...")
  NEVER guess document names - always use names from Step 1!

**Other Tools:**
- Deployment and change history: who deployed what, when, to which service, success/failure status, rollback counts, deployment frequency -> query_deployments_database
- Current events/recent info -> search_web (use after checking documents)
- Incomplete information? Make additional tool calls with refined queries

QUALITY STANDARDS:
- NEVER make up or fabricate information - only use data returned by tools
- NEVER guess or hallucinate document filenames - always use retrieve_documents to discover them
- If initial tool calls don't provide enough information, make additional calls
- Always attribute sources when using tools
- For subagent analysis, ONLY use document names returned by retrieve_documents
- If no tool results are relevant after multiple attempts, explain limitations to user
- Synthesize information from multiple tool calls into coherent answers"""

# All 4 tools the LLM can call -- imported from production ChatService definitions
ALL_TOOLS = [
    ChatService.RETRIEVAL_TOOL,
    ChatService.TEXT_TO_SQL_TOOL,
    ChatService.WEB_SEARCH_TOOL,
    ChatService.ANALYZE_DOCUMENT_TOOL,
]


async def run_tool_selection_pipeline(
    question: str,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> tuple[str | None, MultiTurnSample]:
    """Send question to LLM with all tools and capture the first tool call.

    Returns the tool name selected (or None if LLM answered directly) and a
    MultiTurnSample for AgentGoalAccuracy scoring.

    Args:
        question: The routing question to ask.
        user_id: Placeholder user ID (not used for retrieval in single-turn).
    """
    messages = [
        {"role": "system", "content": TOOL_SELECTION_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_buffer = await _stream_tool_calls(messages)
    ragas_tool_calls = _parse_ragas_tool_calls(tool_calls_buffer)

    actual_name = ragas_tool_calls[0].name if ragas_tool_calls else None

    # Build MultiTurnSample for AgentGoalAccuracy: [HumanMessage, AIMessage(tool_calls)]
    sample = MultiTurnSample(
        user_input=[
            HumanMessage(content=question),
            AIMessage(content="", tool_calls=ragas_tool_calls if ragas_tool_calls else None),
        ]
    )
    return actual_name, sample


async def run_multiturn_pipeline(
    question: str,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> tuple[list[str], MultiTurnSample]:
    """Execute the full 2-step retrieve->analyze agentic sequence.

    Step 1: LLM calls retrieve_documents.
    Step 2: Execute real retrieval, inject ToolMessage result.
    Step 3: LLM calls analyze_document_with_subagent.

    The LLM won't call analyze_document_with_subagent without seeing actual
    document names from a prior retrieval -- so a real RetrievalService call
    is mandatory here.

    Returns actual tool sequence (list of names) and a MultiTurnSample with
    all 4 messages for AgentGoalAccuracy scoring.

    Args:
        question: A question that should trigger retrieve->analyze sequence.
        user_id: User ID for retrieval RLS filtering.
    """
    from services.retrieval_service import RetrievalService

    messages = [
        {"role": "system", "content": TOOL_SELECTION_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    actual_sequence: list[str] = []
    ragas_messages = [HumanMessage(content=question)]

    # -- Step 1: First LLM call -- expect retrieve_documents ----------------
    tool_calls_buffer = await _stream_tool_calls(messages)

    if not tool_calls_buffer:
        # LLM answered directly -- no tool calls at all
        return actual_sequence, MultiTurnSample(user_input=ragas_messages)

    # Parse first tool call
    first_ragas_tcs = _parse_ragas_tool_calls(tool_calls_buffer)
    first_ragas_tc = first_ragas_tcs[0]
    first_tool_name = first_ragas_tc.name
    first_args = first_ragas_tc.args
    actual_sequence.append(first_tool_name)

    ragas_messages.append(AIMessage(content="", tool_calls=[first_ragas_tc]))

    if first_tool_name != "retrieve_documents":
        # Unexpected first tool -- return early with what we have
        return actual_sequence, MultiTurnSample(user_input=ragas_messages)

    # -- Step 2: Execute real retrieval -------------------------------------
    query_text = first_args.get("query", question)
    chunks = await RetrievalService.retrieve_relevant_chunks(
        query=query_text,
        user_id=user_id,
    )
    context_text = "\n\n".join([
        f"Document: {chunk['document_name']}\n{chunk['content']}"
        for chunk in chunks
    ])

    # Inject retrieval result as ToolMessage for RAGAS scoring
    ragas_messages.append(ToolMessage(content=context_text))

    # Build assistant tool_call message for conversation history
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_retrieve",
            "type": "function",
            "function": {"name": "retrieve_documents", "arguments": tool_calls_buffer[0]["args_str"]},
        }],
    })
    messages.append({
        "role": "tool",
        "tool_call_id": "call_retrieve",
        "content": context_text,
    })

    # -- Step 3: Second LLM call -- expect analyze_document_with_subagent ---
    tool_calls_buffer2 = await _stream_tool_calls(messages)

    if tool_calls_buffer2:
        second_ragas_tcs = _parse_ragas_tool_calls(tool_calls_buffer2)
        second_ragas_tc = second_ragas_tcs[0]
        actual_sequence.append(second_ragas_tc.name)
        ragas_messages.append(AIMessage(
            content="",
            tool_calls=[second_ragas_tc],
        ))

    return actual_sequence, MultiTurnSample(user_input=ragas_messages)
