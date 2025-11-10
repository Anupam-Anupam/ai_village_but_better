# Testing CUA Agent Launch in Docker Container

This guide will help you test that the CUA agent launches correctly in the Docker container after the fixes.

## Prerequisites

1. **Ensure your `.env` file has the required variables:**
   ```bash
   CUA_API_KEY=your_cua_api_key_here
   CUA_SANDBOX_NAME=your_sandbox_name_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

2. **Docker Desktop must be running**

## Step-by-Step Testing

### Step 1: Rebuild the Docker Container

Since we made changes to the Dockerfile and docker-compose.yml, rebuild the container:

**Windows (PowerShell):**
```powershell
docker-compose build agent_worker
```

**Linux/Mac:**
```bash
docker-compose build agent_worker
```

### Step 2: Verify Environment Variables

Check that environment variables are being passed to the container:

**Windows (PowerShell):**
```powershell
docker-compose run --rm agent_worker env | Select-String -Pattern "CUA_|OPENAI_"
```

**Linux/Mac:**
```bash
docker-compose run --rm agent_worker env | grep -E "CUA_|OPENAI_"
```

You should see:
- `CUA_API_KEY=...`
- `CUA_SANDBOX_NAME=...`
- `OPENAI_API_KEY=...`

### Step 3: Test CUA Package Installation

Verify that CUA packages are installed:

**Windows (PowerShell):**
```powershell
docker-compose run --rm agent_worker pip list | Select-String -Pattern "cua"
```

**Linux/Mac:**
```bash
docker-compose run --rm agent_worker pip list | grep -i cua
```

You should see packages like:
- `cua-agent`
- `cua-computer`
- `cua-som`

### Step 4: Test CUA Package Imports

Test that the CUA packages can be imported:

**Windows (PowerShell):**
```powershell
docker-compose run --rm agent_worker python -c "from agent import ComputerAgent; from computer import Computer, VMProviderType; print('SUCCESS: CUA packages imported correctly')"
```

**Linux/Mac:**
```bash
docker-compose run --rm agent_worker python -c "from agent import ComputerAgent; from computer import Computer, VMProviderType; print('SUCCESS: CUA packages imported correctly')"
```

Expected output: `SUCCESS: CUA packages imported correctly`

### Step 5: Test execute_task.py with Diagnostics

Test the execute_task.py script directly with the new diagnostics:

**Windows (PowerShell):**
```powershell
docker-compose run --rm agent_worker python /app/agent_worker/execute_task.py "Test task: print hello world"
```

**Linux/Mac:**
```bash
docker-compose run --rm agent_worker python /app/agent_worker/execute_task.py "Test task: print hello world"
```

**What to look for:**
- ✅ `=== CUA Package Diagnostics ===`
- ✅ `Packages installed (via pip): True`
- ✅ `Agent module importable: True`
- ✅ `Computer module importable: True`
- ✅ `Checking CUA environment variables...`
- ✅ `✓ CUA_API_KEY is set (length: ...)`
- ✅ `✓ CUA_SANDBOX_NAME: ...`
- ✅ `✓ OPENAI_API_KEY is set (length: ...)`
- ✅ `Attempting to import CUA packages...`
- ✅ `✓ Successfully imported ComputerAgent from agent module`
- ✅ `✓ Successfully imported Computer and VMProviderType from computer module`
- ✅ `Creating Computer instance...`
- ✅ `✓ Computer instance created successfully`
- ✅ `Creating ComputerAgent instance...`
- ✅ `✓ ComputerAgent instance created successfully`
- ✅ `Starting task execution...`

If you see any ✗ (cross) marks, check the error messages for details.

### Step 6: Start the Full Stack and Test

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Watch the agent_worker logs:**
   ```bash
   docker-compose logs -f agent_worker
   ```

3. **Create a test task in the database:**

   **Windows (PowerShell):**
   ```powershell
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "INSERT INTO tasks (agent_id, title, description, status, metadata) VALUES ('test_user', 'Test CUA Agent', 'Create a file named test.txt with content Hello World', 'pending', '{}') RETURNING id;"
   ```

   **Linux/Mac:**
   ```bash
   docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "INSERT INTO tasks (agent_id, title, description, status, metadata) VALUES ('test_user', 'Test CUA Agent', 'Create a file named test.txt with content Hello World', 'pending', '{}') RETURNING id;"
   ```

4. **Monitor the logs** - You should see:
   - Task picked up by agent_worker
   - CUA Package Diagnostics output
   - CUA agent initialization
   - Task execution progress
   - Task completion

### Step 7: Check Task Results

After the task completes, check the results:

```bash
docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c "SELECT id, title, status, metadata->>'response' as response FROM tasks WHERE title = 'Test CUA Agent' ORDER BY created_at DESC LIMIT 1;"
```

The response should NOT contain "fallback mode - CUA agent not available" if everything is working correctly.

## Troubleshooting

### If CUA packages fail to import:

1. **Check the build logs:**
   ```bash
   docker-compose build agent_worker 2>&1 | Select-String -Pattern "ERROR|WARNING|cua"
   ```

2. **Verify the Dockerfile patch was applied:**
   ```bash
   docker-compose run --rm agent_worker cat /usr/local/lib/python3.12/site-packages/agent/agent.py | Select-String -Pattern "item.get\('name'\)"
   ```

### If environment variables are missing:

1. **Check your `.env` file exists and has the variables**
2. **Verify docker-compose is reading the .env file:**
   ```bash
   docker-compose config | Select-String -Pattern "CUA_|OPENAI_"
   ```

### If you see "fallback mode" in the output:

Check the detailed error messages in the logs. The improved error handling will show:
- Which import failed
- Which environment variable is missing
- Full traceback of the error

## Quick Test Script

You can also use the existing verification script:

**Windows (PowerShell):**
```powershell
.\agents\agent1\agent_worker\verify_cua_installation.ps1
```

This will run all the checks automatically.

## Success Criteria

✅ All tests pass if:
1. CUA packages are installed and importable
2. Environment variables are set correctly
3. ComputerAgent and Computer instances can be created
4. Tasks execute using the CUA agent (not fallback mode)
5. No "CUA agent not available" messages in the output

