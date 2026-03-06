#!/bin/bash
echo "Starting Backend Server..."
cd backend
source venv/bin/activate
uvicorn main:app --port 8080 --reload &
BACKEND_PID=$!

cd ../frontend
echo "Starting Frontend Dev Server..."
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
