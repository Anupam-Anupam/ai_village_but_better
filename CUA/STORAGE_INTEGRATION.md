# CUA Agent Storage Integration

Integration between CUA agent and storage adapters (MongoDB, PostgreSQL, MinIO).

## What It Does

When enabled, the CUA agent automatically stores:
- **Logs** → MongoDB (agent messages, computer calls, errors)
- **Task Progress** → PostgreSQL (task records, progress updates)
- **Screenshots** → MinIO (images from computer_call_output)

## How to Use

### 1. Set Environment Variables

```powershell
# Storage adapters
$env:MONGODB_URL = "mongodb://admin:password@localhost:27017/cua_agentdb?authSource=admin"
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:MINIO_ACCESS_KEY = "minioadmin"
$env:MINIO_SECRET_KEY = "minioadmin"
$env:AGENT_ID = "cua_agent"

# CUA credentials (required)
$env:CUA_API_KEY = "your_cua_api_key"
$env:CUA_SANDBOX_NAME = "your_sandbox_name"
$env:OPENAI_API_KEY = "your_openai_api_key"
```

### 2. Run CUA Agent with Storage

The agent automatically detects storage adapters and uses them:

```powershell
cd CUA
python main.py
```

Or run the test:

```powershell
python test_cua_full_storage.py
```

## What Gets Stored

### MongoDB (`cua_agentdb`)
- **agent_logs**: Agent messages, computer calls, screenshot uploads
- **agent_memories**: (Not used by CUA integration currently)

### PostgreSQL (`hub`)
- **tasks**: Task records with description and status
- **task_progress**: Progress updates during execution
- **binary_file_metadata**: Screenshot metadata (links to MinIO)

### MinIO (`screenshots` bucket)
- **Screenshot files**: Under `cua_agent/screenshots/`
- Metadata stored in PostgreSQL for efficient querying

## Running the Full Test

```powershell
# Set all environment variables
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
$env:MONGODB_URL = "mongodb://admin:password@localhost:27017/cua_agentdb?authSource=admin"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:MINIO_ACCESS_KEY = "minioadmin"
$env:MINIO_SECRET_KEY = "minioadmin"
$env:AGENT_ID = "cua_agent"
$env:CUA_API_KEY = "your_key"
$env:CUA_SANDBOX_NAME = "your_sandbox"
$env:OPENAI_API_KEY = "your_key"

# Run test
python test_cua_full_storage.py
```

The test will:
1. Initialize storage adapters
2. Record baseline counts
3. Execute a CUA agent task
4. Verify data appears in all storage systems
5. Report verification results

## Verification Queries

After running, verify data manually:

**MongoDB:**
```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin
use cua_agentdb
db.agent_logs.find().sort({created_at: -1}).limit(10)
```

**PostgreSQL:**
```bash
docker exec -it postgres psql -U hub -d hub
SELECT * FROM tasks WHERE agent_id = 'cua_agent' ORDER BY created_at DESC LIMIT 5;
SELECT * FROM task_progress WHERE agent_id = 'cua_agent' ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM binary_file_metadata WHERE agent_id = 'cua_agent' ORDER BY uploaded_at DESC LIMIT 5;
```

**MinIO:**
Check metadata in PostgreSQL (binary_file_metadata table) or list objects:
```bash
docker run -it --rm --network ai-village-network minio/mc:latest \
  alias set local http://minio:9000 minioadmin minioadmin && \
  minio/mc:latest ls local/screenshots/cua_agent/
```

