# Quick Test Guide for Screenshot Storage

## Step 1: Start Required Services

```powershell
# Start PostgreSQL, MongoDB, and MinIO
docker-compose up -d postgres mongodb minio

# Wait a few seconds for services to start
Start-Sleep -Seconds 5

# Verify services are running
docker-compose ps
```

## Step 2: Run the Test Script

```powershell
# Set environment variables
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
$env:MINIO_ENDPOINT = "localhost:9000"

# Run the test
python test_screenshot_storage.py
```

## Step 3: Verify in MinIO Console

1. Open browser: http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Navigate to `screenshots` bucket
4. Check for folders: `agent1/`, `agent2/`, `agent3/`
5. Each folder should contain `screenshots/` subfolder with test images

## Step 4: Test with Real CUA Agent (Optional)

If you want to test with actual CUA agent screenshots:

```powershell
# Start all services including agent_worker
docker-compose up -d

# Create a task that will generate screenshots
curl -X POST http://localhost:8000/task `
  -H "Content-Type: application/json" `
  -d '{"text": "Take a screenshot of the desktop"}'

# Check MinIO console for new screenshots in agent1/screenshots/
```

## Expected Results

✅ **Agent ID Normalization**: All agent IDs should normalize correctly
- `agent1-cua` → `agent1`
- `agent2-cua` → `agent2`
- `agent3-cua` → `agent3`

✅ **Screenshot Upload**: Screenshots should be saved to:
- `screenshots/agent1/screenshots/`
- `screenshots/agent2/screenshots/`
- `screenshots/agent3/screenshots/`

✅ **MinIO Console**: You should see the folder structure in MinIO web console

## Troubleshooting

### Services not starting:
```powershell
# Check logs
docker-compose logs postgres
docker-compose logs minio

# Restart services
docker-compose restart postgres mongodb minio
```

### Connection refused:
- Make sure services are running: `docker-compose ps`
- Check port mappings: `docker-compose ps` should show ports mapped
- For PostgreSQL: Should show `0.0.0.0:5433->5432/tcp`
- For MinIO: Should show `0.0.0.0:9000->9000/tcp` and `0.0.0.0:9001->9001/tcp`

