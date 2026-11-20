#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== LocalTube Linux/macOS Installer ==="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: 'python3' is not installed. Please install Python 3.10+ first."
    exit 1
fi
echo "✓ Python3 found"

# Check FFmpeg
if ! command -v ffmpeg &>/dev/null && [ ! -f "$SCRIPT_DIR/bin/ffmpeg" ]; then
    echo "WARNING: 'ffmpeg' not found in PATH or bin/ directory."
    echo "Thumbnails and previews require FFmpeg (e.g. 'sudo apt install ffmpeg' or 'brew install ffmpeg')."
else
    echo "✓ FFmpeg found"
fi

# Backend setup
echo ""
echo "--- Setting up Backend ---"
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
deactivate
echo "✓ Backend ready"

# Frontend setup
if [ -d "$SCRIPT_DIR/frontend" ]; then
    if command -v npm &>/dev/null; then
        echo ""
        echo "--- Setting up & Building Frontend ---"
        cd "$SCRIPT_DIR/frontend"
        if [ ! -d "node_modules" ]; then
            echo "Installing Node.js dependencies..."
            npm install --silent
        fi
        echo "Building static frontend..."
        npm run build
        echo "✓ Frontend built successfully"
    else
        if [ -f "$SCRIPT_DIR/frontend/dist/index.html" ]; then
            echo "✓ Pre-built frontend detected (no npm needed)"
        else
            echo "WARNING: npm is not installed and frontend/dist is missing. Install Node.js or download a release build."
        fi
    fi
fi

echo ""
echo "=== Installation complete! Run ./run.sh to start LocalTube ==="
