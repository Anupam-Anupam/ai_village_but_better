# Fix PostgreSQL Connection Issues

## Issue
PostgreSQL password authentication failed for user "hub"

## Solutions

### Option 1: Use Docker Container Name (Recommended)

If you're running the test from outside Docker, you need to connect to `localhost:5432`. However, if there's a local PostgreSQL instance, it might interfere.

**Fix: Stop local PostgreSQL and use Docker:**

```powershell
# Stop local PostgreSQL service (if running)
Stop-Service postgresql*  # If you have local PostgreSQL

# Verify Docker PostgreSQL is running
docker ps | Select-String postgres

# Set environment variables
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5432/hub"
$env:MONGODB_URL = "mongodb://admin:password@localhost:27017/agent1db?authSource=admin"
$env:MINIO_ENDPOINT = "localhost:9000"
$env:MINIO_ACCESS_KEY = "minioadmin"
$env:MINIO_SECRET_KEY = "minioadmin"
$env:AGENT_ID = "agent1"

# Test connection
python test_connection.py
```

### Option 2: Reset PostgreSQL Container

If the container was initialized with wrong credentials:

```powershell
# Stop and remove PostgreSQL container
docker-compose stop postgres
docker-compose rm -f postgres

# Remove the volume (WARNING: deletes data)
docker volume rm ai_village_but_better_postgres_data

# Start PostgreSQL again
docker-compose up -d postgres

# Wait for initialization
Start-Sleep -Seconds 10

# Verify connection
docker exec ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT 1;"
```

### Option 3: Check Docker Compose Credentials

Verify your `docker-compose.yml` has:

```yaml
postgres:
  environment:
    POSTGRES_USER: hub
    POSTGRES_PASSWORD: hubpassword
    POSTGRES_DB: hub
```

### Option 4: Use Different Port

If local PostgreSQL is using port 5432, change Docker PostgreSQL port:

1. Edit `docker-compose.yml`:
```yaml
postgres:
  ports:
    - "5433:5432"  # Change from 5432 to 5433
```

2. Update connection string:
```powershell
$env:POSTGRES_URL = "postgresql://hub:hubpassword@localhost:5433/hub"
```

### Quick Fix Commands

```powershell
# 1. Check if containers are running
docker ps

# 2. Check PostgreSQL container logs
docker logs ai_village_but_better-postgres-1

# 3. Test direct connection to container
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT 1;"

# 4. If direct connection works but Python doesn't, check:
#    - Environment variable is set correctly
#    - No local PostgreSQL on port 5432
#    - Connection string format is correct
```

## Verify Connection

Run this test:
```powershell
python test_connection.py
```

It should show:
```
✓ Connected to PostgreSQL: postgresql://hub:hubpassword@localhost:5432/hub
✓ Connected to MongoDB: ...
✓ Connected to MinIO: ...
```

