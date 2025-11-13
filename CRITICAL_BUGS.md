# Critical Bugs Found in Codebase

## 🔴 CRITICAL BUGS (Will Crash at Runtime)

### 1. **Undefined Functions in `server/main.py` - `run_task()` Will Crash**
**File:** `server/main.py:461-537`
**Severity:** CRITICAL - Will cause NameError when endpoint is called
**Issue:**
```python
async def run_task(task_id: int) -> Any:
    row = await _fetch_task(task_id)  # ❌ _fetch_task is never defined!
    # ...
    if not _db_pool:  # ❌ _db_pool is never defined!
        raise HTTPException(status_code=500, detail="database not configured")
    stored = await _db_pool.fetchrow(...)  # ❌ _db_pool is never defined!
    # ...
    await _update_task_status(task_id, "processing")  # ❌ _update_task_status is never defined!
    # ...
    await _update_task_status(task_id, "failed", err)  # ❌ _update_task_status is never defined!
    # ...
    await _update_task_status(task_id, "completed", result_payload)  # ❌ _update_task_status is never defined!
```

**Impact:**
- Any call to the `run_task()` function will immediately crash with `NameError`
- This function appears to be dead code (no endpoint calls it), but if it's ever used, it will fail

**Fix:**
- Delete the `run_task()` function entirely (it's not used by any endpoint)
- OR implement the missing functions if this endpoint is needed

---

### 2. **Missing `traceback` Import**
**File:** `server/main.py:134`
**Severity:** CRITICAL - Will cause NameError during agent initialization
**Issue:**
```python
print("Traceback:", traceback.format_exc())  # ❌ traceback not imported!
```

**Impact:**
- If CUA agent initialization fails, the error handler will crash with `NameError: name 'traceback' is not defined`
- Prevents proper error logging during startup

**Fix:**
- Add `import traceback` at the top of the file

---

### 3. **Agent Worker Task Polling is Broken - Race Condition**
**File:** `agents/agent1/agent_worker/db_adapters.py:72-95`
**Severity:** CRITICAL - All agents will compete for the same task
**Issue:**
```python
def get_current_task(self) -> Optional[Dict[str, Any]]:
    """Get the most recent task from the tasks table."""
    # ❌ No filtering by agent_id
    # ❌ No atomic locking
    # ❌ All agents will get the same task
    cur.execute("""
        SELECT id, agent_id, title, description, status, 
               metadata, created_at, updated_at
        FROM tasks
        ORDER BY COALESCE(updated_at, created_at) DESC
        LIMIT 1
    """)
```

**Impact:**
- All three agent workers will try to execute the same task simultaneously
- No atomic locking means race conditions
- Tasks won't be properly distributed to agents
- Multiple agents will waste resources on the same task

**Fix:**
- Use `PostgresAdapter.claim_next_pending_task(agent_id)` instead
- This method uses row-level locking (`SELECT ... FOR UPDATE`) to prevent race conditions
- Each agent should call `claim_next_pending_task()` with their own `agent_id`

**Current State:**
- `PostgresAdapter` does NOT have `claim_next_pending_task()` method - **IT'S MISSING!**
- `PostgresClient` in `db_adapters.py` uses `get_current_task()` which has no locking
- Agent workers use `PostgresClient.get_current_task()` which is broken
- **Need to implement `claim_next_pending_task()` in `PostgresAdapter`** with row-level locking

---

## ⚠️ MEDIUM SEVERITY BUGS

### 4. **Task Assignment Logic is Wrong**
**File:** `server/main.py:211`
**Severity:** MEDIUM - Tasks assigned incorrectly
**Issue:**
```python
# Assign task to an agent (round-robin)
agent = AGENTS[task_id % len(AGENTS)]  # ❌ Wrong logic!
```

**Problem:**
- `task_id` is an auto-incrementing integer (1, 2, 3, 4, ...)
- Using modulo will assign: task 1→agent1, task 2→agent2, task 3→agent3, task 4→agent1, etc.
- This is actually correct for round-robin, BUT:
  - The task is already created with `agent_id="frontend"` (line 203)
  - Then it's updated to "assigned" status (line 215)
  - But the actual `agent_id` field in the task is still "frontend", not the assigned agent
  - The metadata has `assigned_agent_id` but the task's `agent_id` field is wrong

**Fix:**
- Update the task's `agent_id` field, not just metadata:
  ```python
  pg.update_task_status(
      task_id=task_id,
      status="assigned",
      agent_id=agent_id,  # Update the agent_id field
      metadata={"assigned_agent_id": agent_id}
  )
  ```

---

### 5. **Agent ID Mismatch Between Server and Workers**
**File:** `server/main.py:83-85` vs `docker-compose.yml:89, 115, 141`
**Severity:** MEDIUM - Confusing but might work due to normalization
**Issue:**
- Server uses: `agent1-cua`, `agent2-cua`, `agent3-cua`
- Docker Compose uses: `AGENT_ID=agent1`, `AGENT_ID=agent2`, `AGENT_ID=agent3`
- Agent workers normalize IDs (e.g., `agent1-cua` → `agent1`), so this might work
- But it's confusing and could cause issues

**Fix:**
- Standardize on one format everywhere
- Either use `agent1-cua` everywhere OR `agent1` everywhere

---

## 📋 SUMMARY

**Immediate Actions Required:**
1. ✅ **Delete `run_task()` function** from `server/main.py` (it's broken and unused)
2. ✅ **Add `import traceback`** to `server/main.py`
3. ✅ **Fix agent worker polling** - Use `claim_next_pending_task()` instead of `get_current_task()`
4. ✅ **Fix task assignment** - Update `agent_id` field, not just metadata

**Files to Fix:**
- `server/main.py` - Delete `run_task()`, add `traceback` import
- `agents/agent1/agent_worker/runner.py` - Use `claim_next_pending_task()`
- `agents/agent2/agent_worker/runner.py` - Use `claim_next_pending_task()`
- `agents/agent3/agent_worker/runner.py` - Use `claim_next_pending_task()`
- `agents/agent1/agent_worker/db_adapters.py` - Add `claim_next_pending_task()` method or use PostgresAdapter
- `server/main.py:211-219` - Fix task assignment to update `agent_id` field

