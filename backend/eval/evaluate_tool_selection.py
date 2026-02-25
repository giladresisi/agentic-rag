"""
Tool selection evaluation entry point.

Scores the LLM's routing accuracy across 3 passes:
  Pass 1: tool_routing_accuracy — did the model call the right tool? (12 single-turn)
  Pass 2: sequence_accuracy — did the model use the correct 2-step sequence? (3 multi-turn)
  Pass 3: arg_quality via RAGAS AgentGoalAccuracy — did the args accomplish the goal? (all 15)

Run: cd backend && uv run python eval/evaluate_tool_selection.py
     cd backend && uv run python eval/evaluate_tool_selection.py --dry-run
     cd backend && uv run python eval/evaluate_tool_selection.py --dry-run --single-only
"""
import asyncio
import argparse
import os
import sys
from datetime import date

# pyarrow.dataset DLL is blocked by Windows Application Control policy.
# Mock it before ragas/datasets are imported so the rest of pyarrow works fine.
from unittest.mock import MagicMock as _MagicMock
sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.langsmith_service import setup_langsmith
setup_langsmith()

from eval.tool_selection_dataset import TOOL_SELECTION_DATASET, MULTI_TURN_DATASET
from eval.tool_selection_pipeline import run_tool_selection_pipeline, run_multiturn_pipeline
from eval.eval_utils import get_eval_user_id


async def collect_single_turn_results(user_id: str) -> list[dict]:
    """Run all 12 single-turn samples and collect routing accuracy results."""
    print(f"Running single-turn pipeline for {len(TOOL_SELECTION_DATASET)} questions...")
    results = []
    for i, sample in enumerate(TOOL_SELECTION_DATASET):
        print(f"  [{i+1:02d}/{len(TOOL_SELECTION_DATASET)}] {sample.question[:60]}...")
        try:
            actual_name, multi_turn = await run_tool_selection_pipeline(
                sample.question, user_id
            )
        except Exception as exc:
            print(f"    [ERROR] {exc}")
            actual_name, multi_turn = None, None
        correct = int(actual_name == sample.expected_tool)

        # Extract the actual query arg for deterministic keyword relevance check
        actual_query = ""
        if multi_turn and multi_turn.user_input[1].tool_calls:
            actual_query = multi_turn.user_input[1].tool_calls[0].args.get("query", "")

        results.append({
            "question": sample.question,
            "expected_tool": sample.expected_tool,
            "actual_tool": actual_name,
            "category": sample.category,
            "tool_routing_accuracy": correct,
            "_multi_turn": multi_turn,
            "_reference_goal": sample.reference_goal,
            "_actual_query": actual_query,
            "_required_arg_keywords": sample.required_arg_keywords,
        })
    return results


async def collect_multiturn_results(user_id: str) -> list[dict]:
    """Run all 3 multi-turn samples and collect sequence accuracy results."""
    print(f"Running multi-turn pipeline for {len(MULTI_TURN_DATASET)} sequences...")
    results = []
    for i, sample in enumerate(MULTI_TURN_DATASET):
        print(f"  [{i+1:02d}/{len(MULTI_TURN_DATASET)}] {sample.question[:60]}...")
        try:
            actual_seq, multi_turn = await run_multiturn_pipeline(
                sample.question, user_id
            )
        except Exception as exc:
            print(f"    [ERROR] {exc}")
            actual_seq, multi_turn = [], None
        correct = int(actual_seq == sample.expected_sequence)
        results.append({
            "question": sample.question,
            "expected_sequence": sample.expected_sequence,
            "actual_sequence": actual_seq,
            "category": sample.category,
            "sequence_accuracy": correct,
            "_multi_turn": multi_turn,
            "_reference_goal": sample.reference_goal,
        })
    return results


