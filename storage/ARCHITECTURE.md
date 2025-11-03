# Storage Architecture Refactoring

## Overview

Refactored the storage system from per-container local storage to a centralized, scalable architecture using MongoDB, PostgreSQL, and MinIO.

## Access Control Matrix

| Component | MongoDB | PostgreSQL | MinIO |
|-----------|---------|------------|-------|
| **Agents** | Full read/write (own DB) | Write progress + status | Full read/write (own namespace) |
| **Evaluator** | Read all (clustered) | Read all + Write evaluations | Read metadata only |
| **Frontend** | N/A | Read summaries | Read screenshots (presigned URLs) |

## Data Flow

### Agent Writing Data

```
Agent Container
    │
    ├─> MongoDB: Write logs, memories
    ├─> PostgreSQL: Write task progress, update status
    └─> MinIO: Upload screenshots → PostgreSQL: Register metadata
```

### Evaluator Reading Data

```
Evaluator Container
    │
    ├─> MongoDB Cluster: Query all agent logs (on-demand DB connections)
    ├─> PostgreSQL: Query all tasks, progress, evaluations
    └─> PostgreSQL: Query binary_file_metadata (NOT MinIO directly)
```

### Frontend Reading Data

```
Frontend
    │
    ├─> PostgreSQL: Read task summaries, progress
    └─> MinIO: Get presigned URLs for screenshots
```

## Key Design Decisions

### 1. MongoDB Cluster Mode

Evaluator uses cluster mode to query multiple agent databases without maintaining persistent connections to all databases. Connections are created on-demand and cached.

**Efficiency**: O(1) adapter instances, O(N) connections only when needed.

### 2. PostgreSQL for Binary Metadata

MinIO file metadata is stored in PostgreSQL (`binary_file_metadata` table) instead of querying MinIO directly. This enables:
- Fast queries without downloading files
- Indexed searches (by agent_id, task_id, bucket, content_type)
- Relational joins with tasks and evaluations

**Efficiency**: PostgreSQL queries are orders of magnitude faster than MinIO list operations for metadata.

### 3. Namespace Isolation in MinIO

Agent files are stored under `{agent_id}/` prefix in buckets. This provides:
- Logical isolation without separate buckets per agent
- Easy filtering by agent_id
- Simple cleanup (delete prefix)

### 4. Presigned URLs for Frontend

Frontend receives presigned URLs instead of direct access tokens. This provides:
- Time-limited access (default 1 hour)
- No credential exposure to frontend
- Direct S3-compatible access (lower latency)

## Schema Relationships

```
tasks (PostgreSQL)
    ├─> task_progress (PostgreSQL) - One-to-many
    ├─> evaluations (PostgreSQL) - One-to-many
    └─> binary_file_metadata (PostgreSQL) - One-to-many (via task_id)

agent_logs (MongoDB per agent)
    └─> Referenced by task_id (soft foreign key)

agent_memories (MongoDB per agent)
    └─> Referenced by task_id (soft foreign key)
```

## Horizontal Scaling

### Kubernetes Compatibility

All components are designed for Kubernetes:

1. **StatefulSets for Databases**: MongoDB and PostgreSQL run as StatefulSets with persistent volumes
2. **Stateless Agent Pods**: Agents are stateless, connecting to shared databases
3. **Service Discovery**: Environment variables point to service names (e.g., `mongodb:27017`, `postgres:5432`, `minio:9000`)
4. **Horizontal Pod Autoscaling**: Agents can scale horizontally; databases scale vertically

### MinIO Scaling

MinIO supports distributed mode with multiple nodes for high availability and throughput.

## Migration Path

### Phase 1: Parallel Operation
- Deploy new adapters alongside existing code
- Agents can use both old and new storage during transition

### Phase 2: Data Migration
- Migrate screenshots from `CUA/organized_traj/` to MinIO
- Migrate trajectory JSON to PostgreSQL `task_progress` table

### Phase 3: Cutover
- Update agent code to use new adapters exclusively
- Remove old storage code

## Performance Considerations

### Indexes

**PostgreSQL**:
- `idx_agent_status`: Fast filtering by agent_id + status
- `idx_task_timestamp`: Fast task progress queries
- `idx_agent_task`: Fast binary file queries by agent + task

**MongoDB**:
- `agent_id`: Fast agent-specific queries
- `created_at`: Fast time-range queries
- `level`: Fast log level filtering

### Query Patterns

**Evaluator Efficiency**:
```python
# Efficient: Single query with indexes
tasks = pg.get_tasks(status="completed", limit=100)

# Efficient: Metadata only, no binary download
screenshots = pg.get_binary_files(bucket="screenshots", task_id=task_id)

# Efficient: Clustered read with caching
all_logs = mongo.read_all_agent_logs(["agent1", "agent2"], level="error")
```

**Avoid**:
```python
# Inefficient: Downloading all screenshots
for task in tasks:
    screenshot_data = minio.download_screenshot(task.screenshot_path)  # DON'T

# Efficient: Only download when needed
screenshot_metadata = pg.get_binary_files(task_id=task_id)
url = minio.get_presigned_url("screenshots", metadata[0].object_path)
```

## Security Considerations

1. **MinIO Access Keys**: Different keys per environment (dev/staging/prod)
2. **PostgreSQL Credentials**: Separate users with limited permissions
3. **MongoDB Authentication**: AuthSource-based authentication per agent
4. **Network Isolation**: Services communicate via Docker network

## Monitoring

### Metrics to Track

- MongoDB: Connection pool size, query latency, collection sizes
- PostgreSQL: Connection count, query latency, table sizes, index usage
- MinIO: Upload/download throughput, bucket sizes, request latency

### Health Checks

All adapters should implement health check methods:
- `mongo_adapter.health_check()`: Ping MongoDB
- `postgres_adapter.health_check()`: Query PostgreSQL
- `minio_adapter.health_check()`: List buckets

## Error Handling

Adapters implement graceful error handling:
- Connection retries with exponential backoff
- Transaction rollback on PostgreSQL errors
- Metadata registration failures don't block MinIO uploads (logged as warnings)

