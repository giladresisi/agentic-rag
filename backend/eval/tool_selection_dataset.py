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
    expected_tool: str   # exact function name
    category: str        # "retrieve" | "sql" | "web"
    reference_goal: str  # AgentGoalAccuracy reference — what a correct tool call should accomplish


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
    ),
    ToolSelectionSample(
        question="What monitoring gap allowed the auth outage to go undetected for 6 minutes?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-003 with a query targeting the monitoring or detection gap",
    ),
    ToolSelectionSample(
        question="How was the INC-2024-038 failed deployment rollback resolved?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-038 with a query targeting resolution or remediation steps",
    ),
    ToolSelectionSample(
        question="What caused the API gateway timeout cascade in INC-2024-027?",
        expected_tool="retrieve_documents",
        category="retrieve",
        reference_goal="Retrieve documents about INC-2024-027 with a query targeting the API gateway timeout root cause",
    ),
    # ── query_incidents_database (structured data queries) ────────────────────
    ToolSelectionSample(
        question="Which incidents had a severity of P1?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents filtered by severity='P1' to return P1 incidents",
    ),
    ToolSelectionSample(
        question="What is the average resolution time across all incidents?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents to compute AVG(resolution_time_minutes) across all rows",
    ),
    ToolSelectionSample(
        question="Which incidents affected the payment service?",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents filtered by affected_service='payment'",
    ),
    ToolSelectionSample(
        question="List all incidents sorted by detection gap in minutes.",
        expected_tool="query_incidents_database",
        category="sql",
        reference_goal="Query production_incidents ordered by detection_gap_minutes",
    ),
    # ── search_web (real-time / current events) ───────────────────────────────
    ToolSelectionSample(
        question="What is the current weather in London right now today?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for current real-time weather conditions in London",
    ),
    ToolSelectionSample(
        question="What are the latest technology news headlines today?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for today's technology news headlines",
    ),
    ToolSelectionSample(
        question="What happened in the tech industry this week?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for recent tech industry news from the current week",
    ),
    ToolSelectionSample(
        question="What is the current Bitcoin price?",
        expected_tool="search_web",
        category="web",
        reference_goal="Search the web for the current live Bitcoin price",
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
