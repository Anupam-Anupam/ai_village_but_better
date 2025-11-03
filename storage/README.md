# Storage System Architecture

Centralized storage layer for multi-agent architecture with MongoDB, PostgreSQL, and MinIO.

## Architecture Overview

```
┌─────────────────┐
│  User Frontend   │
│  (Read-only)     │
└────────┬────────┘
         │
         ├───> PostgreSQL (progress summaries)
         └───> MinIO (screenshots via presigned URLs)

┌─────────────────┐
│ Agent Containers │
│  (Read/Write)    │
└────────┬────────┘
         │
         ├───> MongoDB (logs, memories)
         ├───> PostgreSQL (task progress + status)
         └───> MinIO (screenshots + binary files)

┌─────────────────┐
│  Evaluator      │
│  (Read + Scores)│
└────────┬────────┘
         │
         ├───> MongoDB Cluster (all agent logs)
         ├───> PostgreSQL (all tasks + evaluations)
         └───> MinIO (metadata only, not binaries)
```

## Storage Components

### MongoDB (Agent Logs)
- **Purpose**: Agent activity logs, memories, configuration
- **Access**:
  - Agents: Full read/write to their own database
  - Evaluator: Read access to all agent databases (clustered)

### PostgreSQL (Task Progress)
- **Purpose**: Task assignments, progress updates, evaluation scores
- **Tables**:
  - `tasks`: Task records
  - `task_progress`: Progress updates
  - `evaluations`: Evaluation scores and reports
  - `binary_file_metadata`: MinIO file metadata
- **Access**:
  - Agents: Write task progress and status updates
  - Evaluator: Full read/write (can write evaluations)
  - Frontend: Read-only (progress summaries)

### MinIO (Binary Files)
- **Purpose**: Screenshots, binary files, large data
- **Buckets**:
  - `screenshots`: Agent screenshots
  - `binaries`: Other binary files
- **Access**:
  - Agents: Full read/write to their namespace (agent_id/)
  - Evaluator: Read metadata only (from PostgreSQL)
  - Frontend: Read screenshots via presigned URLs

## Usage

### Agent Usage

```python
from storage import MongoAdapter, PostgresAdapter, MinIOAdapter

# MongoDB for logs
mongo = MongoAdapter(agent_id="agent1")
mongo.write_log("info", "Task started", task_id="123")
logs = mongo.read_logs(limit=10)

# PostgreSQL for progress
pg = PostgresAdapter()
task_id = pg.create_task(
    agent_id="agent1",
    title="Test Task",
    description="Test description"
)
pg.add_progress_update(task_id, "agent1", 50.0, "Halfway done")

# MinIO for screenshots
minio = MinIOAdapter(agent_id="agent1", postgres_adapter=pg)
object_path = minio.upload_screenshot(
    file_data=screenshot_bytes,
    task_id=task_id
)
```

### Evaluator Usage

```python
from storage import MongoAdapter, PostgresAdapter

# MongoDB cluster mode (read all agents)
mongo = MongoAdapter(cluster_mode=True)
all_logs = mongo.read_all_agent_logs(["agent1", "agent2", "agent3"])

# PostgreSQL (read all tasks, write evaluations)
pg = PostgresAdapter()
tasks = pg.get_tasks(limit=100)
evaluation_id = pg.create_evaluation(
    task_id=task_id,
    agent_id="agent1",
    score=85.5,
    report="Good performance"
)

# MinIO metadata (read only from PostgreSQL)
screenshots = pg.get_binary_files(bucket="screenshots", agent_id="agent1")
```

### Frontend Usage

```python
from storage import PostgresAdapter, MinIOAdapter

# PostgreSQL (read progress summaries)
pg = PostgresAdapter()
tasks = pg.get_tasks(status="completed", limit=10)
progress = pg.get_task_progress(task_id)

# MinIO (get presigned URLs for screenshots)
minio = MinIOAdapter()
url = minio.get_presigned_url("screenshots", object_path, expires_seconds=3600)
```

