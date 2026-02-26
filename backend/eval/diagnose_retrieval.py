"""
Diagnostic script for two eval issues:
  1. Why Q11 (INC-2024-031) returned HTTP headers instead of an answer.
  2. Why context_recall is low (0.411).

Run: cd backend && uv run python eval/diagnose_retrieval.py
"""
import asyncio
import os
import sys
from unittest.mock import MagicMock as _MagicMock

sys.modules.setdefault("pyarrow.dataset", _MagicMock())
sys.modules.setdefault("pyarrow._dataset", _MagicMock())

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.langsmith_service import setup_langsmith
setup_langsmith()

from eval.dataset import GOLDEN_DATASET
from eval.eval_utils import get_eval_user_id
from eval.pipeline import run_rag_pipeline
from services.retrieval_service import RetrievalService


def _ground_truth_keywords(ground_truth: str) -> list[str]:
    """Extract a few distinctive short phrases from the ground truth for coverage check."""
    # Split into ~5-word windows as rough coverage probes
    words = ground_truth.split()
    probes = []
    step = max(1, len(words) // 4)
    for i in range(0, len(words) - 3, step):
        probes.append(" ".join(words[i:i+4]).lower().strip(".,;:"))
    return probes[:4]


def context_covers_ground_truth(contexts: list[str], ground_truth: str) -> float:
    """Simple heuristic: how many 4-word probes from the ground truth appear in contexts?"""
    probes = _ground_truth_keywords(ground_truth)
    if not probes:
        return 0.0
    combined = " ".join(contexts).lower()
    hits = sum(1 for p in probes if p in combined)
    return hits / len(probes)


async def diagnose_q11(user_id: str) -> None:
    """Issue 1: reproduce Q11 and check whether retrieval raises or returns empty."""
    print("\n" + "=" * 65)
    print("ISSUE 1: Q11 (INC-2024-031) — HTTP headers investigation")
    print("=" * 65)

    q11 = GOLDEN_DATASET[10]  # 0-indexed
    print(f"Question: {q11.question}")
    print(f"Source:   {q11.source_doc}")

    # Test retrieval in isolation
    print("\n--- Retrieval only ---")
    try:
        chunks = await RetrievalService.retrieve_relevant_chunks(
            query=q11.question, user_id=user_id
        )
        print(f"  Retrieval OK: {len(chunks)} chunks returned")
        for i, c in enumerate(chunks):
            print(f"  [{i+1}] {c.get('document_name', '?')}  sim={c.get('similarity', 0):.3f}  "
                  f"len={len(c.get('content',''))} chars")
    except Exception as e:
        print(f"  Retrieval FAILED: {type(e).__name__}: {str(e)[:300]}")
        print("  *** This is the root cause of the HTTP-headers issue ***")
        print("  *** The outer evaluate.py handler caught this exception and put it in the answer ***")

    # Run full pipeline (catches exceptions internally)
    print("\n--- Full pipeline (as evaluate.py calls it) ---")
    try:
        result = await run_rag_pipeline(q11.question, user_id=user_id)
        print(f"  Answer: {result['answer'][:200]}")
        print(f"  Contexts: {len(result['contexts'])} chunks")
        if not result["contexts"]:
            print("  *** contexts=[] means the outer evaluate.py handler will record this ***")
            print("  *** with '[PIPELINE ERROR: ...]' as the answer, which may include raw HTTP headers ***")
    except Exception as e:
        print(f"  Pipeline raised: {type(e).__name__}: {str(e)[:300]}")
        print("  *** evaluate.py outer handler catches this → contexts=[], answer=[PIPELINE ERROR:...] ***")


async def diagnose_context_recall(user_id: str) -> None:
    """Issue 2: per-question context coverage analysis to find where recall is lost."""
    print("\n" + "=" * 65)
    print("ISSUE 2: Context recall — per-question coverage analysis")
    print("=" * 65)
    print(f"{'#':>2}  {'Question (short)':<42}  {'Chunks':>6}  {'Coverage':>8}")
    print("-" * 65)

    total_coverage = 0.0
    zero_context_count = 0
    low_coverage = []

    for i, sample in enumerate(GOLDEN_DATASET):
        try:
            chunks = await RetrievalService.retrieve_relevant_chunks(
                query=sample.question, user_id=user_id
            )
            contexts = [c.get("content", "") for c in chunks if c.get("content")]
        except Exception as e:
            contexts = []
            print(f"{i+1:>2}  {sample.question[:42]:<42}  {'ERROR':>6}  {'0.00':>8}  !! {str(e)[:60]}")
            zero_context_count += 1
            total_coverage += 0.0
            low_coverage.append((i + 1, sample.question[:55], 0, 0.0, f"RETRIEVAL ERROR: {str(e)[:60]}"))
            continue

        coverage = context_covers_ground_truth(contexts, sample.ground_truth)
        total_coverage += coverage

        flag = ""
        if not contexts:
            zero_context_count += 1
            flag = "  ** NO CONTEXTS **"
        elif coverage < 0.5:
            flag = "  < low"

        print(f"{i+1:>2}  {sample.question[:42]:<42}  {len(contexts):>6}  {coverage:>8.2f}{flag}")

        if coverage < 0.5 or not contexts:
            low_coverage.append((i + 1, sample.question[:55], len(contexts), coverage, ""))

    avg = total_coverage / len(GOLDEN_DATASET)
    print("-" * 65)
    print(f"    Average heuristic coverage: {avg:.3f}  |  Zero-context samples: {zero_context_count}")

    if low_coverage:
        print("\n--- Low coverage samples — top retrieved docs ---")
        for q_num, q_text, n_chunks, cov, note in low_coverage:
            print(f"\nQ{q_num}: {q_text}")
            if note:
                print(f"  {note}")
                continue
            print(f"  Coverage: {cov:.2f}  Chunks: {n_chunks}")
            try:
                sample = GOLDEN_DATASET[q_num - 1]
                chunks = await RetrievalService.retrieve_relevant_chunks(
                    query=sample.question, user_id=user_id
                )
                doc_names = list({c.get("document_name", "?") for c in chunks})
                print(f"  Retrieved from: {doc_names}")
                print(f"  Ground truth probe words:")
                probes = _ground_truth_keywords(sample.ground_truth)
                combined = " ".join(c.get("content", "") for c in chunks).lower()
                for p in probes:
                    found = "FOUND" if p in combined else "MISSING"
                    print(f"    [{found}] '{p}'")
            except Exception as e:
                print(f"  Could not re-fetch chunks: {e}")


async def main() -> None:
    user_id = get_eval_user_id()
    await diagnose_q11(user_id)
    await diagnose_context_recall(user_id)
    print("\nDiagnosis complete.")


if __name__ == "__main__":
    asyncio.run(main())
