# backend/eval/tool_selection_dataset.py
# Tool selection evaluation dataset.
# Provides single-turn and multi-turn samples for scoring LLM routing accuracy.
# Single-turn: 12 questions across retrieve, sql, and web_search tools.
# Multi-turn: 3 retrieve→analyze sequences that test agentic chaining.
from dataclasses import dataclass
from typing import List


@dataclass
class ToolSelectionSample:
    question: str
    expected_tool: str         # exact function name
    category: str              # "retrieve" | "sql" | "web"
    reference_goal: str        # AgentGoalAccuracy reference — what a correct tool call should accomplish
    required_arg_keywords: List[str]  # deterministic check: at least one must appear in the query arg (case-insensitive)


@dataclass
class MultiTurnSelectionSample:
    question: str
    expected_sequence: List[str]  # ordered list of tool names
    category: str        # "retrieve_then_analyze"
    reference_goal: str  # AgentGoalAccuracy reference — what the full sequence should accomplish


# 12 single-turn samples: 4 per tool category
TOOL_SELECTION_DATASET: List[ToolSelectionSample] = [
    # ── retrieve_documents (postmortem knowledge base questions) ──────────────
    ToolSelectionSample(
        question="What was the root cause of the INC-2024-003 auth service outage?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-003 with a query targeting the root cause of the auth outage",
        required_arg_keywords=["INC-2024-003", "auth", "root cause", "outage"],
    ),
    ToolSelectionSample(
        question="What monitoring gap allowed the auth outage to go undetected for 6 minutes?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-003 with a query targeting the monitoring or detection gap",
        required_arg_keywords=["INC-2024-003", "monitor", "detect", "auth", "gap"],
    ),
    ToolSelectionSample(
        question="How was the INC-2024-038 failed deployment rollback resolved?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-038 with a query targeting resolution or remediation steps",
        required_arg_keywords=["INC-2024-038", "deploy", "rollback", "resolv", "remediat"],
    ),
    ToolSelectionSample(
        question="What caused the API gateway timeout cascade in INC-2024-027?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-027 with a query targeting the API gateway timeout root cause",
        required_arg_keywords=["INC-2024-027", "gateway", "timeout", "cascade", "API"],
    ),
    # ── query_incidents_database (structured data queries) ────────────────────
    ToolSelectionSample(
        question="Which incidents had a severity of P1?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents filtered by severity='P1' to return P1 incidents",
        required_arg_keywords=["P1", "severity", "critical"],
    ),
    ToolSelectionSample(
        question="What is the average resolution time across all incidents?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents to compute AVG(resolution_time_minutes) across all rows",
        required_arg_keywords=["average", "avg", "resolution time", "resolution_time"],
    ),
    ToolSelectionSample(
        question="Which incidents affected the payment service?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents filtered by affected_service='payment'",
        required_arg_keywords=["payment"],
    ),
    ToolSelectionSample(
        question="List all incidents sorted by detection gap in minutes.",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents ordered by detection_gap_minutes",
        required_arg_keywords=["detection", "gap", "sort", "order"],
    ),
    # ── search_web (real-time / current events) ───────────────────────────────
    ToolSelectionSample(
        question="What is the current weather in London right now today?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for current real-time weather conditions in London",
        required_arg_keywords=["weather", "London"],
    ),
    ToolSelectionSample(
        question="What are the latest technology news headlines today?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for today's technology news headlines",
        required_arg_keywords=["tech", "news", "headline", "technology", "latest"],
    ),
    ToolSelectionSample(
        question="What happened in the tech industry this week?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for recent tech industry news from the current week",
        required_arg_keywords=["tech", "industry", "week", "news"],
    ),
    ToolSelectionSample(
        question="What is the current Bitcoin price?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for the current live Bitcoin price",
        required_arg_keywords=["Bitcoin", "BTC", "price", "crypto"],
    ),
]


# 3 multi-turn samples: retrieve_documents → analyze_document_with_subagent
MULTI_TURN_DATASET: List[MultiTurnSelectionSample] = [
    MultiTurnSelectionSample(
        question="Analyze the INC-2024-003 auth outage document in detail and extract all action items.",
        expected_sequence=["retrieve_documents", "analyze_document_with_subagent"],
        category="retrieve_then_analyze",
        reference_goal="First retrieve documents about INC-2024-003, then delegate deep analysis to the subagent tool",
    ),
    MultiTurnSelectionSample(
        question="Give me a comprehensive summary of the payment database corruption incident.",
        expected_sequence=["retrieve_documents", "analyze_document_with_subagent"],
        category="retrieve_then_analyze",
        reference_goal="First retrieve documents about INC-2024-011 payment DB corruption, then delegate analysis to the subagent tool",
    ),
    MultiTurnSelectionSample(
        question="Analyze the memory leak incident document and explain the detection gap.",
        expected_sequence=["retrieve_documents", "analyze_document_with_subagent"],
        category="retrieve_then_analyze",
        reference_goal="First retrieve documents about INC-2024-019 memory leak, then delegate analysis to the subagent tool",
    ),
]
