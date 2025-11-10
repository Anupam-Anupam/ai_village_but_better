# Wait for Docker Desktop to start and then build
Write-Host "Waiting for Docker Desktop to start..." -ForegroundColor Yellow

$maxAttempts = 20
$attempt = 0
$dockerReady = $false

while ($attempt -lt $maxAttempts -and -not $dockerReady) {
    $attempt++
    try {
        docker ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host "✓ Docker Desktop is running!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    
    if (-not $dockerReady) {
        Write-Host "  Attempt $attempt/$maxAttempts - Docker not ready yet..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
}

if (-not $dockerReady) {
    Write-Host "✗ Docker Desktop did not start in time." -ForegroundColor Red
    Write-Host "Please start Docker Desktop manually and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Building agent_worker Docker image..." -ForegroundColor Cyan
Write-Host "This may take several minutes due to CUA package downloads..." -ForegroundColor Gray
Write-Host ""

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

docker-compose build agent_worker

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Build completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verifying CUA package installation..." -ForegroundColor Cyan
    
    Write-Host "Checking installed packages..." -ForegroundColor Yellow
    docker-compose run --rm agent_worker pip list 2>&1 | Select-String -Pattern "cua"
    
    Write-Host ""
    Write-Host "Testing imports..." -ForegroundColor Yellow
    docker-compose run --rm agent_worker python -c "from agent import ComputerAgent; from computer import Computer; print('SUCCESS: CUA packages imported correctly')"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ All verification checks passed!" -ForegroundColor Green
        Write-Host "CUA packages are properly installed in the Docker container." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "✗ CUA packages failed to import!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "✗ Build failed!" -ForegroundColor Red
    exit 1
}

