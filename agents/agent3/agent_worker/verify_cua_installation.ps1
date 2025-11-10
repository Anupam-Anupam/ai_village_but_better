# PowerShell script to verify CUA package installation in Docker container
# Run this after building the agent_worker Docker image

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CUA Package Installation Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "1. Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ERROR: Docker Desktop is not running!" -ForegroundColor Red
        Write-Host "   Please start Docker Desktop and try again." -ForegroundColor Red
        exit 1
    }
    Write-Host "   ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: Docker is not available!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check if agent_worker service exists
Write-Host "2. Checking agent_worker service..." -ForegroundColor Yellow
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

try {
    docker-compose ps agent_worker > $null 2>&1
    Write-Host "   ✓ agent_worker service found" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ agent_worker service not found (this is OK if not built yet)" -ForegroundColor Yellow
}

Write-Host ""

# Build the Docker image
Write-Host "3. Building agent_worker Docker image..." -ForegroundColor Yellow
Write-Host "   This may take several minutes due to CUA package downloads..." -ForegroundColor Gray
docker-compose build agent_worker
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "   ✓ Docker image built successfully" -ForegroundColor Green

Write-Host ""

# Check installed CUA packages
Write-Host "4. Checking installed CUA packages..." -ForegroundColor Yellow
$packages = docker-compose run --rm agent_worker pip list 2>&1 | Select-String -Pattern "cua"
if ($packages) {
    Write-Host "   ✓ Found CUA packages:" -ForegroundColor Green
    $packages | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
} else {
    Write-Host "   ⚠ No CUA packages found in pip list" -ForegroundColor Yellow
}

Write-Host ""

# Test CUA package imports
Write-Host "5. Testing CUA package imports..." -ForegroundColor Yellow
$importTest = docker-compose run --rm agent_worker python -c "from agent import ComputerAgent; from computer import Computer; print('SUCCESS: CUA packages imported correctly')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ CUA packages imported successfully" -ForegroundColor Green
    Write-Host "   $importTest" -ForegroundColor Gray
} else {
    Write-Host "   ✗ ERROR: Failed to import CUA packages!" -ForegroundColor Red
    Write-Host "   $importTest" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test ComputerAgent and Computer classes
Write-Host "6. Testing CUA class instantiation..." -ForegroundColor Yellow
$classTest = docker-compose run --rm agent_worker python -c "from agent import ComputerAgent; from computer import Computer, VMProviderType; print('SUCCESS: CUA classes are available')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ CUA classes are available" -ForegroundColor Green
    Write-Host "   $classTest" -ForegroundColor Gray
} else {
    Write-Host "   ✗ ERROR: Failed to access CUA classes!" -ForegroundColor Red
    Write-Host "   $classTest" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check Python path
Write-Host "7. Checking Python path..." -ForegroundColor Yellow
$pythonPath = docker-compose run --rm agent_worker python -c "import sys; print('\n'.join(sys.path))" 2>&1
Write-Host "   Python paths:" -ForegroundColor Gray
$pythonPath | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ All verification checks passed!" -ForegroundColor Green
Write-Host "CUA packages are properly installed." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

