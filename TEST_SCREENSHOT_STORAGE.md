# Testing Screenshot Storage Functionality

This guide helps you test that screenshots taken by the CUA API are correctly saved in MinIO under the `screenshots` bucket in the folder structure `agent{ID}/screenshots/`.

## Prerequisites

1. **Docker services running:**
   ```powershell
   docker-compose ps
   ```
   
   Should show:
   - `postgres` (running)
   - `mongodb` (running)
   - `minio` (running)
   - `server` (running, optional)
   - `agent_worker` (running, optional)

2. **Environment variables set:**
   ```powershell
   # Check if .env file exists or set these:
   $env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
   $env:MINIO_ENDPOINT = "localhost:9000"
   $env:MINIO_ACCESS_KEY = "minioadmin"
   $env:MINIO_SECRET_KEY = "minioadmin"
   ```

## Test Methods

### Method 1: Automated Test Script

Run the comprehensive test script:

```powershell
# Set environment variables if not in .env
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
$env:MINIO_ENDPOINT = "localhost:9000"

# Run the test
python test_screenshot_storage.py
```

**Expected output:**
- ✅ Agent ID normalization test passes
- ✅ MinIO connection test passes
- ✅ Screenshot upload test passes (uploads to `agent1/screenshots/`)
- ✅ List screenshots test passes

### Method 2: Manual Testing via MinIO Console

1. **Access MinIO Console:**
   - Open browser: http://localhost:9001
   - Login: `minioadmin` / `minioadmin`

2. **Check bucket structure:**
   - Navigate to `screenshots` bucket
   - Should see folders: `agent1/`, `agent2/`, `agent3/`
   - Each folder should contain `screenshots/` subfolder

3. **Verify screenshot paths:**
   - Screenshots should be at: `agent1/screenshots/`, `agent2/screenshots/`, etc.
   - NOT at root level or `agent1-cua/screenshots/`

### Method 3: Test with CUA Agent

1. **Create a task that generates screenshots:**
   ```powershell
   # Send a task that will trigger screenshot capture
   curl -X POST http://localhost:8000/task `
     -H "Content-Type: application/json" `
     -d '{"text": "Take a screenshot of the desktop"}'
   ```

2. **Check MinIO for screenshots:**
   - Access MinIO console: http://localhost:9001
   - Navigate to `screenshots` bucket
   - Check `agent1/screenshots/` folder for new screenshots

3. **Verify in database:**
   ```powershell
   # Check task_progress for screenshot messages
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, message, timestamp FROM task_progress WHERE message LIKE '%screenshot%' ORDER BY timestamp DESC LIMIT 5;"
   ```

### Method 4: Python Interactive Test

```python
from storage import PostgresAdapter, MinIOAdapter
import os

# Initialize adapters
pg = PostgresAdapter(connection_string=os.getenv("POSTGRES_URL"))
minio = MinIOAdapter(
    endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    postgres_adapter=pg,
    agent_id="agent1-cua"  # Test normalization
)

# Check normalized agent_id
print(f"Normalized agent_id: {minio.agent_id}")  # Should print: agent1

# Create test image
test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'

# Upload screenshot
path = minio.upload_screenshot(
    file_data=test_image,
    filename="test.png"
)

print(f"Screenshot path: {path}")  # Should be: agent1/screenshots/test.png

# Verify in MinIO
objects = minio.list_objects("screenshots", prefix="agent1/screenshots/")
print(f"Found {len(objects)} screenshots in agent1/screenshots/")
```

## Verification Checklist

- [ ] Agent ID normalization works (`agent1-cua` → `agent1`)
- [ ] MinIO connection successful
- [ ] Screenshots upload to correct path: `agent{ID}/screenshots/`
- [ ] Screenshots visible in MinIO console
- [ ] Screenshot metadata stored in PostgreSQL
- [ ] Multiple agents can upload to their respective folders

## Troubleshooting

### Issue: MinIO connection fails

**Solution:**
```powershell
# Check if MinIO is running
docker-compose ps minio

# Check MinIO logs
docker-compose logs minio

# Verify endpoint
$env:MINIO_ENDPOINT = "localhost:9000"  # For local
# or
$env:MINIO_ENDPOINT = "minio:9000"  # For Docker network
```

### Issue: Screenshots not appearing

**Solution:**
1. Check agent_worker logs:
   ```powershell
   docker-compose logs agent_worker | Select-String -Pattern "screenshot|upload"
   ```

2. Verify agent_id is being passed correctly:
   ```powershell
   # Check server logs
   docker-compose logs server | Select-String -Pattern "agent_id|storage"
   ```

3. Check PostgreSQL for screenshot metadata:
   ```powershell
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM binary_file_metadata WHERE bucket='screenshots' ORDER BY uploaded_at DESC LIMIT 5;"
   ```

### Issue: Wrong path format

**Solution:**
- Verify `_normalize_agent_id()` method is working
- Check that agent_id is being passed to `MinIOAdapter.__init__()`
- Run the test script to verify normalization

## Expected Path Structure

```
MinIO Bucket: screenshots
├── agent1/
│   └── screenshots/
│       ├── screenshot_20250108_120000.png
│       ├── screenshot_20250108_120001.png
│       └── ...
├── agent2/
│   └── screenshots/
│       └── ...
└── agent3/
    └── screenshots/
        └── ...
```

## Next Steps

After successful testing:
1. Monitor screenshot uploads during actual task execution
2. Verify screenshots are accessible via MinIO console
3. Test screenshot retrieval/download functionality
4. Verify metadata is correctly stored in PostgreSQL

