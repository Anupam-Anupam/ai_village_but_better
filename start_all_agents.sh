#!/bin/bash

# Start all CUA agents in the background
# This script starts all three agents as separate background processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "🚀 Starting all CUA agents..."
echo ""

# Set common environment variables
export CHAT_SERVER_URL="http://localhost:8000"
export CHAT_POLL_INTERVAL="5.0"

# Function to start an agent
start_agent() {
    local agent_id=$1
    local agent_dir="agents/${agent_id}"
    
    if [ ! -d "${agent_dir}" ]; then
        echo "⚠️  Warning: ${agent_dir} does not exist, skipping ${agent_id}"
        return
    fi
    
    echo "Starting ${agent_id}..."
    cd "${agent_dir}"
    
    export AGENT_ID="${agent_id}"
    
    # Start agent in background, redirect output to log file
    nohup python3 main.py > "${SCRIPT_DIR}/logs/${agent_id}.log" 2>&1 &
    local pid=$!
    echo "  ✅ ${agent_id} started (PID: ${pid})"
    
    cd "${SCRIPT_DIR}"
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Start all agents
start_agent "agent1-cua"
start_agent "agent2-cua"
start_agent "agent3-cua"

echo ""
echo "✅ All agents started!"
echo ""
echo "To view agent logs:"
echo "  tail -f logs/agent1-cua.log"
echo "  tail -f logs/agent2-cua.log"
echo "  tail -f logs/agent3-cua.log"
echo ""
echo "To stop all agents:"
echo "  pkill -f 'python3 main.py'"
echo ""

