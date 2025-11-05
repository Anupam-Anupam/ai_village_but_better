# Quick Start: Build, Run, and Test Storage Implementation

Complete command guide to build, run, and test the full storage system.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ installed
- Git (optional, for cloning)

## Step 1: Install Python Dependencies

```bash
# Install storage adapter dependencies
pip install -r storage/requirements.txt

# Install additional test dependencies
pip install httpx asyncio
```

## Step 2: Update Docker Compose (Add MinIO)

Add MinIO service to `docker-compose.yml`:

```yaml
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"  # MinIO API
      - "9001:9001"  # MinIO Console
    volumes:
      - minio_data:/data
    networks:
      - ai-village-network
    depends_on:
      - postgres
      - mongodb
```

Add to volumes section:
```yaml
volumes:
  mongodb_data:
  postgres_data:
  minio_data:
```

## Step 3: Build Docker Images

```bash
# Build all Docker images
docker-compose build

# Or build specific services
docker-compose build server agent1 postgres mongodb minio
```

## Step 4: Start All Services

```bash
# Start all services in background
docker-compose up -d

# Or start specific services first
docker-compose up -d postgres mongodb minio
sleep 5  # Wait for databases to initialize
docker-compose up -d server agent1

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 5: Verify Services Are Running

```bash
# Check PostgreSQL
docker exec -it postgres pg_isready -U hub

# Check MongoDB
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })"

# Check MinIO
curl http://localhost:9000/minio/health/live

# Check Agent (port 8001)
curl http://localhost:8001/

# Check Server (port 8000)
curl http://localhost:8000/
```

## Step 6: Initialize Database Schemas

```bash
# PostgreSQL tables are created automatically by SQLAlchemy
# But you can verify:
docker exec -it postgres psql -U hub -d hub -c "\dt"

# MongoDB collections are created automatically
# But you can verify:
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "use agent1db; show collections"
```

## Step 7: Set Environment Variables

### For Python Tests (Linux/Mac):

```bash
export AGENT_ID=agent1
export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export AGENT_URL=http://localhost:8001
export SERVER_URL=http://localhost:8000
```

### For Python Tests (Windows PowerShell):

```powershell
$env:AGENT_ID="agent1"
$env:MONGODB_URL="mongodb://admin:password@localhost:27017/agent1db?authSource=admin"
$env:POSTGRES_URL="postgresql://hub:hubpassword@localhost:5432/hub"
$env:MINIO_ENDPOINT="localhost:9000"
$env:MINIO_ACCESS_KEY="minioadmin"
$env:MINIO_SECRET_KEY="minioadmin"
$env:AGENT_URL="http://localhost:8001"
$env:SERVER_URL="http://localhost:8000"
```

### For Docker Containers (add to docker-compose.yml):

```yaml
  agent1:
    environment:
      - AGENT_ID=agent1
      - MONGODB_URL=mongodb://admin:password@mongodb:27017/agent1db?authSource=admin
      - POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
```

## Step 8: Run Simple Storage Tests

```bash
# Run simple adapter tests (tests adapters independently)
python test_storage_simple.py

# Expected output: All 3 tests should pass
```

## Step 9: Run Full Integration Tests

```bash
# Run full integration test with agent execution
python test_storage_integration.py

# Expected output: All 6 tests should pass
```

## Step 10: Run PowerShell Verification (Windows)

```powershell
# Run PowerShell verification script
.\test_storage_verification.ps1
```

## Step 11: Manual Verification Commands

### Verify MongoDB Data:

```bash
# Connect to MongoDB
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin

# Inside MongoDB shell:
use agent1db
db.agent_logs.find().limit(5).pretty()
db.agent_memories.find().limit(5).pretty()
db.agent_config.find().pretty()
exit
```

### Verify PostgreSQL Data:

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U hub -d hub

# Inside PostgreSQL:
SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 5;
SELECT * FROM task_progress WHERE agent_id = 'agent1' ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM binary_file_metadata WHERE agent_id = 'agent1' ORDER BY uploaded_at DESC LIMIT 5;
SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT 5;
\q
```

### Verify MinIO Data:

```bash
# Set up MinIO client alias
docker run -it --rm --network ai-village-network minio/mc:latest \
  alias set local http://minio:9000 minioadmin minioadmin

# List buckets
docker run -it --rm --network ai-village-network minio/mc:latest \
  ls local/

# List screenshots
docker run -it --rm --network ai-village-network minio/mc:latest \
  ls local/screenshots/agent1/

# Download a screenshot
docker run -it --rm --network ai-village-network -v $(pwd):/data minio/mc:latest \
  cp local/screenshots/agent1/test.png /data/
```

### Access MinIO Console:

Open browser to: `http://localhost:9001`
- Username: `minioadmin`
- Password: `minioadmin`

## Step 12: Test Agent Execution

### Test Agent Write Command:

```bash
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{
    "type": "write",
    "filename": "test.txt",
    "content": "Hello from storage test"
  }'
```

### Test Agent Screenshot:

```bash
curl -X GET http://localhost:8001/open/test.txt
```

### Test Server Message:

```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test message for storage verification"
  }'
```

## Step 13: View Logs

### View All Service Logs:

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific service logs
docker-compose logs -f agent1
docker-compose logs -f server
docker-compose logs -f postgres
docker-compose logs -f mongodb
docker-compose logs -f minio
```

### View Individual Container Logs:

```bash
docker logs agent1
docker logs server
docker logs postgres
docker logs mongodb
docker logs minio
```

## Step 14: Stop Services

```bash
# Stop all services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: deletes data)
docker-compose down -v
```

## Step 15: Clean Up (Optional)

```bash
# Remove all containers and networks
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Prune unused Docker resources
docker system prune -a
```

## Troubleshooting Commands

### Check Network Connectivity:

```bash
# Test connectivity between containers
docker exec agent1 ping -c 3 postgres
docker exec agent1 ping -c 3 mongodb
docker exec agent1 ping -c 3 minio
```

### Check Port Availability:

```bash
# Linux/Mac
netstat -tuln | grep -E ':(8000|8001|5432|27017|9000|9001)'

# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :5432
netstat -ano | findstr :27017
netstat -ano | findstr :9000
```

### Restart Services:

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart agent1
docker-compose restart server
```

### Rebuild After Code Changes:

```bash
# Rebuild and restart
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build agent1
```

## Complete Test Sequence

Run these commands in order:

```bash
# 1. Build
docker-compose build

# 2. Start services
docker-compose up -d postgres mongodb minio
sleep 5
docker-compose up -d server agent1
sleep 3

# 3. Verify services
docker-compose ps
curl http://localhost:8000/
curl http://localhost:8001/

# 4. Set environment (Linux/Mac)
export AGENT_ID=agent1
export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin

# 5. Run simple tests
python test_storage_simple.py

# 6. Run integration tests
python test_storage_integration.py

# 7. Manual verification
docker exec -it postgres psql -U hub -d hub -c "SELECT COUNT(*) FROM tasks;"
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "use agent1db; db.agent_logs.countDocuments()"
```

## Expected Results

After running all tests, you should see:

1. **MongoDB**: Log entries and memories in `agent1db`
2. **PostgreSQL**: 
   - Tasks in `tasks` table
   - Progress updates in `task_progress` table
   - Screenshot metadata in `binary_file_metadata` table
   - Request logs in `request_logs` table
3. **MinIO**: Screenshot files in `screenshots/agent1/` bucket

All tests should pass with ✓ marks.
