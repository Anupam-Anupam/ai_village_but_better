# Complete Command Reference

All commands to build, run, and test the storage implementation.

## Quick Start (One Command)

### Linux/Mac:
```bash
chmod +x RUN_ALL.sh
./RUN_ALL.sh
```

### Windows PowerShell:
```powershell
.\RUN_ALL.ps1
```

## Step-by-Step Commands

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r storage/requirements.txt
pip install httpx asyncio

# Or use requirements.txt if it exists
pip install -r requirements.txt
```

### 2. Update Docker Compose (Add MinIO)

Add this to your `docker-compose.yml`:

```yaml
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    networks:
      - ai-village-network
    depends_on:
      - postgres
      - mongodb
```

And add to volumes section:
```yaml
volumes:
  mongodb_data:
  postgres_data:
  minio_data:
```

### 3. Build Docker Images

```bash
# Build all services
docker-compose build

# Build specific services
docker-compose build server agent1 postgres mongodb minio

# Rebuild after code changes
docker-compose build --no-cache
```

### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Start databases first
docker-compose up -d postgres mongodb minio
sleep 10
docker-compose up -d server agent1

# Start with logs visible
docker-compose up
```

### 5. Verify Services

```bash
# Check all services
docker-compose ps

# Check individual services
docker ps | grep -E "(postgres|mongodb|minio|agent1|server)"

# Check ports
netstat -tuln | grep -E ':(8000|8001|5432|27017|9000|9001)'
```

### 6. Test Service Health

```bash
# PostgreSQL
docker exec postgres pg_isready -U hub

# MongoDB
docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })"

# MinIO
curl http://localhost:9000/minio/health/live

# Agent
curl http://localhost:8001/

# Server
curl http://localhost:8000/
```

### 7. Set Environment Variables

**Linux/Mac:**
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

**Windows PowerShell:**
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

**Windows CMD:**
```cmd
set AGENT_ID=agent1
set MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
set POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
set MINIO_ENDPOINT=localhost:9000
set MINIO_ACCESS_KEY=minioadmin
set MINIO_SECRET_KEY=minioadmin
set AGENT_URL=http://localhost:8001
set SERVER_URL=http://localhost:8000
```

### 8. Run Tests

```bash
# Simple adapter tests
python test_storage_simple.py

# Full integration test
python test_storage_integration.py

# PowerShell verification (Windows)
.\test_storage_verification.ps1
```

### 9. View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f agent1
docker-compose logs -f server
docker-compose logs -f postgres
docker-compose logs -f mongodb
docker-compose logs -f minio

# Last 100 lines
docker-compose logs --tail=100 agent1
```

### 10. Verify Data in Databases

**MongoDB:**
```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin

# In MongoDB shell:
use agent1db
db.agent_logs.find().limit(5).pretty()
db.agent_memories.find().limit(5).pretty()
db.agent_config.find().pretty()
exit
```

**PostgreSQL:**
```bash
docker exec -it postgres psql -U hub -d hub

# In PostgreSQL:
SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 5;
SELECT * FROM task_progress WHERE agent_id = 'agent1' ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM binary_file_metadata WHERE agent_id = 'agent1' ORDER BY uploaded_at DESC LIMIT 5;
SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT 5;
\q
```

**MinIO:**
```bash
# List buckets
docker run --rm --network ai-village-network minio/mc:latest \
  alias set local http://minio:9000 minioadmin minioadmin && \
  minio/mc:latest ls local/

# List screenshots
docker run --rm --network ai-village-network minio/mc:latest \
  alias set local http://minio:9000 minioadmin minioadmin && \
  minio/mc:latest ls local/screenshots/agent1/
```

### 11. Test Agent Execution

```bash
# Write file
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"type":"write","filename":"test.txt","content":"Hello World"}'

# Get file
curl http://localhost:8001/files/test.txt

# Get screenshot
curl http://localhost:8001/open/test.txt

# Send message to server
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"message":"Test message"}'
```

### 12. Stop Services

```bash
# Stop all services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: deletes data)
docker-compose down -v
```

### 13. Clean Up

```bash
# Remove containers and networks
docker-compose down

# Remove volumes (deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Remove everything including unused images
docker system prune -a
```

### 14. Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart agent1

# Rebuild and restart
docker-compose up -d --build
```

## Complete Sequence

Run these commands in order:

```bash
# 1. Install dependencies
pip install -r storage/requirements.txt

# 2. Build images
docker-compose build

# 3. Start databases
docker-compose up -d postgres mongodb minio
sleep 10

# 4. Start applications
docker-compose up -d server agent1
sleep 5

# 5. Verify services
docker-compose ps
curl http://localhost:8000/
curl http://localhost:8001/

# 6. Set environment (Linux/Mac)
export AGENT_ID=agent1
export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin

# 7. Run tests
python test_storage_simple.py
python test_storage_integration.py

# 8. Verify data
docker exec -it postgres psql -U hub -d hub -c "SELECT COUNT(*) FROM tasks;"
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "use agent1db; db.agent_logs.countDocuments()"
```

## Troubleshooting Commands

```bash
# Check network connectivity
docker exec agent1 ping -c 3 postgres
docker exec agent1 ping -c 3 mongodb
docker exec agent1 ping -c 3 minio

# Check container logs
docker logs agent1
docker logs server
docker logs postgres
docker logs mongodb
docker logs minio

# Check port availability
netstat -tuln | grep -E ':(8000|8001|5432|27017|9000|9001)'

# Remove and recreate specific service
docker-compose rm -f agent1
docker-compose up -d --build agent1

# Execute command in container
docker exec -it agent1 bash
docker exec -it postgres psql -U hub -d hub
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin
```

## All-in-One Scripts

Use the automated scripts for complete setup:

**Linux/Mac:**
```bash
chmod +x RUN_ALL.sh
./RUN_ALL.sh
```

**Windows PowerShell:**
```powershell
.\RUN_ALL.ps1
```

These scripts will:
1. Install dependencies
2. Build Docker images
3. Start all services
4. Verify services are running
5. Set environment variables
6. Run all tests
7. Display summary

