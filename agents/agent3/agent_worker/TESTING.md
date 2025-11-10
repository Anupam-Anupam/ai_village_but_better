# Testing Agent Worker Response to Tasks

This guide explains how to test the agent worker's response to tasks.

## Prerequisites

1. **Docker Desktop** must be running
2. **Required containers** must be running:
   - `postgres` - PostgreSQL database
   - `agent_worker` - Agent worker service
   - `mongodb` - MongoDB for logs (optional but recommended)
   - `minio` - MinIO for file storage (optional but recommended)

## Quick Start

### Option 1: Using the Test Script (Recommended)

**Windows (PowerShell):**
```powershell
.\test_agent_response.ps1 "Your task description here"
```

**Linux/Mac/Windows (Python):**
```bash
python test_agent_response.py "Your task description here"
```

**Default test (if no task provided):**
```bash
python test_agent_response.py
```

### Option 2: Using the API Endpoint

If the server is running, you can create tasks via the API:

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"text": "Your task description here"}'
```

### Option 3: Direct Database Insert

You can also insert tasks directly into PostgreSQL:

```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \
  "INSERT INTO tasks (agent_id, title, description, status, metadata) \
   VALUES ('test_user', 'Test Task', 'Your task description', 'pending', '{}') \
   RETURNING id;"
```

## Monitoring Task Execution

### 1. Watch Agent Worker Logs

```bash
docker-compose logs -f agent_worker
```

This will show:
- When tasks are picked up
- Progress updates
- Execution logs
- Errors (if any)

### 2. Check Task Progress in Database

```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \
  "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

### 3. Check Task Details

```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \
  "SELECT * FROM tasks WHERE id = <TASK_ID>;"
```

### 4. Check MongoDB Logs

```bash
docker exec -it ai_village_but_better-mongodb-1 mongosh -u admin -p password \
  --authenticationDatabase admin --eval \
  "use agent_logs_db; db.agent_logs.find().sort({timestamp: -1}).limit(10).pretty()"
```

## Understanding the Response

The agent worker stores the response in the `tasks` table's `metadata` JSONB column:

```sql
SELECT 
  id,
  title,
  status,
  metadata->>'response' as response,
  metadata->>'last_agent' as last_agent,
  updated_at
FROM tasks
WHERE id = <TASK_ID>;
```

The response structure:
- `metadata.response` - The agent's final response text
- `metadata.last_agent` - The agent ID that processed the task
- `metadata.response_updated_at` - When the response was updated

## Example Test Tasks

### Simple Task
```bash
python test_agent_response.py "Open a web browser and navigate to google.com"
```

### Complex Task
```bash
python test_agent_response.py "Create a Python script that prints 'Hello World' and save it to a file"
```

### Web Task
```bash
python test_agent_response.py "Search for 'Python tutorials' on Google and take a screenshot"
```

## Troubleshooting

### Agent Worker Not Picking Up Tasks

1. **Check if agent_worker is running:**
   ```bash
   docker-compose ps agent_worker
   ```

2. **Check agent_worker logs:**
   ```bash
   docker-compose logs agent_worker
   ```

3. **Verify database connection:**
   ```bash
   docker-compose exec agent_worker python -c "from agent_worker.db_adapters import PostgresClient; import os; pg = PostgresClient(os.getenv('POSTGRES_URL')); print('Connected:', pg.get_current_task())"
   ```

### Task Stuck at 0% Progress

1. **Check if execute_task.py is working:**
   ```bash
   docker-compose exec agent_worker python /app/agent_worker/execute_task.py "Test task"
   ```

2. **Check CUA agent availability:**
   ```bash
   docker-compose exec agent_worker python -c "from agent import ComputerAgent; print('CUA agent available')"
   ```

3. **Check environment variables:**
   ```bash
   docker-compose exec agent_worker env | grep -E "CUA_|POSTGRES_|MONGODB_"
   ```

### No Response in Task Metadata

1. **Check if task execution completed:**
   ```bash
   docker-compose logs agent_worker | grep -i "task.*completed\|response"
   ```

2. **Check for errors:**
   ```bash
   docker-compose logs agent_worker | grep -i error
   ```

3. **Verify task_progress table:**
   ```bash
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \
     "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC;"
   ```

## Expected Behavior

1. **Task Creation** (0-5 seconds)
   - Task is created in PostgreSQL
   - Status: `pending`

2. **Task Pickup** (5-10 seconds)
   - Agent worker polls and finds the task
   - Progress update: "Task picked up" or "working..."

3. **Task Execution** (10-300 seconds depending on task)
   - Progress updates every few seconds
   - CUA agent executes the task
   - Screenshots may be uploaded to MinIO

4. **Task Completion** (when done)
   - Progress: 100%
   - Response stored in `metadata.response`
   - Status: `completed` or `failed`

## Advanced Testing

### Test Multiple Tasks

```bash
for task in "Task 1" "Task 2" "Task 3"; do
  python test_agent_response.py "$task"
  sleep 10
done
```

### Monitor All Tasks

```bash
watch -n 5 'docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, updated_at FROM tasks ORDER BY created_at DESC LIMIT 5;"'
```

### Check Agent Worker Health

```bash
docker-compose exec agent_worker python -c "
from agent_worker.config import Config
from agent_worker.db_adapters import PostgresClient, MongoClientWrapper
from agent_worker.storage import MinioClientWrapper

config = Config.from_env()
pg = PostgresClient(config.postgres_dsn)
mongo = MongoClientWrapper(config.mongo_uri)
minio = MinioClientWrapper(config.minio_endpoint, config.minio_access_key, config.minio_secret_key, config.minio_secure)

print('✓ Config loaded')
print('✓ PostgreSQL connected')
print('✓ MongoDB connected')
print('✓ MinIO connected')
"
```

