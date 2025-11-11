# Testing CUA Agent with Screenshot Capture

This guide shows you how to test the CUA agent with a task that writes "hello world" in the terminal and captures a screenshot.

## Prerequisites

1. **All services running:**
   ```powershell
   docker-compose up -d postgres mongodb minio server agent_worker
   ```

2. **Verify services are running:**
   ```powershell
   docker-compose ps
   ```

   Should show:
   - `postgres` (running)
   - `mongodb` (running)
   - `minio` (running)
   - `server` (running)
   - `agent_worker` (running)

## Test Method 1: Automated Test Script

Run the automated test script:

```powershell
python test_cua_screenshot.py
```

**What it does:**
1. Checks all services are running
2. Creates a task: "Write 'hello world' in the terminal and take a screenshot of it"
3. Waits for the agent_worker to pick up and execute the task
4. Monitors task progress
5. Checks for screenshots in MinIO
6. Provides viewing instructions

**Expected output:**
- Task created successfully
- Task status changes: `pending` → `assigned` → `in_progress` → `completed`
- Screenshots found in MinIO at `agent1/screenshots/`

## Test Method 2: Manual Testing

### Step 1: Create Task via API

```powershell
curl -X POST http://localhost:8000/task `
  -H "Content-Type: application/json" `
  -d '{\"text\": \"Write \"hello world\" in the terminal and take a screenshot of it\"}'
```

**Response:**
```json
{
  "task_id": 74,
  "status": "created"
}
```

### Step 2: Monitor Task Progress

```powershell
# Check task status
curl http://localhost:8000/task/74

# Or query PostgreSQL directly
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, created_at FROM tasks WHERE id=74;"
```

### Step 3: Check Agent Worker Logs

```powershell
# Watch agent_worker logs
docker-compose logs -f agent_worker

# Or check recent logs
docker-compose logs agent_worker --tail 50
```

**What to look for:**
- `[agent1] Task {id} picked: ...`
- `[agent1] Task started`
- `[agent1] Uploaded screenshot: agent1/screenshots/...`
- `[agent1] Task {id} completed`

### Step 4: Verify Screenshots in MinIO

**Option A: MinIO Web Console**
1. Open browser: http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Navigate to `screenshots` bucket
4. Go to `agent1/screenshots/` folder
5. Look for new screenshot files (`.png`)

**Option B: Query Database**
```powershell
# Check binary_file_metadata
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT object_path, bucket, uploaded_at FROM binary_file_metadata WHERE bucket='screenshots' ORDER BY uploaded_at DESC LIMIT 5;"

# Check task_progress for screenshot messages
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, message, timestamp FROM task_progress WHERE message LIKE '%screenshot%' ORDER BY timestamp DESC LIMIT 5;"
```

**Option C: MinIO CLI**
```powershell
# List screenshots (requires minio client installed)
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/screenshots/agent1/screenshots/
```

## Expected Behavior

1. **Task Creation:**
   - Task is created in PostgreSQL with status `pending`
   - Task is assigned to an agent (e.g., `agent1-cua`)

2. **Task Execution:**
   - `agent_worker` polls PostgreSQL and picks up the task
   - Task status changes to `in_progress`
   - CUA agent connects to VM
   - CUA agent executes the task (writes "hello world" in terminal)
   - CUA agent takes a screenshot
   - Screenshot is saved to workdir
   - `agent_worker` uploads screenshot to MinIO
   - Screenshot path: `agent1/screenshots/{filename}.png`
   - Task status changes to `completed`

3. **Screenshot Storage:**
   - Screenshot is stored in MinIO bucket: `screenshots`
   - Path: `agent1/screenshots/{timestamp}.png` or `agent1/screenshots/{uuid}.png`
   - Metadata is stored in PostgreSQL `binary_file_metadata` table
   - Progress update is logged in `task_progress` table

## Troubleshooting

### Issue: Task stays in "pending" status

**Solution:**
```powershell
# Check if agent_worker is running
docker-compose ps agent_worker

# Check agent_worker logs
docker-compose logs agent_worker --tail 50

# Restart agent_worker if needed
docker-compose restart agent_worker
```

### Issue: Task fails with error

**Solution:**
```powershell
# Check task details
curl http://localhost:8000/task/{task_id}

# Check agent_worker logs for errors
docker-compose logs agent_worker | Select-String -Pattern "error|ERROR|failed|FAILED"

# Check server logs
docker-compose logs server | Select-String -Pattern "error|ERROR"
```

### Issue: No screenshots found

**Solution:**
1. Check if CUA agent is configured correctly:
   ```powershell
   # Check agent_worker environment variables
   docker-compose exec agent_worker env | Select-String -Pattern "CUA|OPENAI"
   ```

2. Check if CUA agent is taking screenshots:
   ```powershell
   # Check agent_worker logs for screenshot messages
   docker-compose logs agent_worker | Select-String -Pattern "screenshot|Screenshot"
   ```

3. Verify MinIO connection:
   ```powershell
   # Check MinIO is accessible
   docker-compose ps minio
   
   # Check MinIO logs
   docker-compose logs minio --tail 20
   ```

### Issue: Screenshots in wrong location

**Solution:**
- Verify agent_id normalization is working
- Check that `storage/minio_adapter.py` has `_normalize_agent_id()` method
- Verify screenshots are saved to `agent{ID}/screenshots/` not `agent{ID}-cua/screenshots/`

## Verification Checklist

- [ ] Task created successfully
- [ ] Task picked up by agent_worker
- [ ] Task status changes to `in_progress`
- [ ] CUA agent executes task
- [ ] Screenshot captured
- [ ] Screenshot uploaded to MinIO
- [ ] Screenshot path: `agent1/screenshots/...`
- [ ] Screenshot visible in MinIO console
- [ ] Screenshot metadata in PostgreSQL
- [ ] Task status changes to `completed`

## Next Steps

After successful testing:
1. Monitor screenshot uploads during actual task execution
2. Verify screenshots are accessible via MinIO console
3. Test screenshot retrieval/download functionality
4. Verify metadata is correctly stored in PostgreSQL
5. Test with different agents (agent2, agent3) to verify agent-specific folders

