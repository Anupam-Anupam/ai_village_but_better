#!/bin/bash

# Verify that agents can be set up and run correctly

echo "🔍 Verifying Agent Setup..."
echo ""

# Check if server is running
echo "1. Checking chat server..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Chat server is running"
else
    echo "   ❌ Chat server is NOT running"
    echo "      Start it with: ./start_chat_server.sh"
    exit 1
fi

# Check if agents can reach the server
echo ""
echo "2. Testing agent-server connection..."
for agent_id in agent1-cua agent2-cua agent3-cua; do
    response=$(curl -s "http://localhost:8000/chat/tasks?agent_id=${agent_id}&limit=1")
    if echo "$response" | grep -q "tasks"; then
        echo "   ✅ ${agent_id} can reach server"
    else
        echo "   ⚠️  ${agent_id} connection test failed"
    fi
done

# Check for running agents
echo ""
echo "3. Checking for running agents..."
running=$(ps aux | grep -E "python.*main.py" | grep -v grep | wc -l | tr -d ' ')
if [ "$running" -gt 0 ]; then
    echo "   ✅ Found $running agent process(es) running"
    ps aux | grep -E "python.*main.py" | grep -v grep | awk '{print "      PID:", $2, "-", $11, $12, $13}'
else
    echo "   ❌ No agents are currently running"
    echo "      Start agents with: ./start_all_agents.sh"
fi

# Check pending tasks
echo ""
echo "4. Checking pending tasks..."
pending=$(curl -s "http://localhost:8000/chat/tasks?agent_id=agent1-cua&limit=100" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('tasks', [])))" 2>/dev/null || echo "0")
if [ "$pending" -gt 0 ]; then
    echo "   ⚠️  Found $pending pending task(s) waiting for agents"
    echo "      Agents should process these when they start polling"
else
    echo "   ✅ No pending tasks"
fi

echo ""
echo "=== Summary ==="
echo "For agents to respond to messages:"
echo "  1. Chat server must be running ✅"
echo "  2. Agents must be started manually (they don't auto-start)"
echo "  3. Agents poll for tasks every 5 seconds"
echo ""
echo "To start agents:"
echo "  ./start_all_agents.sh"
echo "  OR"
echo "  ./test_agent.sh agent1-cua"

