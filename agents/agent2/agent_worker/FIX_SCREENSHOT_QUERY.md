# Fix Screenshot Query

The SUBSTRING pattern didn't match. Let's check the actual message format first.

## Step 1: Check Actual Message

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT message, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

This will show you the exact message format.

## Step 2: Alternative Query Methods

### Method 1: Use REPLACE to extract path

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT REPLACE(message, 'uploaded screenshot: ', '') as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

### Method 2: Use SPLIT_PART (if PostgreSQL version supports it)

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT SPLIT_PART(message, 'uploaded screenshot: ', 2) as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

### Method 3: Use REGEXP_REPLACE

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT REGEXP_REPLACE(message, '^uploaded screenshot: ', '') as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

### Method 4: Use RIGHT and POSITION

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT RIGHT(message, LENGTH(message) - POSITION('uploaded screenshot: ' IN message) - LENGTH('uploaded screenshot: ') + 1) as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

## Step 3: Check if Message Contains Screenshot Path

If the message doesn't contain "uploaded screenshot:", check what it actually contains:

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT message FROM task_progress WHERE task_id = 71 ORDER BY timestamp DESC LIMIT 10;"
```

This will show all recent messages for the task, so you can see the actual format.

## Step 4: Check Agent Worker Logs

The screenshot path is also logged in agent_worker logs:

```powershell
docker-compose logs agent_worker | Select-String -Pattern "71.*screenshot"
```

This will show messages like:
```
[agent1] Uploaded screenshot: agent1/screenshots/550e8400-e29b-41d4-a716-446655440000.png
```

## Quick Fix: Use REPLACE

The simplest fix is to use REPLACE:

```powershell
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT REPLACE(message, 'uploaded screenshot: ', '') as screenshot_path, timestamp FROM task_progress WHERE task_id = 71 AND message LIKE '%screenshot%' ORDER BY timestamp DESC;"
```

This removes the prefix and gives you just the path.

