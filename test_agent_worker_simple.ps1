# Simple PowerShell test script to create a task in PostgreSQL and monitor worker logs

Write-Host "============================================================"
Write-Host "AGENT WORKER TEST - Simple Version"
Write-Host "============================================================"
Write-Host ""

# Create a test task directly in PostgreSQL
Write-Host "Creating test task in PostgreSQL..."
$sql = "INSERT INTO tasks (agent_id, title, description, status, metadata, created_at, updated_at) VALUES ('agent1', 'Test Task: Print Hello World', 'This is a test task to verify the agent worker is working.', 'pending', '{\"test\": true}'::jsonb, NOW(), NOW()) RETURNING id;"
$taskResult = docker exec -i postgres psql -U hub -d hub -t -c $sql

$TASK_ID = ($taskResult -replace '\s', '').Trim()

if ([string]::IsNullOrEmpty($TASK_ID)) {
    Write-Host "ERROR: Failed to create task"
    exit 1
}

Write-Host "Created test task with ID: $TASK_ID"
Write-Host ""
Write-Host "Now monitoring worker logs..."
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Show logs
docker-compose logs -f agent_worker
