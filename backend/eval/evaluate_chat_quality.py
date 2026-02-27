"""
Chat quality evaluation entry point.

Drives the real ChatService.stream_response() endpoint (full agentic loop:
tool selection -> retrieval -> synthesis) and scores with RAGAS metrics plus a
deterministic keyword check on the retrieval query arg chosen by the LLM.

Closes both coverage gaps from PROGRESS.md:
  1. Retrieval result quality for LLM-chosen args
  2. Final response quality for the real chat endpoint

Prerequisites:
  1. Postmortem docs uploaded via app UI (backend/eval/postmortems/*.md)
  2. LANGSMITH_API_KEY set in backend/.env
  3. Install eval deps: cd backend && uv pip install -r eval/requirements-eval.txt
  4. Run: cd backend && uv run python eval/evaluate_chat_quality.py

Note on Windows: pyarrow.dataset DLL may be blocked by Application Control.
The workaround below mocks pyarrow.dataset before importing ragas/datasets.
"""
import argparse
import asyncio
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

from eval.dataset import GOLDEN_DATASET
from eval.chat_quality_pipeline import run_chat_quality_pipeline
from eval.eval_utils import get_eval_user_id


async def collect_pipeline_results(user_id: str, limit: int | None = None) -> list[dict]:
    """Run the chat pipeline for all (or limited) golden questions and collect results."""
    samples = GOLDEN_DATASET[:limit] if limit else GOLDEN_DATASET
    total = len(samples)
    print(f"Running chat pipeline for {total} questions...")
    results = []
    for i, sample in enumerate(samples):
        print(f"  [{i+1:02d}/{total}] {sample.question[:55]}...")
        try:
            result = await run_chat_quality_pipeline(sample.question, user_id=user_id)
        except Exception as exc:
            result = {
                "question": sample.question,
                "answer": f"[PIPELINE ERROR: {exc}]",
                "contexts": [],
                "sources": [],
                "tool_name": None,
                "tool_args": {},
            }
        results.append(result)
        # Small delay between questions to avoid Supabase RPC rate limiting.
        # Mirrors the same protection in evaluate.py.
        if i < total - 1:
            await asyncio.sleep(2)
    return results


def score_keyword_relevance(pipeline_results: list[dict], samples) -> list[dict]:
    """Deterministic check: does the LLM's retrieval query arg contain required keywords?

    Free (no API calls). Run before RAGAS so arg quality is visible immediately.
    Returns 1.0 if any keyword matches, 0.0 if none match, None if no keywords defined.
    """
    for result, sample in zip(pipeline_results, samples):
        actual_query = result.get("tool_args", {}).get("query", "")
        keywords = sample.required_arg_keywords
        if not keywords:
            result["arg_keyword_relevance"] = None
        else:
            result["arg_keyword_relevance"] = (
                1.0 if any(kw.lower() in actual_query.lower() for kw in keywords) else 0.0
            )
    return pipeline_results


def build_ragas_dataset(pipeline_results: list[dict], samples):
    """Build RAGAS EvaluationDataset from pipeline results + golden ground truths."""
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    ragas_samples = [
        SingleTurnSample(
            user_input=sample.question,
            response=result["answer"],
            retrieved_contexts=result["contexts"],
            reference=sample.ground_truth,
        )
        for sample, result in zip(samples, pipeline_results, strict=True)
    ]
    return EvaluationDataset(samples=ragas_samples)


def run_ragas_scoring(dataset):
    """Run RAGAS evaluate with all 4 metrics (LLM-graded, ~60 API calls)."""
    from ragas import evaluate
    from ragas.metrics._faithfulness import faithfulness
    from ragas.metrics._answer_relevance import answer_relevancy
    from ragas.metrics._context_precision import context_precision
    from ragas.metrics._context_recall import context_recall
    from ragas.embeddings.base import embedding_factory
    from ragas.llms import LangchainLLMWrapper
    from ragas.run_config import RunConfig
    from langchain_openai import ChatOpenAI

    embeddings = embedding_factory("openai")
    # Explicit LLM with max_tokens=8192 to match evaluate.py.
    # Without this, RAGAS auto-creates an LLM with its default max_tokens (3072).
    # With RETRIEVAL_LIMIT=10, faithfulness prompts (10 chunks × ~1000 chars) exceed
    # 3072 tokens, causing instructor to retry 3× at ~5-6 min each.
    llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", max_tokens=8192))

    # Reduce strictness from 3→1: RAGAS requests n=strictness completions per sample.
    # Modern OpenAI APIs return only n=1, causing the "LLM returned 1 generations
    # instead of requested 3" warning and producing 0.000 for answer_relevancy.
    # With strictness=1 we get valid scores from the single generation we actually receive.
    answer_relevancy.strictness = 1

    # Limit concurrent API calls to avoid OpenAI rate-limit timeouts.
    # Default max_workers=16 fires 16 simultaneous requests; after ~30 jobs the TPM
    # limit is exhausted and remaining jobs fail with TimeoutError (returning NaN).
    # max_workers=4 keeps throughput reasonable while staying under rate limits.
    run_config = RunConfig(max_workers=4, timeout=180)

    print("\nScoring with RAGAS (LLM-graded -- takes 1-3 minutes)...")
    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=run_config,
    )


