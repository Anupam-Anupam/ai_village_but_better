#!/bin/bash
# Simple test script to create a task in PostgreSQL and monitor worker logs

echo "============================================================"
echo "AGENT WORKER TEST - Simple Version"
echo "============================================================"
echo ""

# Create a test task directly in PostgreSQL
echo "Creating test task in PostgreSQL..."
TASK_ID=$(docker exec -i postgres psql -U hub -d hub -t -c "
INSERT INTO tasks (agent_id, title, description, status, metadata, created_at, updated_at)
VALUES (
    'agent1',
    'Test Task: Print Hello World',
    'This is a test task to verify the agent worker is working.',
    'pending',
    '{\"test\": true}'::jsonb,
    NOW(),
    NOW()
)
RETURNING id;
" | tr -d ' ')

if [ -z "$TASK_ID" ]; then
    echo "ERROR: Failed to create task"
    exit 1
fi

echo "✓ Created test task with ID: $TASK_ID"
echo ""
echo "Monitoring worker logs for the next 30 seconds..."
echo "Press Ctrl+C to stop early"
echo ""

# Monitor logs
timeout 30 docker-compose logs -f agent_worker 2>&1 || true

echo ""
echo "============================================================"
echo "Checking task progress..."
echo "============================================================"

docker exec -i postgres psql -U hub -d hub -c "
SELECT 
    id,
    task_id,
    agent_id,
    progress_percent,
    message,
    timestamp
FROM task_progress
WHERE task_id = $TASK_ID
ORDER BY timestamp DESC
LIMIT 10;
"

echo ""
echo "To view worker logs: docker-compose logs -f agent_worker"
echo "To check task details: docker exec -it postgres psql -U hub -d hub -c \"SELECT * FROM tasks WHERE id = $TASK_ID;\""

