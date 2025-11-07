# Check if Docker is running
try {
    $dockerVersion = docker --version
    Write-Host "Docker is installed and running: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "Docker is not running or not installed. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Check if MinIO container is already running
$minioRunning = docker ps --filter "name=minio" --format '{{.Names}}' | Select-String -Pattern "minio"

if ($null -eq $minioRunning) {
    Write-Host "Starting MinIO container..." -ForegroundColor Yellow
    
    # Create a volume for MinIO data if it doesn't exist
    $volumeExists = docker volume ls --filter "name=minio_data" --format '{{.Name}}'
    if ($null -eq $volumeExists) {
        docker volume create minio_data
    }
    
    # Run MinIO container
    docker run -d `
        -p 9000:9000 `
        -p 9001:9001 `
        --name minio `
        -v minio_data:/data `
        -e "MINIO_ROOT_USER=minioadmin" `
        -e "MINIO_ROOT_PASSWORD=minioadmin" `
        quay.io/minio/minio server /data --console-address ":9001"
    
    # Wait for MinIO to start
    Start-Sleep -Seconds 5
    Write-Host "MinIO is starting up..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
} else {
    Write-Host "MinIO is already running." -ForegroundColor Green
}

# Check if MinIO is accessible
$minioStatus = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing -ErrorAction SilentlyContinue

if ($minioStatus.StatusCode -eq 200) {
    Write-Host "`n✅ MinIO is running successfully!" -ForegroundColor Green
    Write-Host "   - MinIO Server: http://localhost:9000" -ForegroundColor Cyan
    Write-Host "   - MinIO Console: http://localhost:9001" -ForegroundColor Cyan
    Write-Host "   - Username: minioadmin" -ForegroundColor Cyan
    Write-Host "   - Password: minioadmin" -ForegroundColor Cyan
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Open http://localhost:9001 in your browser"
    Write-Host "2. Log in with the credentials above"
    Write-Host "3. Create a bucket named 'screenshots'"
    Write-Host "4. Create folders 'agent1', 'agent2', 'agent3' inside the bucket"
    Write-Host "5. Upload test images named 'latest.png' to each folder"
} else {
    Write-Host "`n❌ Could not connect to MinIO. Check Docker logs with: docker logs minio" -ForegroundColor Red
}

# Open MinIO Console in default browser
Start-Process "http://localhost:9001"