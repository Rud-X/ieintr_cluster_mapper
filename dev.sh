#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Vite) dev servers together.
# Usage: ./dev.sh [--port 8000] [--db path/to/db]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pass any extra args (--port, --db, etc.) through to the backend
BACKEND_ARGS="$@"

cleanup() {
  echo ""
  echo "Stopping servers..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup INT TERM

echo "Starting backend..."
python "$SCRIPT_DIR/server.py" $BACKEND_ARGS &
BACKEND_PID=$!

echo "Starting frontend..."
cd "$SCRIPT_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

wait
