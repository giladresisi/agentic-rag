#!/bin/bash
# Run all automated backend tests (pytest).
# Usage (from project root):  bash backend/tests/run_tests.sh
# Usage (from backend/tests): bash run_tests.sh
# Any extra args are forwarded to pytest, e.g.: bash run_tests.sh -k test_auth -v

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

if ! command -v uv &>/dev/null; then
  echo "ERROR: uv not found. Install from https://docs.astral.sh/uv/"
  exit 1
fi

echo "Running backend tests..."
uv run pytest tests/auto/ "$@"