## Schema Definitions

### MongoDB Collections

**agent_logs**:
```json
{
  "level": "info|error|warning|debug",
  "message": "Log message",
  "agent_id": "agent1",
  "task_id": "optional_task_id",
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z"
}
```

**agent_memories**:
```json
{
  "content": "Memory content",
  "agent_id": "agent1",
  "memory_type": "general|task_result|observation",
  "task_id": "optional_task_id",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### PostgreSQL Tables

**tasks**:
- `id`: Integer (primary key)
- `agent_id`: String (indexed)
- `title`: String
- `description`: Text
- `status`: String (indexed)
- `metadata`: JSONB
- `created_at`: DateTime (indexed)
- `updated_at`: DateTime

**task_progress**:
- `id`: Integer (primary key)
- `task_id`: Integer (foreign key, indexed)
- `agent_id`: String (indexed)
- `progress_percent`: Float
- `message`: Text
- `data`: JSONB
- `timestamp`: DateTime (indexed)

**evaluations**:
- `id`: Integer (primary key)
- `task_id`: Integer (foreign key, indexed)
- `agent_id`: String (indexed)
- `score`: Float
- `report`: Text
- `metrics`: JSONB
- `created_at`: DateTime (indexed)

**binary_file_metadata**:
- `id`: Integer (primary key)
- `agent_id`: String (indexed)
- `task_id`: Integer (foreign key, nullable)
- `object_path`: String (unique, indexed)
- `bucket`: String (indexed)
- `content_type`: String
- `size_bytes`: Integer
- `metadata`: JSONB
- `uploaded_at`: DateTime (indexed)

### MinIO Object Structure

**Screenshots**:
- Bucket: `screenshots`
- Path format: `{agent_id}/screenshots/{filename}.png`
- Content-Type: `image/png`

**Binary Files**:
- Bucket: `binaries`
- Path format: `{agent_id}/{relative_path}`
- Content-Type: Varies

## Environment Variables

Required environment variables for each component:

### Agents
```
MONGODB_URL=mongodb://admin:password@mongodb:27017/agent1db?authSource=admin
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
AGENT_ID=agent1
```

### Evaluator
```
MONGODB_URL=mongodb://admin:password@mongodb:27017
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Frontend
```
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Evaluator Query Efficiency

The evaluator queries data efficiently using:

1. **MongoDB Cluster Mode**: Single adapter instance connects to multiple agent databases on-demand
2. **PostgreSQL Indexes**: Indexed columns for fast filtering (agent_id, status, task_id, timestamps)
3. **MinIO Metadata in PostgreSQL**: Binary file metadata stored in PostgreSQL for fast queries without downloading files
4. **Batch Reads**: Supports batch operations for reading logs from multiple agents

Example efficient query:
```python
# Read logs from all agents with a single adapter
mongo = MongoAdapter(cluster_mode=True)
all_logs = mongo.read_all_agent_logs(
    agent_ids=["agent1", "agent2", "agent3"],
    level="error",
    limit_per_agent=50
)

# Query task summaries without joining binary data
pg = PostgresAdapter()
tasks = pg.get_tasks(status="completed")
screenshot_metadata = pg.get_binary_files(bucket="screenshots", task_id=task_id)
```

## Migration Notes

### From Local Storage to Centralized

1. **Screenshots**: Migrate from `CUA/organized_traj/` to MinIO
2. **Logs**: Existing MongoDB structure is compatible
3. **Progress**: Move from trajectory JSON files to PostgreSQL `task_progress` table

### Backward Compatibility

- Existing `AgentDatabase` class can coexist with new adapters
- Gradual migration: agents can use both old and new storage during transition

## Installation

```bash
pip install -r storage/requirements.txt
```

## Setup

See `SETUP.md` for Docker and MinIO setup commands.

