# Debugging: Why CUA Agent Response is Not in Database

## Problem

Tasks show as "pending" status and have no response in the database.

## Possible Causes

### 1. Agent Worker Not Running

**Check if agent_worker container is running:**
```powershell
docker-compose ps agent_worker
```

**Check agent_worker logs:**
```powershell
docker-compose logs agent_worker
```

**Expected log output:**
```
[agent1] Starting agent worker...
[agent1] Connected to PostgreSQL
[agent1] Connected to MongoDB
[agent1] Agent worker started
[agent1] No task found, polling again in 5s...
```

### 2. Agent Worker Not Picking Up Tasks

**Check if tasks are being polled:**
```powershell
docker-compose logs -f agent_worker
```

You should see:
- `[agent1] Task <ID> picked: <title>`
- `[agent1] Task <ID> completed`

**If you don't see task pickup:**
- Check if `get_current_task()` is finding tasks
- Verify task status is "pending"
- Check if task progress is already 100% (tasks with 100% progress are skipped)

### 3. Task Execution Failing

**Check for errors in logs:**
```powershell
docker-compose logs agent_worker | Select-String -Pattern "ERROR|Failed|Exception"
```

**Common errors:**
- CUA agent import failures
- Missing environment variables (CUA_API_KEY, OPENAI_API_KEY)
- Authentication errors
- Timeout errors

### 4. Response Not Being Saved

**Check if response update is failing:**
```powershell
docker-compose logs agent_worker | Select-String -Pattern "Failed to update task response|Warning"
```

**Check task progress:**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 5;"
```

## Diagnostic Commands

### Check Task Status
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, created_at FROM tasks WHERE id = <TASK_ID>;"
```

### Check Task Progress
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

### Check Task Response
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response FROM tasks WHERE id = <TASK_ID>;"
```

### Check Agent Worker Logs for Specific Task
```powershell
docker-compose logs agent_worker | Select-String -Pattern "<TASK_ID>"
```

### Test Agent Worker Directly
```powershell
docker-compose exec agent_worker python /app/agent_worker/execute_task.py "Test task"
```

## Solutions

### Solution 1: Restart Agent Worker

If agent_worker is not running or stuck:

```powershell
docker-compose restart agent_worker
docker-compose logs -f agent_worker
```

### Solution 2: Check Database Connection

Verify agent_worker can connect to PostgreSQL:

```powershell
docker-compose exec agent_worker python -c "from agent_worker.db_adapters import PostgresClient; import os; pg = PostgresClient(os.getenv('POSTGRES_URL')); print('Connected:', pg.get_current_task())"
```

### Solution 3: Manually Trigger Task Processing

If tasks are stuck, you can manually check what `get_current_task()` returns:

```powershell
docker-compose exec agent_worker python -c "from agent_worker.db_adapters import PostgresClient; import os; pg = PostgresClient(os.getenv('POSTGRES_URL')); task = pg.get_current_task(); print('Current task:', task)"
```

### Solution 4: Check Task Query Logic

The agent_worker uses `get_current_task()` which may have specific criteria. Check what tasks it's looking for:

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, agent_id, title, status FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5;"
```

### Solution 5: Verify Response Extraction

The response is extracted from stdout between `AGENT_RESPONSE_START` and `AGENT_RESPONSE_END` markers. Check if these markers are present:

```powershell
docker-compose logs agent_worker | Select-String -Pattern "AGENT_RESPONSE"
```

## Expected Flow

1. **Task Created** → Status: `pending`
2. **Agent Worker Polls** → Finds task via `get_current_task()`
3. **Task Picked** → Log: `[agent1] Task <ID> picked: <title>`
4. **Task Executed** → `execute_task.py` runs
5. **Response Generated** → CUA agent produces output
6. **Response Saved** → `update_task_response()` called
7. **Task Completed** → Status should update (if implemented)

## Check Each Step

### Step 1: Is task in database?
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT COUNT(*) FROM tasks WHERE status = 'pending';"
```

### Step 2: Is agent_worker running?
```powershell
docker-compose ps agent_worker
```

### Step 3: Is agent_worker polling?
```powershell
docker-compose logs agent_worker | Select-String -Pattern "polling|No task found"
```

### Step 4: Is task being picked up?
```powershell
docker-compose logs agent_worker | Select-String -Pattern "picked|Task.*picked"
```

### Step 5: Is task executing?
```powershell
docker-compose logs agent_worker | Select-String -Pattern "executing|run_task.py"
```

### Step 6: Is response being saved?
```powershell
docker-compose logs agent_worker | Select-String -Pattern "update_task_response|response"
```

## Quick Fix: Force Task Processing

If a task is stuck, you can manually trigger execution:

```powershell
# Get task ID
$taskId = 69  # Replace with your task ID

# Manually execute
docker-compose exec agent_worker python /app/agent_worker/execute_task.py "Your task description here"
```

Then check if response was saved:
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT metadata->>'response' as response FROM tasks WHERE id = $taskId;"
```

