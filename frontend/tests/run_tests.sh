#!/bin/bash
# Run all automated frontend E2E tests (Playwright).
# Usage (from project root):  bash frontend/tests/run_tests.sh
# Usage (from frontend/tests): bash run_tests.sh
# Any extra args are forwarded to playwright, e.g.: bash run_tests.sh --headed
#
# Requires both servers to be available (playwright.config.ts starts them automatically).
# Backend .env is loaded by playwright.config.ts — no manual env setup needed.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "ERROR: node_modules not found. Run: npm install"
  exit 1
fi

echo "Running frontend E2E tests..."
npx playwright test "$@"
