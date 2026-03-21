#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Whisper Local STT Setup ==="

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p app/static models uploads

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "WARNING: ffmpeg is not installed. Audio format conversion will not work."
    echo "Install with: brew install ffmpeg"
    echo ""
fi

echo ""
echo "=== Setup Complete ==="
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  python -m app.main"