def score_arg_keyword_relevance(single_results: list[dict]) -> list[dict]:
    """Deterministic check: does the LLM's query arg contain at least one required keyword?

    Applied only to single-turn results (which carry _actual_query and _required_arg_keywords).
    Multi-turn results are not passed here and do not get this score.

    Catches the most common arg quality failures:
    - Empty query arg (LLM called the right tool but passed no meaningful query)
    - Completely off-topic query (right tool, wrong domain — e.g. querying "London weather"
      when asked about INC-2024-003)

    This is a necessary complement to AgentGoalAccuracy: the LLM judge can miss obvious
    failures when broad reference_goals give it too much latitude. Keywords are
    domain-specific and cannot be satisfied by accident.
    """
    for r in single_results:
        actual_query = r.pop("_actual_query", "")
        keywords = r.pop("_required_arg_keywords", [])
        if not keywords:
            r["arg_keyword_relevance"] = None
            continue
        query_lower = actual_query.lower()
        match = any(kw.lower() in query_lower for kw in keywords)
        r["arg_keyword_relevance"] = 1.0 if match else 0.0
    return single_results


async def score_arg_quality(all_results: list[dict]) -> list[dict]:
    """Score all 15 samples with RAGAS AgentGoalAccuracy (LLM-graded, ~15 API calls)."""
    from ragas.metrics.collections.agent_goal_accuracy.metric import AgentGoalAccuracyWithReference
    from ragas.llms.base import llm_factory
    from openai import AsyncOpenAI

    # gpt-4o-mini for cost-efficient LLM grading of arg quality
    metric = AgentGoalAccuracyWithReference(
        llm=llm_factory("gpt-4o-mini", client=AsyncOpenAI())
    )
    print(f"Scoring arg quality with AgentGoalAccuracy for {len(all_results)} samples...")
    for i, r in enumerate(all_results):
        multi_turn = r.pop("_multi_turn")
        reference_goal = r.pop("_reference_goal")
        print(f"  [{i+1:02d}/{len(all_results)}] {r['question'][:50]}...")
        if multi_turn is None:
            r["arg_quality"] = 0.0
            continue
        try:
            result = await metric.ascore(
                user_input=multi_turn.user_input,
                reference=reference_goal,
            )
            r["arg_quality"] = float(result.value)
        except Exception as exc:
            print(f"    [ERROR scoring arg_quality] {exc}")
            r["arg_quality"] = 0.0
    return all_results


def print_summary(single_results: list[dict], multi_results: list[dict], all_results: list[dict]) -> None:
    """Print formatted evaluation summary."""
    print("\n" + "=" * 64)
    print("Tool Selection Evaluation")
    print("=" * 64)

    # Single-turn routing accuracy by category
    if single_results:
        single_overall = sum(r["tool_routing_accuracy"] for r in single_results) / len(single_results)
        categories = ["retrieve", "sql", "web"]
        print(f"\nSingle-turn routing accuracy ({len(single_results)} samples):")
        print(f"  overall  : {single_overall:.3f}")
        for cat in categories:
            cat_results = [r for r in single_results if r["category"] == cat]
            if cat_results:
                cat_score = sum(r["tool_routing_accuracy"] for r in cat_results) / len(cat_results)
                correct = sum(r["tool_routing_accuracy"] for r in cat_results)
                print(f"  {cat:<8} : {cat_score:.3f}   ({correct}/{len(cat_results)})")

    # Arg keyword relevance (deterministic, single-turn only)
    kw_results = [r for r in single_results if r.get("arg_keyword_relevance") is not None]
    if kw_results:
        kw_overall = sum(r["arg_keyword_relevance"] for r in kw_results) / len(kw_results)
        print(f"\nArg keyword relevance / deterministic ({len(kw_results)} single-turn samples):")
        print(f"  overall  : {kw_overall:.3f}")
        for cat in ["retrieve", "sql", "web"]:
            cat_kw = [r for r in kw_results if r["category"] == cat]
            if cat_kw:
                cat_score = sum(r["arg_keyword_relevance"] for r in cat_kw) / len(cat_kw)
                correct = int(sum(r["arg_keyword_relevance"] for r in cat_kw))
                print(f"  {cat:<8} : {cat_score:.3f}   ({correct}/{len(cat_kw)})")
        failing = [r for r in kw_results if r["arg_keyword_relevance"] == 0.0]
        if failing:
            print(f"  failing samples:")
            for r in failing:
                print(f"    - [{r['category']}] {r['question'][:55]}...")
                print(f"      actual query arg: {r.get('actual_tool', '?')} -> (see LangSmith for full args)")

    # Multi-turn sequence accuracy
    if multi_results:
        multi_overall = sum(r["sequence_accuracy"] for r in multi_results) / len(multi_results)
        correct_multi = sum(r["sequence_accuracy"] for r in multi_results)
        print(f"\nMulti-turn sequence accuracy ({len(multi_results)} samples):")
        print(f"  retrieve -> analyze : {multi_overall:.3f}   ({correct_multi}/{len(multi_results)})")

    # Arg quality from AgentGoalAccuracy (LLM judge, all 15 samples)
    if all_results and "arg_quality" in all_results[0]:
        arg_overall = sum(r["arg_quality"] for r in all_results) / len(all_results)
        print(f"\nArg quality / AgentGoalAccuracy LLM judge ({len(all_results)} samples):")
        print(f"  overall  : {arg_overall:.3f}")

    print("=" * 64)


