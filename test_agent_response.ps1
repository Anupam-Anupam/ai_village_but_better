# PowerShell script to test agent worker response to tasks
# Usage: .\test_agent_response.ps1 "Your task description here"

param(
    [string]$TaskDescription = "Open a web browser and search for 'Python programming tutorials'"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AGENT WORKER RESPONSE TEST" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Task Description: $TaskDescription" -ForegroundColor Yellow
Write-Host ""

# Check if Python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python or use the Python script directly:" -ForegroundColor Yellow
    Write-Host "  python test_agent_response.py `"$TaskDescription`"" -ForegroundColor White
    exit 1
}

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker Desktop is not running!" -ForegroundColor Red
        Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✓ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Docker is not available!" -ForegroundColor Red
    exit 1
}

# Check if containers are running
Write-Host ""
Write-Host "Checking required containers..." -ForegroundColor Yellow
$requiredContainers = @("postgres", "agent_worker")
$allRunning = $true

foreach ($container in $requiredContainers) {
    $containerName = "ai_village_but_better-${container}-1"
    $running = docker ps --filter "name=$containerName" --format "{{.Names}}" 2>&1 | Select-String -Pattern $containerName
    if ($running) {
        Write-Host "  ✓ $container is running" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ $container is not running" -ForegroundColor Red
        $allRunning = $false
    }
}

if (-not $allRunning) {
    Write-Host ""
    Write-Host "Starting required containers..." -ForegroundColor Yellow
    docker-compose up -d postgres agent_worker
    Write-Host "Waiting 5 seconds for containers to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "Running test script..." -ForegroundColor Cyan
Write-Host ""

# Run the Python test script
python test_agent_response.py $TaskDescription

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "To view agent worker logs in real-time:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f agent_worker" -ForegroundColor White
Write-Host ""

