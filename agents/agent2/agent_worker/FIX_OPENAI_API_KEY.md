# Fixing OpenAI API Key Error

## ✅ Good News: CUA Agent is Launching Successfully!

The diagnostics show that the CUA agent is working correctly:
- ✅ Packages installed
- ✅ Imports successful  
- ✅ Environment variables set
- ✅ ComputerAgent instance created
- ✅ Task execution started

## ❌ The Problem: Invalid OpenAI API Key

The error you're seeing is:
```
Incorrect API key provided: sk-proj-********************************************************************************************************************************************************bFcA
```

This means your `OPENAI_API_KEY` in the `.env` file is either:
1. **Incorrect/Invalid** - The key doesn't exist or has been revoked
2. **Expired** - The key has expired
3. **Wrong format** - The key is malformed
4. **Insufficient permissions** - The key doesn't have the right permissions

## Steps to Fix

### Step 1: Verify Your OpenAI API Key

1. **Go to OpenAI Platform:**
   - Visit: https://platform.openai.com/account/api-keys
   - Sign in to your OpenAI account

2. **Check your API keys:**
   - Look for active API keys
   - Make sure the key starts with `sk-` (for secret key)
   - Verify the key hasn't been revoked or expired

3. **Create a new API key if needed:**
   - Click "Create new secret key"
   - Copy the key immediately (you won't see it again)
   - Make sure it has proper permissions for API access

### Step 2: Update Your .env File

1. **Open your `.env` file** in the project root

2. **Update the OPENAI_API_KEY:**
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   ```
   
   **Important:**
   - Don't include quotes around the key
   - Don't include any spaces
   - Make sure there are no extra characters
   - The key should start with `sk-` or `sk-proj-`

3. **Save the file**

### Step 3: Verify the Key Format

Your OpenAI API key should:
- Start with `sk-` (standard keys) or `sk-proj-` (project keys)
- Be approximately 51 characters long
- Not contain any spaces or special characters (except hyphens)

Example format:
```
sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

### Step 4: Restart Docker Containers

After updating the `.env` file:

**Windows (PowerShell):**
```powershell
# Stop containers
docker-compose down

# Rebuild and start (to pick up new env vars)
docker-compose up -d --build agent_worker
```

**Linux/Mac:**
```bash
docker-compose down
docker-compose up -d --build agent_worker
```

### Step 5: Test Again

Run the test command:
```powershell
docker-compose run --rm agent_worker python /app/agent_worker/execute_task.py "Test task: print hello"
```

You should now see:
- ✅ All the same successful diagnostics
- ✅ Task execution completes without authentication errors
- ✅ No "Incorrect API key" error

## Alternative: Check Key in Container

To verify the key is being passed correctly to the container:

**Windows (PowerShell):**
```powershell
docker-compose run --rm agent_worker python -c "import os; key = os.getenv('OPENAI_API_KEY'); print(f'Key length: {len(key) if key else 0}'); print(f'Key starts with sk-: {key.startswith(\"sk-\") if key else False}')"
```

**Linux/Mac:**
```bash
docker-compose run --rm agent_worker python -c "import os; key = os.getenv('OPENAI_API_KEY'); print(f'Key length: {len(key) if key else 0}'); print(f'Key starts with sk-: {key.startswith(\"sk-\") if key else False}')"
```

Expected output:
- Key length: ~51 (or longer for project keys)
- Key starts with sk-: True

## Common Issues

### Issue: Key has extra whitespace
**Solution:** Remove any spaces before/after the key in `.env` file

### Issue: Key is wrapped in quotes
**Solution:** Remove quotes from the `.env` file:
```bash
# ❌ Wrong:
OPENAI_API_KEY="sk-..."

# ✅ Correct:
OPENAI_API_KEY=sk-...
```

### Issue: Using an organization key instead of personal key
**Solution:** Make sure you're using a key from your personal account, not an organization key that might have restrictions

### Issue: Key doesn't have API access enabled
**Solution:** Check your OpenAI account settings to ensure API access is enabled

## Verification

Once fixed, you should see successful task execution like:
```
✓ ComputerAgent instance created successfully
Starting task execution...
LLM processing started with 1 messages
[Task executes successfully]
Task completed successfully
```

Instead of the authentication error.

