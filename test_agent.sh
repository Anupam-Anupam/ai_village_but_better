#!/bin/bash

# Test script to run an agent and verify it can communicate with the chat server

AGENT_ID=${1:-agent1-cua}
AGENT_DIR="agents/${AGENT_ID}"

echo "🧪 Testing agent: ${AGENT_ID}"
echo "📁 Agent directory: ${AGENT_DIR}"
echo ""

# Check if agent directory exists
if [ ! -d "${AGENT_DIR}" ]; then
    echo "❌ Error: Agent directory ${AGENT_DIR} does not exist"
    exit 1
fi

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Error: Chat server is not running at http://localhost:8000"
    echo "   Start it with: ./start_chat_server.sh"
    exit 1
fi

echo "✅ Chat server is running"
echo ""

# Check if .env file exists
if [ ! -f "${AGENT_DIR}/.env" ]; then
    echo "⚠️  Warning: ${AGENT_DIR}/.env not found. Agent may need environment variables."
fi

# Set required environment variables
export CHAT_SERVER_URL="http://localhost:8000"
export AGENT_ID="${AGENT_ID}"
export CHAT_POLL_INTERVAL="5.0"

echo "🚀 Starting agent ${AGENT_ID}..."
echo "   CHAT_SERVER_URL=${CHAT_SERVER_URL}"
echo "   AGENT_ID=${AGENT_ID}"
echo "   CHAT_POLL_INTERVAL=${CHAT_POLL_INTERVAL}"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

cd "${AGENT_DIR}"
python3 main.py

