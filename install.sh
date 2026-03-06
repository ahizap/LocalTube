#!/bin/bash
set -e

echo "=== Install Script ==="

# Check for required system tools
for cmd in python3 node npm ffmpeg ffprobe; do
  if ! command -v $cmd &>/dev/null; then
    echo "ERROR: '$cmd' is not installed. Please install it first."
    exit 1
  fi
done
echo "✓ System dependencies found (python3, node, npm, ffmpeg, ffprobe)"

# Backend setup
echo ""
echo "--- Setting up Backend ---"
cd backend

if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet
deactivate

echo "✓ Backend ready"

# Frontend setup
cd ../frontend
echo ""
echo "--- Setting up Frontend ---"
echo "Installing Node.js dependencies..."
npm install --silent

echo "✓ Frontend ready"

echo ""
echo "=== Installation complete! Run ./run.sh to start. ==="
