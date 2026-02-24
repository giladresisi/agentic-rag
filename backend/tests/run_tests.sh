#!/bin/bash
# Run all automated backend tests (pytest).
# Usage (from project root):  bash backend/tests/run_tests.sh
# Usage (from backend/tests): bash run_tests.sh
# Any extra args are forwarded to pytest, e.g.: bash run_tests.sh -k test_auth -v

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

if [ ! -f "venv/Scripts/python" ]; then
  echo "ERROR: venv not found. Run: python -m venv venv && venv/Scripts/pip install -r requirements.txt"
  exit 1
fi

echo "Running backend tests..."
venv/Scripts/python -m pytest tests/auto/ "$@"
