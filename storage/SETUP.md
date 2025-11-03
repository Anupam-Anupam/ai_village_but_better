# Storage System Setup Guide

Manual setup commands for Docker, MinIO, PostgreSQL, and MongoDB.

## Prerequisites

- Docker and Docker Compose installed
- Access to terminal/command prompt

## 1. Docker Compose Setup

### Add MinIO to docker-compose.yml

Add the following service to your `docker-compose.yml`:

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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
```

### Update existing services

Update agent services to include MinIO environment variables:

```yaml
  agent1:
    # ... existing config ...
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AGENT_ID=1
      - HUB_URL=http://server:8000
      - MONGODB_URL=mongodb://admin:password@mongodb:27017/agent1db?authSource=admin
      - POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      - mongodb
      - postgres
      - minio
```

### Update volumes section

```yaml
volumes:
  mongodb_data:
  postgres_data:
  minio_data:
```

## 2. Manual Docker Commands

### Start MinIO container

```bash
docker run -d \
  --name minio \
  --network ai-village-network \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -v minio_data:/data \
  minio/minio:latest server /data --console-address ":9001"
```

### Start PostgreSQL container (if not using docker-compose)

```bash
docker run -d \
  --name postgres \
  --network ai-village-network \
  -e POSTGRES_USER=hub \
  -e POSTGRES_PASSWORD=hubpassword \
  -e POSTGRES_DB=hub \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15
```

### Start MongoDB container (if not using docker-compose)

```bash
docker run -d \
  --name mongodb \
  --network ai-village-network \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:7.0
```

## 3. MinIO Setup Commands

### Access MinIO Console

Open browser to: `http://localhost:9001`

Login credentials:
- Username: `minioadmin`
- Password: `minioadmin`

### Create buckets manually (if needed)

Buckets are created automatically by the adapter, but you can create them manually:

```bash
# Using MinIO client (mc)
docker run -it --rm \
  --network ai-village-network \
  -v $(pwd):/data \
  minio/mc:latest \
  alias set local http://minio:9000 minioadmin minioadmin

docker run -it --rm \
  --network ai-village-network \
  -v $(pwd):/data \
  minio/mc:latest \
  mb local/screenshots

docker run -it --rm \
  --network ai-village-network \
  -v $(pwd):/data \
  minio/mc:latest \
  mb local/binaries
```

### Set bucket policies (optional)

Make screenshots bucket publicly readable for frontend:

```bash
docker run -it --rm \
  --network ai-village-network \
  -v $(pwd):/data \
  minio/mc:latest \
  policy set download local/screenshots
```

## 4. PostgreSQL Schema Initialization

### Connect to PostgreSQL

```bash
docker exec -it postgres psql -U hub -d hub
```

### Verify tables exist

```sql
\dt
```

Expected tables:
- `tasks`
- `task_progress`
- `evaluations`
- `binary_file_metadata`

### Manual table creation (if needed)

Tables are created automatically by SQLAlchemy, but you can verify with:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

## 5. MongoDB Verification

### Connect to MongoDB

```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin
```

### List databases

```javascript
show dbs
```

Expected databases:
- `agent1db`
- `agent2db`
- `agent3db`
- `serverdb`

### Verify collections

```javascript
use agent1db
show collections
```

Expected collections:
- `agent_logs`
- `agent_memories`
- `agent_config`

## 6. Environment Variables

### Agent containers

```bash
# MongoDB
MONGODB_URL=mongodb://admin:password@mongodb:27017/agent1db?authSource=admin

# PostgreSQL
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
AGENT_ID=1
```

### Evaluator service

```bash
# MongoDB (cluster mode)
MONGODB_URL=mongodb://admin:password@mongodb:27017

# PostgreSQL
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub

# MinIO (read-only metadata)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Frontend service

```bash
# PostgreSQL (read-only)
POSTGRES_URL=postgresql://hub:hubpassword@postgres:5432/hub

# MinIO (read screenshots)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## 7. Testing Commands

### Test MinIO connection

```bash
docker run -it --rm \
  --network ai-village-network \
  minio/mc:latest \
  alias set test http://minio:9000 minioadmin minioadmin && \
  minio/mc:latest ls test
```

### Test PostgreSQL connection

```bash
docker exec -it postgres psql -U hub -d hub -c "SELECT COUNT(*) FROM tasks;"
```

### Test MongoDB connection

```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin -eval "db.runCommand({ connectionStatus: 1 })"
```

## 8. Network Configuration

### Verify network exists

```bash
docker network ls | grep ai-village-network
```

### Create network if missing

```bash
docker network create ai-village-network
```

## 9. Health Checks

### MinIO health

```bash
curl http://localhost:9000/minio/health/live
```

Expected: `200 OK`

### PostgreSQL health

```bash
docker exec -it postgres pg_isready -U hub
```

### MongoDB health

```bash
docker exec -it mongodb mongosh -u admin -p password --authenticationDatabase admin -eval "db.runCommand({ ping: 1 })"
```

## 10. Troubleshooting

### View MinIO logs

```bash
docker logs minio
```

### View PostgreSQL logs

```bash
docker logs postgres
```

### View MongoDB logs

```bash
docker logs mongodb
```

### Reset MinIO data

```bash
docker stop minio
docker rm minio
docker volume rm minio_data
# Then recreate using commands above
```

### Reset PostgreSQL data

```bash
docker stop postgres
docker rm postgres
docker volume rm postgres_data
# Then recreate using commands above
```

### Reset MongoDB data

```bash
docker stop mongodb
docker rm mongodb
docker volume rm mongodb_data
# Then recreate using commands above
```

