# Storage Testing Guide

Guide for testing the storage system with a CUA agent.

## Prerequisites

1. **Docker containers running**:
   ```bash
   docker-compose up -d postgres mongodb minio
   ```

2. **Agent and server containers running**:
   ```bash
   docker-compose up -d agent1 server
   ```

3. **Environment variables set**:
   ```bash
   export AGENT_ID=agent1
   export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
   export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
   export MINIO_ENDPOINT=localhost:9000
   export MINIO_ACCESS_KEY=minioadmin
   export MINIO_SECRET_KEY=minioadmin
   ```

## Test Scripts

### 1. Simple Adapter Tests (`test_storage_simple.py`)

Tests each storage adapter independently without requiring running services.

**Usage**:
```bash
python test_storage_simple.py
```

**Tests**:
- MongoDB adapter: Write/read logs and memories
- PostgreSQL adapter: Create tasks, add progress, update status
- MinIO adapter: Upload/download screenshots

**Expected Output**:
```
======================================================================
Simple Storage Adapter Tests
======================================================================

[1/3] Testing MongoDB Adapter...
✓ Wrote log: 507f1f77bcf86cd799439011
✓ Read 1 logs
✓ Wrote memory: 507f1f77bcf86cd799439012
✓ Read 1 memories
✓ MongoDB adapter test passed

[2/3] Testing PostgreSQL Adapter...
✓ Created task: 1
✓ Added progress: 1
✓ Updated status: True
✓ Retrieved task: Test Task
✓ Retrieved 1 progress updates
✓ PostgreSQL adapter test passed

[3/3] Testing MinIO Adapter...
✓ Uploaded screenshot: agent1/screenshots/test.png
✓ Downloaded screenshot matches
✓ Found 1 screenshot metadata entries
✓ MinIO adapter test passed

======================================================================
Test Summary
======================================================================
✓ PASS: MongoDB
✓ PASS: PostgreSQL
✓ PASS: MinIO

Total: 3/3 tests passed
```

### 2. Full Integration Test (`test_storage_integration.py`)

Tests complete storage integration with agent execution and server logging.

**Usage**:
```bash
python test_storage_integration.py
```

**Tests**:
1. MongoDB log storage
2. PostgreSQL task storage
3. MinIO screenshot storage
4. Agent execution integration
5. Server request logging

**Expected Output**:
```
======================================================================
Storage Integration Test
======================================================================

[1/5] Initializing storage adapters...
✓ Storage adapters initialized

[2/5] Testing MongoDB log storage...
✓ Wrote log entry: 507f1f77bcf86cd799439011
✓ Verified log entry in MongoDB

[3/5] Testing PostgreSQL task storage...
✓ Created task: 1
✓ Added progress update: 1
✓ Updated task status to completed
✓ Verified task in PostgreSQL
✓ Verified progress updates in PostgreSQL

[4/5] Testing MinIO screenshot storage...
✓ Uploaded screenshot: agent1/screenshots/test_screenshot_20240101_120000.png
✓ Verified screenshot metadata in PostgreSQL
✓ Verified screenshot download from MinIO

[5/5] Testing agent execution and storage integration...
  Sending request to agent: http://localhost:8001/execute
✓ Agent executed task successfully
  Requesting screenshot of test file...
✓ Screenshot uploaded to MinIO: agent1/screenshots/test_file.txt_screenshot.png

[6/6] Testing server request logging...
  Sending request to server: http://localhost:8000/message
✓ Server processed request successfully
✓ Verified request log in PostgreSQL (found 1 logs)

======================================================================
Test Summary
======================================================================
✓ PASS: mongodb_logs
✓ PASS: postgresql_tasks
✓ PASS: minio_screenshots
✓ PASS: agent_execution
✓ PASS: server_logging

Total: 5/5 tests passed
```

## Manual Testing

### 1. Test MongoDB Logs

```python
from storage import MongoAdapter

mongo = MongoAdapter(agent_id="agent1")
log_id = mongo.write_log("info", "Test message", task_id="123")
logs = mongo.read_logs(limit=10)
print(f"Found {len(logs)} logs")
```

### 2. Test PostgreSQL Tasks

