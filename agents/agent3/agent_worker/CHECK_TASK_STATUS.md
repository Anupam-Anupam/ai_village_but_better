# Check Why Task Status is "Pending"

## Quick Diagnostic Commands

### 1. Check if Agent Worker is Running

```powershell
docker-compose ps agent_worker
```

**Expected:** Status should be "Up" or "running"

### 2. Check Agent Worker Logs

```powershell
docker-compose logs agent_worker --tail 50
```

**Look for:**
- `[agent1] Agent worker started`
- `[agent1] No task found, polling again...`
- `[agent1] Task <ID> picked: <title>`
- Any ERROR messages

### 3. Check What Task Agent Worker is Seeing

```powershell
docker-compose exec agent_worker python -c "from agent_worker.db_adapters import PostgresClient; import os; pg = PostgresClient(os.getenv('POSTGRES_URL')); task = pg.get_current_task(); print('Current task:', task['id'] if task else 'None', task['title'] if task else '')"
```

This shows which task `get_current_task()` is returning (it gets the most recent task).

### 4. Check Task Progress for Your Task

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = 71 ORDER BY timestamp DESC LIMIT 5;"
```

If there's no progress, the task hasn't been picked up yet.

### 5. Check All Pending Tasks

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, created_at, updated_at FROM tasks WHERE status = 'pending' ORDER BY created_at DESC LIMIT 5;"
```

### 6. Check if Agent Worker is Stuck

Watch the logs in real-time:

```powershell
docker-compose logs -f agent_worker
```

You should see polling messages every 5 seconds:
```
[agent1] No task found, polling again in 5s...
```

## Common Issues

### Issue 1: Agent Worker Not Running

**Solution:**
```powershell
docker-compose up -d agent_worker
docker-compose logs -f agent_worker
```

### Issue 2: Agent Worker Picking Different Task

The `get_current_task()` method gets the **most recent task** by `updated_at` or `created_at`. If you have multiple tasks, it might be processing a different one.

**Check:**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, COALESCE(updated_at, created_at) as sort_date FROM tasks ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 5;"
```

**Solution:** Wait for other tasks to complete, or manually update the task's `updated_at` to make it the most recent:

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "UPDATE tasks SET updated_at = NOW() WHERE id = 71;"
```

### Issue 3: Agent Worker Stuck on Previous Task

If agent_worker is stuck executing a previous task, it won't pick up new tasks.

**Check logs:**
```powershell
docker-compose logs agent_worker | Select-String -Pattern "Task.*picked|executing|completed"
```

**Solution:** Restart agent_worker:
```powershell
docker-compose restart agent_worker
```

### Issue 4: Task Already Has 100% Progress

If a task has 100% progress, agent_worker skips it.

**Check:**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT MAX(COALESCE(progress_percent, percent, 0)) as max_progress FROM task_progress WHERE task_id = 71;"
```

**Solution:** Reset progress or update task status manually.

## Force Task Processing

If you want to force agent_worker to process task 71:

### Option 1: Make Task Most Recent

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "UPDATE tasks SET updated_at = NOW() WHERE id = 71;"
```

### Option 2: Manually Execute Task

```powershell
# Get task description
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -t -c "SELECT description FROM tasks WHERE id = 71;"

# Execute manually (replace with actual description)
docker-compose exec agent_worker python /app/agent_worker/execute_task.py "make a python file that prints 'hello world'"
```

## Expected Behavior

1. **Agent worker polls** every 5 seconds
2. **Gets most recent task** via `get_current_task()`
3. **Checks progress** - if >= 100%, skips
4. **Executes task** if progress < 100%
5. **Updates response** in database
6. **Moves to next task**

## Debug Your Specific Task (ID 71)

Run these commands in order:

```powershell
# 1. Check if agent_worker is running
docker-compose ps agent_worker

# 2. Check what task agent_worker sees
docker-compose exec agent_worker python -c "from agent_worker.db_adapters import PostgresClient; import os; pg = PostgresClient(os.getenv('POSTGRES_URL')); task = pg.get_current_task(); print('Current task ID:', task['id'] if task else 'None')"

# 3. Check your task's progress
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT MAX(COALESCE(progress_percent, percent, 0)) as max_progress FROM task_progress WHERE task_id = 71;"

# 4. Check agent_worker logs
docker-compose logs agent_worker --tail 20

# 5. Make your task most recent (if needed)
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "UPDATE tasks SET updated_at = NOW() WHERE id = 71;"

# 6. Watch logs in real-time
docker-compose logs -f agent_worker
```

