#!/bin/bash
# Script to start backend server with venv activation
# Can be run from start_scripts directory

# Get script directory and navigate to backend root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.." || exit 1

echo "Working directory: $(pwd)"
echo ""

uv run uvicorn main:app --host 0.0.0.0 --port 8000
