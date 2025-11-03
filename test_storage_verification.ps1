# Storage Verification Test Script
# =================================
# Tests storage functionality with a CUA agent by:
# 1. Sending requests to agent and server
# 2. Verifying data is stored in MongoDB, PostgreSQL, and MinIO
#
# Prerequisites:
#   - Docker containers running (postgres, mongodb, minio, agent1, server)
#   - Python with storage adapters installed

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Storage Verification Test"
Write-Host "========================================"
Write-Host ""

# Configuration
$agentUrl = if ($env:AGENT_URL) { $env:AGENT_URL } else { "http://localhost:8001" }
$serverUrl = if ($env:SERVER_URL) { $env:SERVER_URL } else { "http://localhost:8000" }
$agentId = if ($env:AGENT_ID) { $env:AGENT_ID } else { "agent1" }

Write-Host "[1/6] Testing Agent Execution..."
try {
    # Send write request to agent
    $writePayload = @{
        type = "write"
        filename = "test_storage.txt"
        content = "Test content for storage verification at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    } | ConvertTo-Json -Depth 4
    
    $writeResp = Invoke-WebRequest -Method POST -Uri "$agentUrl/execute" -ContentType "application/json" -Body $writePayload -UseBasicParsing
    Write-Host "✓ Agent write request successful"
    Write-Host "  Response: $($writeResp.Content.Substring(0, [Math]::Min(200, $writeResp.Content.Length)))..."
} catch {
    Write-Host "✗ Agent write request failed: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "[2/6] Testing Screenshot Generation..."
try {
    # Get screenshot of the created file
    $screenshotResp = Invoke-WebRequest -Method GET -Uri "$agentUrl/open/test_storage.txt" -UseBasicParsing -TimeoutSec 30
    
    $screenshotJson = $screenshotResp.Content | ConvertFrom-Json
    if ($screenshotJson.screenshot) {
        Write-Host "✓ Screenshot generated successfully"
        
        # Save screenshot locally for verification
        $outputFile = "test_storage_screenshot.png"
        $bytes = [System.Convert]::FromBase64String($screenshotJson.screenshot)
        [System.IO.File]::WriteAllBytes($outputFile, $bytes)
        Write-Host "  Screenshot saved to: $outputFile ($($bytes.Length) bytes)"
    } else {
        Write-Host "✗ No screenshot in response"
    }
} catch {
    Write-Host "✗ Screenshot request failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[3/6] Testing Server Request Logging..."
try {
    # Send message to server
    $messagePayload = @{
        message = "Test message for storage verification at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    } | ConvertTo-Json -Depth 4
    
    $serverResp = Invoke-WebRequest -Method POST -Uri "$serverUrl/message" -ContentType "application/json" -Body $messagePayload -UseBasicParsing
    Write-Host "✓ Server request successful"
    Write-Host "  Response: $($serverResp.Content.Substring(0, [Math]::Min(200, $serverResp.Content.Length)))..."
    
    # Wait for server to log request
    Start-Sleep -Seconds 2
    
} catch {
    Write-Host "✗ Server request failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[4/6] Verifying MongoDB Data..."
try {
    # Check MongoDB using docker exec
    $mongoCheck = docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin --quiet --eval "use ${agentId}db; db.agent_logs.countDocuments()"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ MongoDB connection successful"
        Write-Host "  Log count: $mongoCheck"
        
        # Get recent logs
        $logs = docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin --quiet --eval "use ${agentId}db; db.agent_logs.find().sort({created_at: -1}).limit(3).toArray()" | ConvertFrom-Json
        if ($logs) {
            Write-Host "  Recent logs:"
            foreach ($log in $logs) {
                Write-Host "    - $($log.level): $($log.message)"
            }
        }
    } else {
        Write-Host "✗ MongoDB check failed"
    }
} catch {
    Write-Host "✗ MongoDB verification failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[5/6] Verifying PostgreSQL Data..."
try {
    # Check PostgreSQL tasks
    $taskCount = docker exec postgres psql -U hub -d hub -t -c "SELECT COUNT(*) FROM tasks WHERE agent_id = '$agentId';"
    $taskCount = $taskCount.Trim()
    
    Write-Host "✓ PostgreSQL connection successful"
    Write-Host "  Tasks count: $taskCount"
    
    # Get recent tasks
    $tasks = docker exec postgres psql -U hub -d hub -t -A -F "|" -c "SELECT id, title, status FROM tasks WHERE agent_id = '$agentId' ORDER BY created_at DESC LIMIT 3;"
    if ($tasks) {
        Write-Host "  Recent tasks:"
        foreach ($task in $tasks.Split("`n")) {
            if ($task.Trim()) {
                Write-Host "    - Task: $task"
            }
        }
    }
    
    # Check request logs
    $logCount = docker exec postgres psql -U hub -d hub -t -c "SELECT COUNT(*) FROM request_logs WHERE path = '/message';"
    $logCount = $logCount.Trim()
    Write-Host "  Request logs count: $logCount"
    
} catch {
    Write-Host "✗ PostgreSQL verification failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "[6/6] Verifying MinIO Data..."
try {
    # List screenshots in MinIO
    $objects = docker run --rm --network ai-village-network minio/mc:latest alias set local http://minio:9000 minioadmin minioadmin 2>&1
    $objects = docker run --rm --network ai-village-network minio/mc:latest ls local/screenshots/${agentId}/ 2>&1
    
    if ($LASTEXITCODE -eq 0 -and $objects) {
        Write-Host "✓ MinIO connection successful"
        Write-Host "  Objects in screenshots/$agentId/:"
        foreach ($line in $objects.Split("`n")) {
            if ($line.Trim()) {
                Write-Host "    - $line"
            }
        }
    } else {
        Write-Host "✗ MinIO check failed or no objects found"
    }
} catch {
    Write-Host "✗ MinIO verification failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "========================================"
Write-Host "Verification Summary"
Write-Host "========================================"
Write-Host ""
Write-Host "To verify data manually:"
Write-Host ""
Write-Host "MongoDB:"
Write-Host "  docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin"
Write-Host "  use ${agentId}db"
Write-Host "  db.agent_logs.find().limit(5)"
Write-Host ""
Write-Host "PostgreSQL:"
Write-Host "  docker exec -it postgres psql -U hub -d hub"
Write-Host "  SELECT * FROM tasks WHERE agent_id = '$agentId' ORDER BY created_at DESC LIMIT 5;"
Write-Host "  SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT 5;"
Write-Host ""
Write-Host "MinIO:"
Write-Host "  docker run -it --rm --network ai-village-network -v `$(pwd):/data minio/mc:latest alias set local http://minio:9000 minioadmin minioadmin"
Write-Host "  docker run -it --rm --network ai-village-network -v `$(pwd):/data minio/mc:latest ls local/screenshots/${agentId}/"
Write-Host ""
Write-Host "Python Test Scripts:"
Write-Host "  python test_storage_simple.py          # Simple adapter tests"
Write-Host "  python test_storage_integration.py     # Full integration test"
Write-Host ""

