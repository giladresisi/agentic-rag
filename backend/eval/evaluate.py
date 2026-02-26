"""
RAGAS evaluation entry point.

Runs 15 golden Q&A pairs through the RAG pipeline, scores them with RAGAS,
and pushes per-sample results to LangSmith as dataset 'ir-copilot-golden-set'.

Prerequisites:
  1. Postmortem docs uploaded via app UI (backend/eval/postmortems/*.md)
  2. LANGSMITH_API_KEY set in backend/.env
  3. Install eval deps: cd backend && uv pip install -r eval/requirements-eval.txt
  4. Run: cd backend && uv run python eval/evaluate.py

Note on Windows: pyarrow.dataset DLL may be blocked by Application Control.
The workaround below mocks pyarrow.dataset before importing ragas/datasets.
This does not affect evaluation correctness — RAGAS 0.4.x uses EvaluationDataset,
not pyarrow.dataset, for its evaluation logic.
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
from eval.pipeline import run_rag_pipeline
from eval.eval_utils import get_eval_user_id


async def collect_pipeline_results(user_id: str) -> list[dict]:
    """Run the RAG pipeline for all golden questions and collect results.

    Cohere free-tier note: the Cohere rerank API allows 10 requests/minute.
    Each question triggers one rerank call, so 15 questions exhausts the limit
    at question 11 with a 429 error. If RERANKING_PROVIDER=cohere and you are
    on the free tier, slice the dataset to at most 10 questions before running:

        # In this function, replace GOLDEN_DATASET with GOLDEN_DATASET[:10]

    The recommended alternative is RERANKING_PROVIDER=local in backend/.env,
    which uses an on-device cross-encoder with no rate limits.
    """
    print(f"Running pipeline for {len(GOLDEN_DATASET)} questions...")
    results = []
    for i, sample in enumerate(GOLDEN_DATASET):
        print(f"  [{i+1:02d}/{len(GOLDEN_DATASET)}] {sample.question[:55]}...")
        try:
            result = await run_rag_pipeline(sample.question, user_id=user_id)
        except Exception as exc:
            result = {"question": sample.question, "answer": f"[PIPELINE ERROR: {exc}]", "contexts": []}
        results.append(result)
    return results


def build_ragas_dataset(pipeline_results: list[dict]):
    """Build RAGAS EvaluationDataset from pipeline results + golden ground truths.

    RAGAS 0.4.x API: uses SingleTurnSample + EvaluationDataset instead of
    the legacy HuggingFace Dataset.from_dict() approach from RAGAS 0.1.x.
    """
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    samples = [
        SingleTurnSample(
            user_input=sample.question,
            response=result["answer"],
            retrieved_contexts=result["contexts"],
            reference=sample.ground_truth,
        )
        for sample, result in zip(GOLDEN_DATASET, pipeline_results, strict=True)
    ]
    return EvaluationDataset(samples=samples)


def run_ragas_scoring(dataset):
    """Run RAGAS evaluate with all 4 metrics.

    Uses legacy metric singleton instances (ragas.metrics._* modules) which are
    pre-instantiated Metric objects compatible with ragas.evaluate().
    ragas.metrics.collections contains a parallel new API with a different base
    class that is NOT compatible with evaluate() — do not use it here.

    embeddings= is required for answer_relevancy (MetricWithEmbeddings).
    Uses embedding_factory("openai") which picks up OPENAI_API_KEY from env.

    Scores are LLM-graded — expects ~60 OpenAI API calls for 15 questions.
    """
    from ragas import evaluate
    from ragas.metrics._faithfulness import faithfulness
    from ragas.metrics._answer_relevance import answer_relevancy
    from ragas.metrics._context_precision import context_precision
    from ragas.metrics._context_recall import context_recall
    from ragas.embeddings.base import embedding_factory

    embeddings = embedding_factory("openai")

    # Reduce strictness from 3→1: RAGAS requests n=strictness completions per sample.
    # Modern OpenAI APIs return only n=1, causing the "LLM returned 1 generations
    # instead of requested 3" warning and producing 0.000 for answer_relevancy.
    # With strictness=1 we get valid scores from the single generation we actually receive.
    answer_relevancy.strictness = 1

    print("\nScoring with RAGAS (LLM-graded -- takes 1-3 minutes)...")
    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        embeddings=embeddings,
    )


def print_results(result) -> object:
    """Print a summary table and return the pandas DataFrame for LangSmith upload."""
    df = result.to_pandas()
    print("\n" + "=" * 65)
    print("EVALUATION RESULTS")
    print("=" * 65)
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for col in metric_cols:
        if col in df.columns:
            mean = df[col].mean()
            print(f"  {col:<22}: {mean:.3f}")
    print("=" * 65)
    return df


def push_to_langsmith(df, experiment_name: str) -> None:
    """Push per-sample scores to LangSmith as a dataset + examples."""
    from langsmith import Client
    client = Client()
    dataset_name = "ir-copilot-golden-set"

    # Reuse existing dataset or create it fresh
    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        dataset = existing[0]
        print(f"  Using existing LangSmith dataset: {dataset_name}")
    else:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="IR-Copilot RAG golden evaluation set — 15 postmortem Q&A pairs",
        )
        print(f"  Created LangSmith dataset: {dataset_name}")

    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for _, row in df.iterrows():
        outputs = {
            "answer": row.get("answer", ""),
            "reference": row.get("reference", ""),
        }
        # NaN-safe metric push (RAGAS may return NaN for skipped samples)
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
    parser = argparse.ArgumentParser(description="RAG pipeline evaluation using RAGAS")
    parser.add_argument("--dry-run", action="store_true", help="Skip LangSmith push")
    args = parser.parse_args()

    user_id = get_eval_user_id()
    pipeline_results = await collect_pipeline_results(user_id)
    dataset = build_ragas_dataset(pipeline_results)
    score = run_ragas_scoring(dataset)
    df = print_results(score)

    if not args.dry_run:
        try:
            push_to_langsmith(df, experiment_name=f"rag-eval-{date.today()}")
            print("\nDone. View results at: https://smith.langchain.com/")
        except Exception as e:
            print(f"\nWarning: LangSmith push failed ({e}). Scores printed above.")
    else:
        print("\nDry run complete — LangSmith push skipped.")


if __name__ == "__main__":
    asyncio.run(main())