```python
from storage import PostgresAdapter

pg = PostgresAdapter()
task_id = pg.create_task("agent1", "Test", "Description", "pending")
pg.add_progress_update(task_id, "agent1", 50.0, "Halfway done")
task = pg.get_task(task_id)
print(f"Task: {task['title']} - {task['status']}")
```

### 3. Test MinIO Screenshots

```python
from storage import PostgresAdapter, MinIOAdapter

pg = PostgresAdapter()
minio = MinIOAdapter(agent_id="agent1", postgres_adapter=pg)

# Upload test image
with open("test.png", "rb") as f:
    screenshot_data = f.read()

object_path = minio.upload_screenshot(screenshot_data, "test.png")

# Download and verify
downloaded = minio.download_screenshot(object_path)
print(f"Uploaded: {len(screenshot_data)} bytes")
print(f"Downloaded: {len(downloaded)} bytes")
```

### 4. Test Agent Execution

```bash
# Send request to agent
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{
    "type": "write",
    "filename": "test.txt",
    "content": "Hello World"
  }'

# Get screenshot
curl -X GET http://localhost:8001/open/test.txt
```

### 5. Verify Data in Databases

**MongoDB**:
```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin

use agent1db
db.agent_logs.find().limit(5)
db.agent_memories.find().limit(5)
```

**PostgreSQL**:
```bash
docker exec -it postgres psql -U hub -d hub

SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 5;
SELECT * FROM task_progress WHERE agent_id = 'agent1' ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM binary_file_metadata WHERE agent_id = 'agent1' ORDER BY uploaded_at DESC LIMIT 5;
SELECT * FROM request_logs WHERE path = '/message' ORDER BY timestamp DESC LIMIT 5;
```

**MinIO**:
```bash
# Using MinIO client
docker run -it --rm \
  --network ai-village-network \
  minio/mc:latest \
  alias set local http://localhost:9000 minioadmin minioadmin

docker run -it --rm \
  --network ai-village-network \
  minio/mc:latest \
  ls local/screenshots/agent1/
```

## Troubleshooting

### MongoDB Connection Issues

```python
# Test MongoDB connection
from pymongo import MongoClient
client = MongoClient("mongodb://admin:password@localhost:27017")
client.admin.command('ping')
```

### PostgreSQL Connection Issues

```python
# Test PostgreSQL connection
from storage.postgres_adapter import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text("SELECT 1"))
    print("✓ PostgreSQL connected")
finally:
    db.close()
```

### MinIO Connection Issues

```python
# Test MinIO connection
from storage.minio_adapter import MinIOAdapter

minio = MinIOAdapter(agent_id="agent1")
buckets = minio.client.list_buckets()
print(f"✓ MinIO connected, found {len(buckets)} buckets")
```

## Integration with Agent Code

To integrate storage adapters into your agent:

```python
# In agent code
from storage import MongoAdapter, PostgresAdapter, MinIOAdapter

# Initialize adapters
mongo = MongoAdapter(agent_id=os.getenv("AGENT_ID"))
pg = PostgresAdapter()
minio = MinIOAdapter(agent_id=os.getenv("AGENT_ID"), postgres_adapter=pg)

# Log activity
mongo.write_log("info", "Task started", task_id=task_id)

# Create task in PostgreSQL
task_id = pg.create_task(
    agent_id=os.getenv("AGENT_ID"),
    title="Task Title",
    description="Description",
    status="in_progress"
)

# Add progress
pg.add_progress_update(task_id, os.getenv("AGENT_ID"), 50.0, "Halfway done")

# Upload screenshot
screenshot_bytes = b"..."  # Screenshot data
object_path = minio.upload_screenshot(screenshot_bytes, "screenshot.png", task_id=task_id)

# Update task status
pg.update_task_status(task_id, "completed")
```

## Expected Results

After running tests, you should see:

1. **MongoDB**: Log entries and memories in `agent1db`
2. **PostgreSQL**: Tasks, progress updates, and metadata in `hub` database
3. **MinIO**: Screenshots in `screenshots` bucket under `agent1/` prefix
4. **Server Logs**: Request logs in PostgreSQL `request_logs` table

## Next Steps

1. Integrate storage adapters into agent code
2. Update agent endpoints to use storage adapters
3. Test with multiple agents
4. Verify evaluator can read all agent data
5. Test frontend screenshot viewing