def push_to_langsmith(single_results: list[dict], multi_results: list[dict], experiment_name: str) -> None:
    """Push per-sample scores to LangSmith as dataset 'ir-copilot-tool-selection'."""
    from langsmith import Client
    client = Client()
    dataset_name = "ir-copilot-tool-selection"

    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        dataset = existing[0]
        print(f"  Using existing LangSmith dataset: {dataset_name}")
    else:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="IR-Copilot tool selection evaluation — routing accuracy across 15 questions",
        )
        print(f"  Created LangSmith dataset: {dataset_name}")

    for r in single_results:
        client.create_example(
            inputs={"question": r["question"], "expected_tool": r["expected_tool"], "category": r["category"]},
            outputs={
                "actual_tool": r["actual_tool"],
                "tool_routing_accuracy": r["tool_routing_accuracy"],
                "arg_keyword_relevance": r.get("arg_keyword_relevance"),
                "arg_quality": r.get("arg_quality"),
            },
            dataset_id=dataset.id,
        )

    for r in multi_results:
        client.create_example(
            inputs={"question": r["question"], "expected_sequence": r["expected_sequence"], "category": r["category"]},
            outputs={
                "actual_sequence": r["actual_sequence"],
                "sequence_accuracy": r["sequence_accuracy"],
                "arg_quality": r.get("arg_quality"),
            },
            dataset_id=dataset.id,
        )

    print(f"  Pushed {len(single_results) + len(multi_results)} examples to dataset: {dataset_name}")
    print(f"  Experiment label: {experiment_name}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Tool selection evaluation")
    parser.add_argument("--dry-run", action="store_true", help="Skip LangSmith push")
    parser.add_argument("--single-only", action="store_true", help="Skip multi-turn pipeline")
    args = parser.parse_args()

    user_id = get_eval_user_id()

    single_results = await collect_single_turn_results(user_id)

    multi_results = []
    if not args.single_only:
        multi_results = await collect_multiturn_results(user_id)

    # Pass 3a: deterministic keyword check (single-turn only, no API calls)
    single_results = score_arg_keyword_relevance(single_results)

    # Pass 3b: LLM-judge arg quality (all 15 samples via AgentGoalAccuracy)
    all_results = await score_arg_quality(single_results + multi_results)

    print_summary(single_results, multi_results, all_results)

    if not args.dry_run:
        push_to_langsmith(single_results, multi_results, experiment_name=f"tool-selection-eval-{date.today()}")
        print("\nDone. View results at: https://smith.langchain.com/")
    else:
        print("\nDry run — LangSmith push skipped.")


if __name__ == "__main__":
    asyncio.run(main())
