# Starting Agent Worker Service

## Quick Start

### 1. Start Agent Worker

```powershell
docker-compose up -d agent_worker
```

This will:
- Build the image if needed
- Start the container in detached mode
- Connect to PostgreSQL, MongoDB, and MinIO

### 2. Check if it's Running

```powershell
docker-compose ps agent_worker
```

**Expected output:**
```
NAME                    STATUS
agent_worker            Up
```

### 3. Check Logs

```powershell
docker-compose logs agent_worker
```

**Expected log output:**
```
[agent1] Starting agent worker...
[agent1] Configuration:
  - PostgreSQL: postgresql://hub:hubpassword@postgres:5432/hub...
  - MongoDB: mongodb://admin:password@mongodb:27017/agent_logs_db...
  - MinIO: minio:9000
  - Poll interval: 5s
  - Task timeout: 300s
[agent1] Connected to PostgreSQL
[agent1] Connected to MongoDB
[agent1] Connected to MinIO
[agent1] Agent worker started
[agent1] No task found, polling again in 5s...
```

### 4. Watch Logs in Real-Time

```powershell
docker-compose logs -f agent_worker
```

Press `Ctrl+C` to stop watching.

## Troubleshooting

### Issue 1: Container Fails to Start

**Check logs:**
```powershell
docker-compose logs agent_worker
```

**Common errors:**
- **Connection refused** → Dependencies (postgres, mongodb, minio) not running
- **Build failed** → Docker image needs to be rebuilt
- **Environment variables missing** → Check `.env` file

**Solution:**
```powershell
# Start dependencies first
docker-compose up -d postgres mongodb minio

# Wait a few seconds for them to start
Start-Sleep -Seconds 5

# Then start agent_worker
docker-compose up -d agent_worker
```

### Issue 2: Build Required

If the image doesn't exist or needs rebuilding:

```powershell
docker-compose build agent_worker
docker-compose up -d agent_worker
```

### Issue 3: Environment Variables Missing

Check if required environment variables are set:

```powershell
docker-compose config | Select-String -Pattern "CUA_|OPENAI_|POSTGRES_"
```

**Required variables:**
- `CUA_API_KEY`
- `CUA_SANDBOX_NAME`
- `OPENAI_API_KEY`
- `POSTGRES_URL`
- `MONGODB_URL`

**Solution:** Create or update `.env` file in project root.

### Issue 4: Container Keeps Restarting

**Check logs:**
```powershell
docker-compose logs agent_worker --tail 50
```

**Common causes:**
- Database connection failure
- Missing environment variables
- Import errors

**Solution:**
```powershell
# Check what's failing
docker-compose logs agent_worker | Select-String -Pattern "ERROR|Failed|Exception"

# Restart with fresh build
docker-compose down agent_worker
docker-compose build agent_worker
docker-compose up -d agent_worker
```

### Issue 5: Container Exits Immediately

**Check exit code:**
```powershell
docker-compose ps agent_worker
```

**Check logs:**
```powershell
docker-compose logs agent_worker
```

**Solution:** Fix the error shown in logs, then restart.

## Verify It's Working

### 1. Check Status

```powershell
docker-compose ps agent_worker
```

Should show: `Up` or `running`

### 2. Check Logs

```powershell
docker-compose logs agent_worker --tail 20
```

Should show:
- `[agent1] Agent worker started`
- `[agent1] No task found, polling again in 5s...` (repeating every 5 seconds)

### 3. Test Task Processing

Once agent_worker is running, it should automatically pick up pending tasks. Check if your task (ID 71) gets processed:

```powershell
# Watch logs
docker-compose logs -f agent_worker

# In another terminal, check task status
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status FROM tasks WHERE id = 71;"
```

You should see:
```
[agent1] Task 71 picked: Test Task: make a python file...
```

## Full Startup Sequence

If starting everything from scratch:

```powershell
# 1. Start all dependencies
docker-compose up -d postgres mongodb minio

# 2. Wait for services to be ready
Start-Sleep -Seconds 10

# 3. Start agent_worker
docker-compose up -d agent_worker

# 4. Check status
docker-compose ps

# 5. Watch logs
docker-compose logs -f agent_worker
```

## Stop Agent Worker

```powershell
# Stop (keeps container)
docker-compose stop agent_worker

# Stop and remove container
docker-compose down agent_worker
```

## Restart Agent Worker

```powershell
docker-compose restart agent_worker
```

## Check Dependencies

Agent worker depends on:
- `postgres` - PostgreSQL database
- `mongodb` - MongoDB for logs
- `minio` - MinIO for file storage

**Check if dependencies are running:**
```powershell
docker-compose ps postgres mongodb minio
```

All should show `Up` status.

