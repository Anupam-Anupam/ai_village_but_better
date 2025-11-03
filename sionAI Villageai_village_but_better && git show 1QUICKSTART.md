[1mdiff --cc QUICKSTART.md[m
[1mindex ea1dfb6,a381e97..0000000[m
[1m--- a/QUICKSTART.md[m
[1m+++ b/QUICKSTART.md[m
[36m@@@ -1,420 -1,418 +1,0 @@@[m
[31m--# Quick Start: Build, Run, and Test Storage Implementation[m
[31m--[m
[31m--Complete command guide to build, run, and test the full storage system.[m
[31m--[m
[31m--## Prerequisites[m
[31m--[m
[31m--- Docker and Docker Compose installed[m
[31m--- Python 3.8+ installed[m
[31m--- Git (optional, for cloning)[m
[31m--[m
[31m--## Step 1: Install Python Dependencies[m
[31m--[m
[31m--```bash[m
[31m--# Install storage adapter dependencies[m
[31m--pip install -r storage/requirements.txt[m
[31m--[m
[31m--# Install additional test dependencies[m
[31m--pip install httpx asyncio[m
[31m--```[m
[31m--[m
[31m--## Step 2: Update Docker Compose (Add MinIO)[m
[31m--[m
[31m--Add MinIO service to `docker-compose.yml`:[m
[31m--[m
[31m--```yaml[m
[31m--  minio:[m
[31m--    image: minio/minio:latest[m
[31m--    command: server /data --console-address ":9001"[m
[31m--    environment:[m
[31m--      MINIO_ROOT_USER: minioadmin[m
[31m--      MINIO_ROOT_PASSWORD: minioadmin[m
[31m--    ports:[m
[31m--      - "9000:9000"  # MinIO API[m
[31m--      - "9001:9001"  # MinIO Console[m
[31m--    volumes:[m
[31m--      - minio_data:/data[m
[31m--    networks:[m
[31m--      - ai-village-network[m
[31m--    depends_on:[m
[31m--      - postgres[m
[31m--      - mongodb[m
[31m--```[m
[31m--[m
[31m--Add to volumes section:[m
[31m--```yaml[m
[31m--volumes:[m
[31m--  mongodb_data:[m
[31m--  postgres_data:[m
[31m--  minio_data:[m
[31m--```[m
[31m--[m
[31m--## Step 3: Build Docker Images[m
[31m--[m
[31m--```bash[m
[31m--# Build all Docker images[m
[31m--docker-compose build[m
[31m--[m
[31m--# Or build specific services[m
[31m--docker-compose build server agent1 postgres mongodb minio[m
[31m--```[m
[31m--[m
[31m--## Step 4: Start All Services[m
[31m--[m
[31m--```bash[m
[31m--# Start all services in background[m
[31m--docker-compose up -d[m
[31m--[m
[31m--# Or start specific services first[m
[31m--docker-compose up -d postgres mongodb minio[m
[31m--sleep 5  # Wait for databases to initialize[m
[31m--docker-compose up -d server agent1[m
[31m--[m
[31m--# Check service status[m
[31m--docker-compose ps[m
[31m--[m
[31m--# View logs[m
[31m--docker-compose logs -f[m
[31m--```[m
[31m--[m
[31m--## Step 5: Verify Services Are Running[m
[31m--[m
[31m--```bash[m
[31m--# Check PostgreSQL[m
[31m--docker exec -it postgres pg_isready -U hub[m
[31m--[m
[31m--# Check MongoDB[m
[31m--docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })"[m
[31m--[m
[31m--# Check MinIO[m
[31m--curl http://localhost:9000/minio/health/live[m
[31m--[m
[31m--# Check Agent (port 8001)[m
[31m--curl http://localhost:8001/[m
[31m--[m
[31m--# Check Server (port 8000)[m
[31m--curl http://localhost:8000/[m
[31m--```[m
[31m--[m
[31m--## Step 6: Initialize Database Schemas[m
[31m--[m
[31m--```bash[m
[31m--# PostgreSQL tables are created automatically by SQLAlchemy[m
[31m--# But you can verify:[m
[31m--docker exec -it postgres psql -U hub -d hub -c "\dt"[m
[31m--[m
[31m--# MongoDB collections are created automatically[m
[31m--# But you can verify:[m
[31m--docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "use agent1db; show collections"[m
[31m--```[m
[31m--[m
[31m--## Step 7: Set Environment Variables[m
[31m--[m
[31m--### For Python Tests (Linux/Mac):[m
[31m--[m
[31m--```bash[m
[31m--export AGENT_ID=agent1[m
[31m--export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin[m
[31m--export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub[m
[31m--export MINIO_ENDPOINT=localhost:9000[m
[31m--export MINIO_ACCESS_KEY=minioadmin[m
[31m--export MINIO_SECRET_KEY=minioadmin[m
[31m--export AGENT_URL=http://localhost:8001[m
[31m--export SERVER_URL=http://localhost:8000[m
[31m--```[m
[31m--[m
[31m--### For Python Tests (Windows PowerShell):[m
[31m--[m
[31m--```powershell[m
[31m--$env:AGENT_ID="agent1"[m
[31m--$env:MONGODB_URL="mongodb://admin:password@localhost:27017/agent1db?authSource=admin"[m
[31m--$env:POSTGRES_URL="postgresql://hub:hubpassword@localhost:5432/hub"[m
[31m--$env:MINIO_ENDPOINT="localhost:9000"[m
[31m--$env:MINIO_ACCESS_KEY="minioadmin"[m
[31m--$env:MINIO_SECRET_KEY="minioadmin"[m
[31m--$env:AGENT_URL="http://localhost:8001"[m
[31m--$env:SERVER_URL="http://localhost:8000"[m
[31m--```[m
[31m--[m
[31m--### For Docker Containers (add to docker-compose.yml):[m
[31m--[m
[31m--```yaml[m
[31m--  agent1:[m
[31m--    environment:[m
[31m--      - AGENT_ID=agent1[m
[31m--      - MONGODB_URL=mongodb://admin:password@mongodb:27017/agent1db?authSource=admin[m
[31m--      - POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub[m
[31m--      - MINIO_ENDPOINT=minio:9000[m
[31m--      - MINIO_ACCESS_KEY=minioadmin[m
[31m--      - MINIO_SECRET_KEY=minioadmin[m
[31m--```[m
[31m--[m
[31m--## Step 8: Run Simple Storage Tests[m
[31m--[m
[31m--```bash[m
[31m--# Run simple adapter tests (tests adapters independently)[m
[31m--python test_storage_simple.py[m
[31m--[m
[31m--# Expected output: All 3 tests should pass[m
[31m--```[m
[31m--[m
[31m--## Step 9: Run Full Integration Tests[m
[31m--[m
[31m--```bash[m
[31m--# Run full integration test with agent execution[m
[31m--python test_storage_integration.py[m
[31m--[m
[31m--# Expected output: All 6 tests should pass[m
[31m--```[m
[31m--[m
[31m--## Step 10: Run PowerShell Verification (Windows)[m
[31m--[m
[31m--```powershell[m
[31m--# Run PowerShell verification script[m
[31m--.\test_storage_verification.ps1[m
[31m--```[m
[31m--[m
[31m--## Step 11: Manual Verification Commands[m
[31m--[m
[31m--### Verify MongoDB Data:[m
[31m--[m
[31m--```bash[m
[31m--# Connect to MongoDB[m
[31m--docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin[m
[31m--[m
[31m--# Inside MongoDB shell:[m
[31m--use agent1db[m
[31m--db.agent_logs.find().limit(5).pretty()[m
[31m--db.agent_memories.find().limit(5).pretty()[m
[31m--db.agent_config.find().pretty()[m
[31m--exit[m
[31m--```[m
[31m--[m
[31m--### Verify PostgreSQL Data:[m
[31m--[m
[31m--```bash[m
[31m--# Connect to PostgreSQL[m
[31m--docker exec -it postgres psql -U hub -d hub[m
[31m--[m
[31m--# Inside PostgreSQL:[m
[31m--SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 5;[m
[31m--SELECT * FROM task_progress WHERE agent_id = 'agent1' ORDER BY timestamp DESC LIMIT 5;[m
[31m--SELECT * FROM binary_file_metadata WHERE agent_id = 'agent1' ORDER BY uploaded_at DESC LIMIT 5;[m
[31m--SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT 5;[m
[31m--\q[m
[31m--```[m
[31m--[m
[31m--### Verify MinIO Data:[m
[31m--[m
[31m--```bash[m
[31m--# Set up MinIO client alias[m
[31m--docker run -it --rm --network ai-village-network minio/mc:latest \[m
[31m--  alias set local http://minio:9000 minioadmin minioadmin[m
[31m--[m
[31m--# List buckets[m
[31m--docker run -it --rm --network ai-village-network minio/mc:latest \[m
[31m--  ls local/[m
[31m--[m
[31m--# List screenshots[m
[31m--docker run -it --rm --network ai-village-network minio/mc:latest \[m
[31m--  ls local/screenshots/agent1/[m
[31m--[m
[31m--# Download a screenshot[m
[31m--docker run -it --rm --network ai-village-network -v $(pwd):/data minio/mc:latest \[m
[31m--  cp local/screenshots/agent1/test.png /data/[m
[31m--```[m
[31m--[m
[31m--### Access MinIO Console:[m
[31m--[m
[31m--Open browser to: `http://localhost:9001`[m
[31m--- Username: `minioadmin`[m
[31m--- Password: `minioadmin`[m
[31m--[m
[31m--## Step 12: Test Agent Execution[m
[31m--[m
[31m--### Test Agent Write Command:[m
[31m--[m
[31m--```bash[m
[31m--curl -X POST http://localhost:8001/execute \[m
[31m--  -H "Content-Type: application/json" \[m
[31m--  -d '{[m
[31m--    "type": "write",[m
[31m--    "filename": "test.txt",[m
[31m--    "content": "Hello from storage test"[m
[31m--  }'[m
[31m--```[m
[31m--[m
[31m--### Test Agent Screenshot:[m
[31m--[m
[31m--```bash[m
[31m--curl -X GET http://localhost:8001/open/test.txt[m
[31m--```[m
[31m--[m
[31m--### Test Server Message:[m
[31m--[m
[31m--```bash[m
[31m--curl -X POST http://localhost:8000/message \[m
[31m--  -H "Content-Type: application/json" \[m
[31m--  -d '{[m
[31m--    "message": "Test message for storage verification"[m
[31m--  }'[m
[31m--```[m
[31m--[m
[31m--## Step 13: View Logs[m
[31m--[m
[31m--### View All Service Logs:[m
[31m--[m
[31m--```bash[m
[31m--# View all logs[m
[31m--docker-compose logs[m
[31m--[m
[31m--# Follow logs in real-time[m
[31m--docker-compose logs -f[m
[31m--[m
[31m--# View specific service logs[m
[31m--docker-compose logs -f agent1[m
[31m--docker-compose logs -f server[m
[31m--docker-compose logs -f postgres[m
[31m--docker-compose logs -f mongodb[m
[31m--docker-compose logs -f minio[m
[31m--```[m
[31m--[m
[31m--### View Individual Container Logs:[m
[31m--[m
[31m--```bash[m
[31m--docker logs agent1[m
[31m--docker logs server[m
[31m--docker logs postgres[m
[31m--docker logs mongodb[m
[31m--docker logs minio[m
[31m--```[m
[31m--[m
[31m--## Step 14: Stop Services[m
[31m--[m
[31m--```bash[m
[31m--# Stop all services[m
[31m--docker-compose stop[m
[31m--[m
[31m--# Stop and remove containers[m
[31m--docker-compose down[m
[31m--[m
[31m--# Stop and remove containers + volumes (WARNING: deletes data)[m
[31m--docker-compose down -v[m
[31m--```[m
[31m--[m
[31m--## Step 15: Clean Up (Optional)[m
[31m--[m
[31m--```bash[m
[31m--# Remove all containers and networks[m
[31m--docker-compose down[m
[31m--[m
[31m--# Remove volumes (WARNING: deletes all data)[m
[31m--docker-compose down -v[m
[31m--[m
[31m--# Remove images[m
[31m--docker-compose down --rmi all[m
[31m--[m
[31m--# Prune unused Docker resources[m
[31m--docker system prune -a[m
[31m--```[m
[31m--[m
[31m--## Troubleshooting Commands[m
[31m--[m
[31m--### Check Network Connectivity:[m
[31m--[m
[31m--```bash[m
[31m--# Test connectivity between containers[m
[31m--docker exec agent1 ping -c 3 postgres[m
[31m--docker exec agent1 ping -c 3 mongodb[m
[31m--docker exec agent1 ping -c 3 minio[m
[31m--```[m
[31m--[m
[31m--### Check Port Availability:[m
[31m--[m
[31m--```bash[m
[31m--# Linux/Mac[m
[31m--netstat -tuln | grep -E ':(8000|8001|5432|27017|9000|9001)'[m
[31m--[m
[31m--# Windows[m
[31m--netstat -ano | findstr :8000[m
[31m--netstat -ano | findstr :8001[m
[31m--netstat -ano | findstr :5432[m
[31m--netstat -ano | findstr :27017[m
[31m--netstat -ano | findstr :9000[m
[31m--```[m
[31m--[m
[31m--### Restart Services:[m
[31m--[m
[31m--```bash[m
[31m--# Restart all services[m
[31m--docker-compose restart[m
[31m--[m
[31m--# Restart specific service[m
[31m--docker-compose restart agent1[m
[31m--docker-compose restart server[m
[31m--```[m
[31m--[m
[31m--### Rebuild After Code Changes:[m
[31m--[m
[31m--```bash[m
[31m--# Rebuild and restart[m
[31m--docker-compose up -d --build[m
[31m--[m
[31m--# Rebuild specific service[m
[31m--docker-compose up -d --build agent1[m
[31m--```[m
[31m--[m
[31m--## Complete Test Sequence[m
[31m--[m
[31m--Run these commands in order:[m
[31m--[m
[31m--```bash[m
[31m--# 1. Build[m
[31m--docker-compose build[m
[31m--[m
[31m--# 2. Start services[m
[31m--docker-compose up -d postgres mongodb minio[m
[31m--sleep 5[m
[31m--docker-compose up -d server agent1[m
[31m--sleep 3[m
[31m--[m
[31m--# 3. Verify services[m
[31m--docker-compose ps[m
[31m--curl http://localhost:8000/[m
[31m--curl http://localhost:8001/[m
[31m--[m
[31m--# 4. Set environment (Linux/Mac)[m
[31m--export AGENT_ID=agent1[m
[31m--export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin[m
[31m--export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub[m
[31m--export MINIO_ENDPOINT=localhost:9000[m
[31m--export MINIO_ACCESS_KEY=minioadmin[m
[31m--export MINIO_SECRET_KEY=minioadmin[m
[31m--[m
[31m--# 5. Run simple tests[m
[31m--python test_storage_simple.py[m
[31m--[m
[31m--# 6. Run integration tests[m
[31m--python test_storage_integration.py[m
[31m--[m
[31m--# 7. Manual verification[m
[31m--docker exec -it postgres psql -U hub -d hub -c "SELECT COUNT(*) FROM tasks;"[m
[31m--docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin --eval "use agent1db; db.agent_logs.countDocuments()"[m
[31m--```[m
[31m--[m
[31m--## Expected Results[m
[31m--[m
[31m--After running all tests, you should see:[m
[31m--[m
[31m--1. **MongoDB**: Log entries and memories in `agent1db`[m
[31m--2. **PostgreSQL**: [m
[31m--   - Tasks in `tasks` table[m
[31m--   - Progress updates in `task_progress` table[m
[31m--   - Screenshot metadata in `binary_file_metadata` table[m
[31m--   - Request logs in `request_logs` table[m
[31m--3. **MinIO**: Screenshot files in `screenshots/agent1/` bucket[m
[31m--[m
[31m--All tests should pass with ✓ marks.[m
[31m- [m
[31m--[m
[31m- ==========================================================================[m
