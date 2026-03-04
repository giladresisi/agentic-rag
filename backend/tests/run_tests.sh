#!/bin/bash
# Run all automated backend tests (pytest).
# Usage (from project root):  bash backend/tests/run_tests.sh
# Usage (from backend/tests): bash run_tests.sh
# Options:
#   --include-evals   Also run eval integration tests (requires EVAL_DOCS_INGESTED=true in backend/.env)
# Any other args are forwarded to pytest, e.g.: bash run_tests.sh -k test_auth -v

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

if ! command -v uv &>/dev/null; then
  echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/"
  exit 1
fi

INCLUDE_EVALS=false
EXTRA_ARGS=()

for arg in "$@"; do
  if [[ "$arg" == "--include-evals" ]]; then
    INCLUDE_EVALS=true
  else
    EXTRA_ARGS+=("$arg")
  fi
done

if $INCLUDE_EVALS; then
  EVAL_FLAG=$(grep -E '^EVAL_DOCS_INGESTED=' .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
  if [[ "$EVAL_FLAG" != "true" ]]; then
    echo "WARNING: EVAL_DOCS_INGESTED is not set to 'true' in backend/.env."
    echo "         Eval integration tests require this to run — they will be skipped."
    echo "         Set EVAL_DOCS_INGESTED=true in backend/.env to enable them."
    echo ""
  fi
  echo "Running backend tests (including eval integration tests)..."
  uv run pytest tests/auto/ eval/tests/ "${EXTRA_ARGS[@]}"
else
  echo "Running backend tests..."
  uv run pytest tests/auto/ "${EXTRA_ARGS[@]}"
fi
