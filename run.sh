#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-run installer if virtualenv doesn't exist
if [ ! -f "$SCRIPT_DIR/backend/venv/bin/activate" ]; then
    echo "Virtual environment not found. Running installer..."
    bash "$SCRIPT_DIR/install.sh"
fi

if [ -f "$SCRIPT_DIR/frontend/dist/index.html" ]; then
    echo "=== Starting LocalTube (Unified Server) ==="
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    python3 "$SCRIPT_DIR/run_app.py"
else
    echo "=== Starting LocalTube (Dev Mode) ==="
    echo "Starting Backend Server..."
    cd "$SCRIPT_DIR/backend"
    source venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload &
    BACKEND_PID=$!

    echo "Starting Frontend Dev Server..."
    cd "$SCRIPT_DIR/frontend"
    npm run dev -- --host &
    FRONTEND_PID=$!

    echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"
    echo "Press Ctrl+C to stop both servers."

    # Try opening browser
    if command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:5173 &>/dev/null &
    elif command -v open &>/dev/null; then
        open http://localhost:5173 &>/dev/null &
    fi

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
    wait
fi
