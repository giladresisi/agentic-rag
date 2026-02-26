#!/bin/bash
# Run all three RAGAS evaluation pipelines in sequence.
#
# Usage (from project root):  bash backend/eval/run_evals.sh [--dry-run]
# Usage (from backend/):      bash eval/run_evals.sh [--dry-run]
#
# Options:
#   --dry-run   Print scores but skip LangSmith push (no API cost for scoring)
#
# Prerequisites:
#   - Postmortem docs uploaded via app UI (backend/eval/postmortems/*.md)
#   - TEST_EMAIL / TEST_PASSWORD set in backend/.env
#   - LANGSMITH_API_KEY set in backend/.env (skipped with --dry-run)
#   - Eval deps installed: cd backend && uv pip install -r eval/requirements-eval.txt

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

DRY_RUN_FLAG=""
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN_FLAG="--dry-run"
  fi
done

echo "================================================================"
echo " IR-Copilot RAGAS Evaluation Suite"
echo "================================================================"
echo ""

echo "===== [1/3] RAG Pipeline Eval (evaluate.py) ====="
uv run python eval/evaluate.py $DRY_RUN_FLAG

echo ""
echo "===== [2/3] Tool Selection Eval (evaluate_tool_selection.py) ====="
uv run python eval/evaluate_tool_selection.py $DRY_RUN_FLAG

echo ""
echo "===== [3/3] Chat Quality Eval (evaluate_chat_quality.py) ====="
uv run python eval/evaluate_chat_quality.py $DRY_RUN_FLAG

echo ""
echo "================================================================"
echo " All 3 evals complete."
echo "================================================================"
