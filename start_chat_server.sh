#!/bin/bash

# Start the AI Village Chat Server
# This script sets up the environment and starts the FastAPI server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${SCRIPT_DIR}/server"

echo "🚀 Starting AI Village Chat Server..."
echo ""

# Check if dependencies are installed
if ! python3 -c "import fastapi, uvicorn, pymongo" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    cd "${SERVER_DIR}"
    pip3 install -r requirements.txt
fi

# Set environment variables
export MONGODB_URL="${MONGODB_URL:-mongodb://admin:password@localhost:27017/serverdb?authSource=admin}"
export CHAT_CORS_ORIGINS="${CHAT_CORS_ORIGINS:-*}"

echo "📡 MongoDB URL: ${MONGODB_URL}"
echo "🌐 CORS Origins: ${CHAT_CORS_ORIGINS}"
echo ""

# Start the server
cd "${SERVER_DIR}"
echo "✅ Starting server on http://0.0.0.0:8000"
echo "   Press Ctrl+C to stop"
echo ""

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

