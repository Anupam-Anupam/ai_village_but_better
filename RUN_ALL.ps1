# Complete Build, Run, and Test Script (PowerShell)
# ===================================================
# Run this script to build, start, and test the full storage implementation

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Storage Implementation: Complete Setup"
Write-Host "========================================"
Write-Host ""

# Step 1: Install Python Dependencies
Write-Host "[Step 1/10] Installing Python dependencies..." -ForegroundColor Yellow
if (Test-Path "storage\requirements.txt") {
    pip install -r storage\requirements.txt
    pip install httpx asyncio 2>$null
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ storage/requirements.txt not found" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Check Docker Compose
Write-Host "[Step 2/10] Checking Docker Compose configuration..." -ForegroundColor Yellow
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "✗ docker-compose.yml not found" -ForegroundColor Red
    exit 1
}

# Check if MinIO service exists
$dockerComposeContent = Get-Content "docker-compose.yml" -Raw
if ($dockerComposeContent -notmatch "minio:") {
    Write-Host "⚠ MinIO service not found in docker-compose.yml" -ForegroundColor Yellow
    Write-Host "Please add MinIO service to docker-compose.yml (see QUICKSTART.md)"
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
} else {
    Write-Host "✓ Docker Compose configuration found" -ForegroundColor Green
}
Write-Host ""

# Step 3: Build Docker Images
Write-Host "[Step 3/10] Building Docker images..." -ForegroundColor Yellow
docker-compose build
Write-Host "✓ Docker images built" -ForegroundColor Green
Write-Host ""

# Step 4: Start Database Services
Write-Host "[Step 4/10] Starting database services..." -ForegroundColor Yellow
docker-compose up -d postgres mongodb
$dockerComposeServices = docker-compose ps --services 2>&1 | Out-String
if ($dockerComposeServices -match "minio") {
    docker-compose up -d minio
}
Write-Host "Waiting for databases to initialize (10 seconds)..."
Start-Sleep -Seconds 10
Write-Host "✓ Database services started" -ForegroundColor Green
Write-Host ""

# Step 5: Verify Database Services
Write-Host "[Step 5/10] Verifying database services..." -ForegroundColor Yellow

# Check PostgreSQL
try {
    $pgResult = docker exec postgres pg_isready -U hub 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
    } else {
        Write-Host "✗ PostgreSQL is not ready" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ PostgreSQL check failed: $_" -ForegroundColor Red
    exit 1
}

# Check MongoDB
try {
    $mongoResult = docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin --quiet --eval "db.runCommand({ ping: 1 })" 2>&1
    if ($LASTEXITCODE -eq 0 -or $mongoResult -match "ok") {
        Write-Host "✓ MongoDB is ready" -ForegroundColor Green
    } else {
        Write-Host "✗ MongoDB is not ready" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ MongoDB check failed: $_" -ForegroundColor Red
    exit 1
}

# Check MinIO if it exists
$dockerComposeServices = docker-compose ps --services 2>&1 | Out-String
if ($dockerComposeServices -match "minio") {
    try {
        $minioResult = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($minioResult.StatusCode -eq 200) {
            Write-Host "✓ MinIO is ready" -ForegroundColor Green
        } else {
            Write-Host "⚠ MinIO health check failed (may still be starting)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠ MinIO health check failed (may still be starting)" -ForegroundColor Yellow
    }
}
Write-Host ""

# Step 6: Start Application Services
Write-Host "[Step 6/10] Starting application services..." -ForegroundColor Yellow
docker-compose up -d agent1 server
Start-Sleep -Seconds 5
Write-Host "✓ Application services started" -ForegroundColor Green
Write-Host ""

# Step 7: Verify Application Services
Write-Host "[Step 7/10] Verifying application services..." -ForegroundColor Yellow

# Check Agent
try {
    $agentResult = Invoke-WebRequest -Uri "http://localhost:8001/" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($agentResult.StatusCode -eq 200 -or $agentResult.StatusCode -eq 404) {
        Write-Host "✓ Agent is running" -ForegroundColor Green
    } else {
        Write-Host "⚠ Agent may still be starting" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Agent may still be starting" -ForegroundColor Yellow
}

# Check Server
try {
    $serverResult = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($serverResult.StatusCode -eq 200 -or $serverResult.StatusCode -eq 404) {
        Write-Host "✓ Server is running" -ForegroundColor Green
    } else {
        Write-Host "⚠ Server may still be starting" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Server may still be starting" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Set Environment Variables
Write-Host "[Step 8/10] Setting environment variables..." -ForegroundColor Yellow
$env:AGENT_ID = "agent1"
$env:MONGODB_URL = "mongodb://admin:password@localhost:27017/agent1db?authSource=admin"
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5432/hub"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:MINIO_ACCESS_KEY = "minioadmin"
$env:MINIO_SECRET_KEY = "minioadmin"
$env:AGENT_URL = "http://localhost:8001"
$env:SERVER_URL = "http://localhost:8000"
Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host ""

# Step 9: Run Simple Storage Tests
Write-Host "[Step 9/10] Running simple storage tests..." -ForegroundColor Yellow
try {
    python test_storage_simple.py 2>&1 | Out-String | Write-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Simple storage tests passed" -ForegroundColor Green
    } else {
        Write-Host "✗ Simple storage tests failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "Continuing anyway..."
    }
} catch {
    Write-Host "✗ Simple storage tests failed: $_" -ForegroundColor Red
    Write-Host "Continuing anyway..."
}
Write-Host ""

# Step 10: Run Integration Tests
Write-Host "[Step 10/10] Running integration tests..." -ForegroundColor Yellow
try {
    python test_storage_integration.py 2>&1 | Out-String | Write-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Integration tests passed" -ForegroundColor Green
    } else {
        Write-Host "✗ Integration tests failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "See logs above for details"
    }
} catch {
    Write-Host "✗ Integration tests failed: $_" -ForegroundColor Red
    Write-Host "See logs above for details"
}
Write-Host ""

# Summary
Write-Host "========================================"
Write-Host "Setup Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Services running:"
docker-compose ps
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. View logs: docker-compose logs -f"
Write-Host "2. Access MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
Write-Host "3. Test manually: See QUICKSTART.md"
Write-Host ""
Write-Host "To stop services: docker-compose down"
Write-Host ""

