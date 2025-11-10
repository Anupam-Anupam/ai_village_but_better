# Database Query Commands

Quick reference for querying the PostgreSQL database to check tasks, progress, and responses.

## Container Name

The PostgreSQL container name may vary. Common names:
- `ai_village_but_better-postgres-1` (default docker-compose naming)
- `postgres` (if using service name directly)

**To find your container name:**
```powershell
docker ps | Select-String postgres
```

## Basic Connection

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub
```

## Common Queries

### 1. List All Recent Tasks

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, agent_id, title, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 10;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, agent_id, title, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 10;"
```

### 2. Get Specific Task Details

Replace `<TASK_ID>` with the actual task ID:

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM tasks WHERE id = <TASK_ID>;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM tasks WHERE id = <TASK_ID>;"
```

### 3. Get Task Response (from metadata)

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response, metadata->>'last_agent' as last_agent FROM tasks WHERE id = <TASK_ID>;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response, metadata->>'last_agent' as last_agent FROM tasks WHERE id = <TASK_ID>;"
```

### 4. Get Task Progress Updates

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

### 5. Get Formatted Progress Summary

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, agent_id, progress_percent, message, timestamp FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, agent_id, progress_percent, message, timestamp FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp DESC LIMIT 10;"
```

### 6. Count Tasks by Status

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT status, COUNT(*) as count FROM tasks GROUP BY status;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT status, COUNT(*) as count FROM tasks GROUP BY status;"
```

### 7. Get Latest Task for Agent

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 1;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT * FROM tasks WHERE agent_id = 'agent1' ORDER BY created_at DESC LIMIT 1;"
```

### 8. Get Tasks with Responses

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response FROM tasks WHERE metadata->>'response' IS NOT NULL ORDER BY updated_at DESC LIMIT 10;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response FROM tasks WHERE metadata->>'response' IS NOT NULL ORDER BY updated_at DESC LIMIT 10;"
```

### 9. Get Maximum Progress for a Task

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, MAX(COALESCE(progress_percent, percent, 0)) as max_progress FROM task_progress WHERE task_id = <TASK_ID> GROUP BY task_id;"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT task_id, MAX(COALESCE(progress_percent, percent, 0)) as max_progress FROM task_progress WHERE task_id = <TASK_ID> GROUP BY task_id;"
```

### 10. List All Tables

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\dt"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\dt"
```

### 11. Describe Table Structure

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\d tasks"
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\d task_progress"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\d tasks"
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\d task_progress"
```

## Interactive Mode

To enter interactive psql mode:

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub
```

Then you can run SQL queries directly:
```sql
SELECT * FROM tasks ORDER BY created_at DESC LIMIT 5;
SELECT * FROM task_progress WHERE task_id = 1 ORDER BY timestamp DESC;
\q  -- to exit
```

## Quick Test Queries

### Find Latest Task ID
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -t -c "SELECT id FROM tasks ORDER BY created_at DESC LIMIT 1;"
```

### Check if Task Has Response
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, CASE WHEN metadata->>'response' IS NOT NULL THEN 'Has Response' ELSE 'No Response' END as has_response FROM tasks WHERE id = <TASK_ID>;"
```

### Get All Progress Messages for Task
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT timestamp, message, progress_percent FROM task_progress WHERE task_id = <TASK_ID> ORDER BY timestamp ASC;"
```

## MongoDB Logs (Optional)

If you want to check MongoDB logs:

**Windows (PowerShell):**
```powershell
docker exec -it ai_village_but_better-mongodb-1 mongosh -u admin -p password --authenticationDatabase admin --eval "use agent_logs_db; db.agent_logs.find().sort({timestamp: -1}).limit(5).pretty()"
```

**Linux/Mac:**
```bash
docker exec -it ai_village_but_better-mongodb-1 mongosh -u admin -p password --authenticationDatabase admin --eval "use agent_logs_db; db.agent_logs.find().sort({timestamp: -1}).limit(5).pretty()"
```

## Example: Complete Task Check

Here's a complete example to check a task:

```powershell
# 1. Get latest task ID
$taskId = docker exec ai_village_but_better-postgres-1 psql -U hub -d hub -t -c "SELECT id FROM tasks ORDER BY created_at DESC LIMIT 1;" | ForEach-Object { $_.Trim() }

# 2. Get task details
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, description, status, created_at FROM tasks WHERE id = $taskId;"

# 3. Get progress
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT progress_percent, message, timestamp FROM task_progress WHERE task_id = $taskId ORDER BY timestamp DESC LIMIT 5;"

# 4. Get response
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT metadata->>'response' as response FROM tasks WHERE id = $taskId;"
```

## Troubleshooting

### If container name is different:

Find the correct name:
```powershell
docker ps --format "table {{.Names}}\t{{.Image}}" | Select-String postgres
```

### If connection fails:

Check if container is running:
```powershell
docker ps | Select-String postgres
```

### If you get "relation does not exist":

The tables might not be created yet. Check if tables exist:
```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "\dt"
```

