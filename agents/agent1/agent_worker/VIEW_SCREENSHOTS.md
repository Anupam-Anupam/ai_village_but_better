# Viewing Screenshots

Screenshots are stored in **MinIO** (object storage) and can be accessed via:
1. **MinIO Web Console** (easiest)
2. **Database queries** (to find screenshot paths)
3. **API/Programmatic access**

## Method 1: MinIO Web Console (Easiest)

### Access the MinIO Console

1. **Open your browser:**
   ```
   http://localhost:9001
   ```

2. **Login credentials:**
   - Username: `minioadmin`
   - Password: `minioadmin`

3. **Navigate to screenshots:**
   - Click on the **"screenshots"** bucket
   - Browse to `agent1/screenshots/` folder
   - You'll see all uploaded screenshots

### Screenshot Path Format

Screenshots are stored at:
```
screenshots/agent1/screenshots/{uuid}.png
```

Example:
```
screenshots/agent1/screenshots/550e8400-e29b-41d4-a716-446655440000.png
```

## Method 2: Query Database for Screenshot Paths

**Note:** The agent_worker stores screenshot paths in `task_progress` messages, not in a separate `binary_files` table.

### Find Screenshots for a Task (from task_progress)

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, agent_id, message, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, agent_id, message, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

This will show messages like:
```
uploaded screenshot: agent1/screenshots/550e8400-e29b-41d4-a716-446655440000.png
```

### Extract Screenshot Paths from Messages

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, SUBSTRING(message FROM 'uploaded screenshot: (.+)') as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

### Check if binary_file_metadata Table Exists

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\d binary_file_metadata"
```

If the table exists (created by storage/postgres_adapter), you can query it:
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, agent_id, object_path, bucket, uploaded_at FROM binary_file_metadata WHERE task_id = 71 ORDER BY uploaded_at DESC;"
```

**Note:** The agent_worker doesn't populate this table - it only stores paths in task_progress messages.

## Method 3: Check Agent Worker Logs

Screenshot uploads are logged in agent_worker logs:

```powershell
docker-compose logs agent_worker | Select-String -Pattern "screenshot|Uploaded"
```

You'll see messages like:
```
[agent1] Uploaded screenshot: agent1/screenshots/550e8400-e29b-41d4-a716-446655440000.png
```

## Method 4: Download Screenshot via MinIO API

### Using MinIO Client (mc)

1. **Install MinIO Client:**
   - Download from: https://min.io/download#/windows
   - Or use Docker: `docker run -it --rm minio/mc`

2. **Configure alias:**
   ```powershell
   mc alias set local http://localhost:9000 minioadmin minioadmin
   ```

3. **List screenshots:**
   ```powershell
   mc ls local/screenshots/agent1/screenshots/
   ```

4. **Download screenshot:**
   ```powershell
   mc cp local/screenshots/agent1/screenshots/{filename}.png ./downloads/
   ```

### Using Python

```python
from minio import Minio
from minio.error import S3Error

# Initialize MinIO client
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# List screenshots
objects = client.list_objects("screenshots", prefix="agent1/screenshots/", recursive=True)
for obj in objects:
    print(f"Screenshot: {obj.object_name}")

# Download a screenshot
try:
    client.fget_object(
        "screenshots",
        "agent1/screenshots/550e8400-e29b-41d4-a716-446655440000.png",
        "downloaded_screenshot.png"
    )
    print("Screenshot downloaded!")
except S3Error as e:
    print(f"Error: {e}")
```

## Method 5: Direct URL Access (if configured)

If MinIO is configured for public access, you can access screenshots directly:

```
http://localhost:9000/screenshots/agent1/screenshots/{uuid}.png
```

**Note:** By default, MinIO requires authentication, so this may not work without additional configuration.

## Quick Commands

### Check if MinIO is Running

```powershell
docker-compose ps minio
```

### Check MinIO Logs

```powershell
docker-compose logs minio
```

### Access MinIO Console

Open browser: `http://localhost:9001`
- Username: `minioadmin`
- Password: `minioadmin`

### Find Screenshots for Task 71

```powershell
# Check task_progress for screenshot messages
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT message FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"

# Extract screenshot paths
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT SUBSTRING(message FROM 'uploaded screenshot: (.+)') as screenshot_path FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"

# Check logs
docker-compose logs agent_worker | Select-String -Pattern "71.*screenshot"
```

## Troubleshooting

### Issue: No Screenshots Found

1. **Check if task executed:**
   ```powershell
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = 71 ORDER BY timestamp DESC LIMIT 5;"
   ```

2. **Check if screenshots were created:**
   - CUA agent may not have taken screenshots
   - Screenshots are only created if the agent performs visual actions

3. **Check upload logs:**
   ```powershell
   docker-compose logs agent_worker | Select-String -Pattern "uploaded screenshot|Failed to upload"
   ```

### Issue: Can't Access MinIO Console

1. **Check if MinIO is running:**
   ```powershell
   docker-compose ps minio
   ```

2. **Check port mapping:**
   ```powershell
   docker-compose ps minio
   ```
   Should show: `0.0.0.0:9001->9001/tcp`

3. **Check if port is in use:**
   ```powershell
   netstat -ano | findstr :9001
   ```

### Issue: Screenshots Not Uploading

1. **Check MinIO connection:**
   ```powershell
   docker-compose logs agent_worker | Select-String -Pattern "MinIO|Connected"
   ```

2. **Check for upload errors:**
   ```powershell
   docker-compose logs agent_worker | Select-String -Pattern "Failed to upload|ERROR.*screenshot"
   ```

3. **Verify MinIO bucket exists:**
   - Access MinIO console: http://localhost:9001
   - Check if "screenshots" bucket exists

## Expected Behavior

1. **Task executes** → CUA agent may take screenshots
2. **Screenshots saved** → Saved to `/tmp/agent_work/.../screenshots/` directory
3. **Screenshots detected** → Agent worker detects new files
4. **Screenshots uploaded** → Uploaded to MinIO `screenshots` bucket
5. **Metadata saved** → Path saved to `binary_files` table in PostgreSQL

## Screenshot Storage Structure

```
MinIO Bucket: screenshots
├── agent1/
│   └── screenshots/
│       ├── {uuid1}.png
│       ├── {uuid2}.png
│       └── ...
└── agent2/
    └── screenshots/
        └── ...
```

## How Screenshots Are Tracked

The agent_worker stores screenshot information in:

1. **task_progress table** - Screenshot paths are stored in progress messages:
   ```sql
   SELECT message FROM task_progress 
   WHERE task_id = 71 AND message LIKE '%screenshot%';
   ```
   Messages look like: `uploaded screenshot: agent1/screenshots/{uuid}.png`

2. **MongoDB logs** - Screenshot uploads are logged with metadata

3. **MinIO** - The actual screenshot files are stored in the `screenshots` bucket

**Note:** The `binary_file_metadata` table exists in the schema (from `storage/postgres_adapter.py`), but the agent_worker doesn't populate it. It only stores paths in `task_progress` messages.

## Example: Complete Screenshot Check

```powershell
# 1. Check if task has screenshots (from task_progress)
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT COUNT(*) as screenshot_count FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%';"

# 2. Get screenshot paths from task_progress messages
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT SUBSTRING(message FROM 'uploaded screenshot: (.+)') as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"

# 3. Check upload logs
docker-compose logs agent_worker | Select-String -Pattern "71.*screenshot"

# 4. Access MinIO console
# Open: http://localhost:9001
# Login: minioadmin / minioadmin
# Navigate: screenshots bucket → agent1/screenshots/
```

