# Agent Worker

Simple, robust, and minimal agent worker that runs inside each CUA agent container.

## Overview

The agent worker polls the central PostgreSQL `tasks` table for the current task, executes `run_task.py` when a task is found, tracks progress, uploads screenshots to MinIO, logs to MongoDB, and updates the task response.

## Environment Variables

The worker requires the following environment variables (set via `.env` file or environment):

### Required

- `POSTGRES_URL` or `POSTGRES_DSN` - PostgreSQL connection string (psycopg2 DSN format)
  - Example: `postgresql://user:password@host:5432/dbname`
  - Note: `POSTGRES_URL` is preferred to match existing codebase convention
  
- `MONGODB_URL` or `MONGO_URI` - MongoDB connection string
  - Example: `mongodb://admin:password@mongodb:27017/agent_logs_db?authSource=admin`
  - Note: `MONGODB_URL` is preferred to match existing codebase convention
  
- `MINIO_ENDPOINT` - MinIO endpoint
  - Example: `minio:9000` or `localhost:9000`
  
- `MINIO_ACCESS_KEY` - MinIO access key
  - Example: `minioadmin`
  
- `MINIO_SECRET_KEY` - MinIO secret key
  - Example: `minioadmin`
  
- `AGENT_ID` - Agent identifier (string or integer)
  - Example: `agent1` or `1`

### Optional

- `MINIO_SECURE` - Use HTTPS for MinIO (default: `false`)
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`
  
- `POLL_INTERVAL_SECONDS` - Polling interval in seconds (default: `5`)
  
- `RUN_TASK_TIMEOUT_SECONDS` - Task execution timeout in seconds (default: `300`)

## Sample .env File

### For Docker (inside Docker network)

```env
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
MONGODB_URL=mongodb://admin:password@mongodb:27017/agent_logs_db?authSource=admin
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
AGENT_ID=agent1
POLL_INTERVAL_SECONDS=5
RUN_TASK_TIMEOUT_SECONDS=300
```

### For Local Development (outside Docker)

```env
POSTGRES_URL=postgresql://hub:hubpassword@localhost:5433/hub
MONGODB_URL=mongodb://admin:password@localhost:27017/agent_logs_db?authSource=admin
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
AGENT_ID=agent1
POLL_INTERVAL_SECONDS=5
RUN_TASK_TIMEOUT_SECONDS=300
```

**Note**: When running outside Docker, use `localhost` instead of service names (`postgres`, `mongodb`, `minio`), and use the mapped port `5433` for PostgreSQL instead of `5432`.

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure `run_task.py` is available in the same directory or parent directory of the worker.

3. Set up environment variables (see above).

## Running the Worker

### Docker (Recommended)

The worker is designed to run inside a Docker container. It's already configured in `docker-compose.yml`:

```bash
# Build and start the agent worker
docker-compose up -d agent_worker

# View logs
docker-compose logs -f agent_worker

# Stop the worker
docker-compose stop agent_worker
```

The worker will automatically:
- Connect to PostgreSQL using service name `postgres:5432`
- Connect to MongoDB using service name `mongodb:27017`
- Connect to MinIO using service name `minio:9000`
- Use the `ai-village-network` Docker network

### Manual Command (Local Development)

If running outside Docker (not recommended for production):

From the project root:

```bash
python -m agents.agent1.agent_worker.main
```

Or from the `agent_worker` directory:

```bash
python main.py
```

**Note**: When running outside Docker, you must use `localhost` instead of service names and the mapped ports (e.g., `localhost:5433` for PostgreSQL).

## How It Works

1. **Polling**: The worker polls the `tasks` table every `POLL_INTERVAL_SECONDS` for the most recent task.

2. **Progress Check**: If a task is found, it checks `task_progress` for the maximum progress percent. If progress >= 100, the task is skipped.

3. **Task Execution**: If progress < 100:
   - Creates a unique working directory (`/tmp/agent_work/<AGENT_ID>/<task_id>/<timestamp>`)
   - Ensures `./screenshots/` directory exists
   - Snapshots existing files in `./screenshots/`
   - Executes `run_task.py` via subprocess with timeout
   - Writes heartbeat progress updates while task runs

4. **Screenshot Upload**: After task completion:
   - Detects newly created files in `./screenshots/`
   - Uploads each new file to MinIO bucket `screenshots` at path `agent<AGENT_ID>/screenshots/<uuid>.png`
   - Inserts progress updates for each upload

5. **Logging**: All events are logged to MongoDB `agent_logs` collection with fields:
   - `agent_id`
   - `task_id`
   - `level` (info, error, warning, debug)
   - `message`
   - `metadata`
   - `timestamp`

6. **Task Update**: Updates the `tasks` table with final response and inserts final progress row with percent 100.

## Logs

- **MongoDB**: Logs are written to the `agent_logs` collection in the database specified by `MONGODB_URL` or `MONGO_URI`.
- **Console**: The worker also prints log messages to stdout/stderr for container logs.

## Error Handling

- All errors are caught, logged to MongoDB, and the worker continues polling (no fatal exit).
- Database connection errors trigger reconnection attempts.
- Task execution errors are logged but don't stop the worker.

## Graceful Shutdown

The worker handles `SIGTERM` and `SIGINT` signals for graceful shutdown:
- Stops the polling loop
- Completes current task execution (if any)
- Closes database connections
- Cleans up working directories

## Database Schema Assumptions

The worker assumes the following PostgreSQL tables exist:

- `tasks`: Contains task records with columns: `id`, `agent_id`, `title`, `description`, `status`, `metadata`, `created_at`, `updated_at`
- `task_progress`: Contains progress updates with columns: `task_id`, `agent_id`, `progress_percent` (or `percent`), `message`, `timestamp` (or `created_at`)
- `binary_file_metadata`: Optional table for file metadata (if present, metadata is inserted here)

The worker handles missing columns gracefully by trying alternative column names and logging warnings.