def print_results(score, pipeline_results: list[dict]):
    """Print RAGAS metrics table then keyword relevance summary. Returns DataFrame."""
    df = score.to_pandas()
    print("\n" + "=" * 65)
    print("CHAT QUALITY EVALUATION RESULTS")
    print("=" * 65)
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for col in metric_cols:
        if col in df.columns:
            mean = df[col].mean()
            print(f"  {col:<22}: {mean:.3f}")

    # Keyword relevance summary (deterministic, shown separately)
    kw_scores = [r["arg_keyword_relevance"] for r in pipeline_results if r["arg_keyword_relevance"] is not None]
    if kw_scores:
        passing = sum(1 for s in kw_scores if s == 1.0)
        total = len(kw_scores)
        mean_kw = sum(kw_scores) / total
        print(f"  {'arg_keyword_relevance':<22}: {mean_kw:.3f}   ({passing}/{total} pass)")
        failing = [
            r["question"][:60]
            for r in pipeline_results
            if r["arg_keyword_relevance"] == 0.0
        ]
        if failing:
            print("  failing:")
            for q in failing:
                print(f"    - {q}...")
    print("=" * 65)
    return df


def push_to_langsmith(df, pipeline_results: list[dict], experiment_name: str) -> None:
    """Push per-sample scores to LangSmith as dataset 'ir-copilot-chat-quality'."""
    from langsmith import Client
    client = Client()
    dataset_name = "ir-copilot-chat-quality"

    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        dataset = existing[0]
        print(f"  Using existing LangSmith dataset: {dataset_name}")
    else:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="IR-Copilot chat quality eval -- real ChatService endpoint, 15 Q&A pairs",
        )
        print(f"  Created LangSmith dataset: {dataset_name}")

    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for i, (_, row) in enumerate(df.iterrows()):
        pr = pipeline_results[i] if i < len(pipeline_results) else {}
        outputs = {
            "answer": row.get("answer", ""),
            "reference": row.get("reference", ""),
            "tool_name": pr.get("tool_name"),
            "tool_args": pr.get("tool_args", {}),
            "arg_keyword_relevance": pr.get("arg_keyword_relevance"),
        }
        # NaN-safe metric push
        for col in metric_cols:
            if col in row:
                val = row[col]
                outputs[col] = float(val) if val == val else None  # NaN check

        client.create_example(
            inputs={"question": row.get("user_input", row.get("question", ""))},
            outputs=outputs,
            dataset_id=dataset.id,
        )

    print(f"  Pushed {len(df)} examples to dataset: {dataset_name}")
    print(f"  Experiment label: {experiment_name}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Chat quality evaluation using real ChatService")
    parser.add_argument("--dry-run", action="store_true", help="Skip LangSmith push")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Limit to first N samples")
    args = parser.parse_args()

    user_id = get_eval_user_id()
    samples = GOLDEN_DATASET[:args.limit] if args.limit else GOLDEN_DATASET

    pipeline_results = await collect_pipeline_results(user_id, limit=args.limit)
    pipeline_results = score_keyword_relevance(pipeline_results, samples)
    dataset = build_ragas_dataset(pipeline_results, samples)
    score = run_ragas_scoring(dataset)
    df = print_results(score, pipeline_results)

    if not args.dry_run:
        try:
            push_to_langsmith(df, pipeline_results, experiment_name=f"chat-quality-eval-{date.today()}")
            print("\nDone. View results at: https://smith.langchain.com/")
        except Exception as e:
            print(f"\nWarning: LangSmith push failed ({e}). Scores printed above.")
    else:
        print("\nDry run complete -- LangSmith push skipped.")


if __name__ == "__main__":
    asyncio.run(main())
