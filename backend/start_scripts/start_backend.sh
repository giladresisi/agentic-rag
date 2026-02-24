#!/bin/bash
# Script to start backend server after killing any existing processes on port 8000
# Can be run from start_scripts directory

# Get script directory and navigate to backend root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.." || exit 1

echo "=== Starting Backend Server ==="
echo "Working directory: $(pwd)"
echo ""

# Find all PIDs using port 8000
echo "Checking for existing processes on port 8000..."
PIDS=$(netstat -ano | grep ':8000' | grep 'LISTENING' | awk '{print $5}' | sort -u)

if [ -n "$PIDS" ]; then
    echo "Found processes on port 8000:"
    echo "$PIDS"
    echo ""
    echo "Killing existing processes..."
    for PID in $PIDS; do
        echo "  Killing PID $PID..."
        taskkill -F -PID $PID 2>/dev/null || true
    done
    echo ""
    echo "Waiting 2 seconds for processes to terminate..."
    sleep 2
else
    echo "No existing processes found on port 8000"
    echo ""
fi

# Verify port is clear
REMAINING=$(netstat -ano | grep ':8000' | grep 'LISTENING' | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "[WARNING] Port 8000 still has $REMAINING processes!"
    echo "You may need to manually kill Python processes:"
    echo "  taskkill -F -IM python.exe"
    echo ""
    exit 1
fi

echo "[OK] Port 8000 is clear"
echo ""

# Start backend server
echo "Starting uvicorn server on port 8000..."
echo "Press Ctrl+C to stop"
echo ""

uv run uvicorn main:app --reload --port 8000
