from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
from .executor import run_shell_command, browse_url, write_file, read_file, generate_file, render_file_screenshot
import asyncpg
import httpx
import json
from typing import Any

app = FastAPI(title="Agent Sandbox", version="0.1")

# New: DB pool for task routing to CUA agents
DATABASE_URL = os.environ.get("DATABASE_URL")  # e.g. postgres://user:pass@host:port/dbname
_db_pool: asyncpg.pool.Pool | None = None

@app.on_event("startup")
async def _startup():
    global _db_pool
    if DATABASE_URL:
        _db_pool = await asyncpg.create_pool(DATABASE_URL, max_size=8)
    else:
        _db_pool = None  # DB operations will error if missing

@app.on_event("shutdown")
async def _shutdown():
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None

async def _fetch_task(task_id: int) -> Any:
    if not _db_pool:
        raise HTTPException(status_code=500, detail="database not configured")
    row = await _db_pool.fetchrow("SELECT id, status, payload, agent_url FROM tasks WHERE id=$1", task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row

async def _update_task_status(task_id: int, status: str, result: Any | None = None):
    if not _db_pool:
        raise HTTPException(status_code=500, detail="database not configured")
    if result is None:
        await _db_pool.execute("UPDATE tasks SET status=$1, updated_at=now() WHERE id=$2", status, task_id)
    else:
        # store result as JSON text
        await _db_pool.execute(
            "UPDATE tasks SET status=$1, result=$2::jsonb, updated_at=now() WHERE id=$3",
            status, json.dumps(result), task_id
        )

async def run_task(task_id: int) -> Any:
    """
    Route the task to its configured CUA agent, store the agent response in DB,
    and return the response. No placeholder messages are written to the DB.
    Expected tasks table columns: id, status, payload (jsonb), agent_url (text), result (jsonb).
    """
    row = await _fetch_task(task_id)
    task_status = row["status"]
    if task_status == "completed":
        # return stored result if already completed
        if not _db_pool:
            raise HTTPException(status_code=500, detail="database not configured")
        stored = await _db_pool.fetchrow("SELECT result FROM tasks WHERE id=$1", task_id)
        return stored["result"] if stored else None

    # mark processing (no human-readable placeholder)
    await _update_task_status(task_id, "processing")

    agent_url = row.get("agent_url")
    if not agent_url:
        await _update_task_status(task_id, "failed", {"error": "missing agent_url"})
        raise HTTPException(status_code=400, detail="task missing agent_url")

    payload = row.get("payload") or {}

    # POST to CUA agent and capture response
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(agent_url, json=payload)
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = {"status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        err = {"error": str(e)}
        await _update_task_status(task_id, "failed", err)
        raise HTTPException(status_code=502, detail=err)

    # store final response and mark completed
    await _update_task_status(task_id, "completed", resp_data)
    return resp_data

# New endpoint to run a task and return the agent response stored in DB
@app.post("/tasks/{task_id}/run")
async def run_task_endpoint(task_id: int):
    """
    Trigger routing of the task to its CUA agent, persist agent response in Postgres,
    and return the agent response to the frontend.
    """
    result = await run_task(task_id)
    return {"task_id": task_id, "result": result}

class ExecutePayload(BaseModel):
    type: str = "shell"   # "shell", "browse", "write", or "generate"
    command: str = ""     # used for shell or browse (browse uses command as URL)
    filename: str | None = None   # used for write/generate
    content: str | None = None    # used for write
    instruction: str | None = None # used for generate

@app.post("/execute")
async def execute(payload: ExecutePayload):
    """
    Execute a sandboxed command.
    Payload JSON:
      - shell:    { "type":"shell", "command":"echo hello" }
      - browse:   { "type":"browse", "command":"https://example.com" }
      - write:    { "type":"write",  "filename":"hello.py", "content":"print(\"hi\")" }
      - generate: { "type":"generate","filename":"hello.py","instruction":"Create a Python script that prints 'hi'."}
    """
    if payload.type == "shell":
        if not payload.command:
            raise HTTPException(status_code=400, detail="command required for shell")
        result = await run_shell_command(payload.command)
        return result

    if payload.type == "browse":
        if not payload.command:
            raise HTTPException(status_code=400, detail="url required for browse")
        result = await browse_url(payload.command)
        return result

    if payload.type == "write":
        if not payload.filename or payload.content is None:
            raise HTTPException(status_code=400, detail="filename and content required for write")
        result = await write_file(payload.filename, payload.content)
        return result

    # New: generate from instruction — return generation result plus file content when successful
    if payload.type == "generate":
        if not payload.filename or not payload.instruction:
            raise HTTPException(status_code=400, detail="filename and instruction required for generate")
        gen_result = await generate_file(payload.filename, payload.instruction)
        if gen_result.get("status") == "ok":
            # read file content and include it in the response for immediate verification
            read_result = await read_file(payload.filename)
            return {"generate": gen_result, "file": read_result}
        else:
            return gen_result

    raise HTTPException(status_code=400, detail="invalid type; allowed: shell, browse, write, generate")

# New endpoint: safely fetch a file from the agent workdir
@app.get("/files/{filename}")
async def get_file(filename: str):
    """
    Return the content of a file in the agent workdir.
    Filename must be a simple basename (no slashes/traversal).
    """
    result = await read_file(filename)
    if result.get("status") == "ok":
        return {"filename": filename, "content": result["stdout"]}
    elif result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=result.get("stderr", "not found"))
    else:
        raise HTTPException(status_code=400, detail=result.get("stderr", "error"))

@app.get("/open/{filename}")
async def open_file(filename: str):
    """
    Render the named file inside the agent workdir and return a PNG screenshot (base64).
    Example: GET /open/story.txt
    Response JSON: { "filename": "story.txt", "screenshot": "<base64_png>" }
    """
    result = await render_file_screenshot(filename)
    if result.get("status") == "ok":
        return {"filename": filename, "screenshot": result["screenshot"]}
    elif result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=result.get("stderr", "not found"))
    elif result.get("status") == "unavailable":
        raise HTTPException(status_code=503, detail=result.get("stderr", "playwright unavailable"))
    else:
        raise HTTPException(status_code=400, detail=result.get("stderr", "error"))

@app.post("/edit/{filename}")
async def edit_file(filename: str, payload: dict):
    """
    Open a file in a text editor (nano/gedit) for manual editing.
    Example: POST /edit/story.txt
    Response: Instructions for manual editing
    """
    # Validate filename
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Check if file exists
    result = await read_file(filename)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return manual instructions for editing
    return {
        "filename": filename,
        "message": f"To edit {filename}, run one of these commands manually:",
        "commands": [
            f"nano {filename}",
            f"gedit {filename}",
            f"cat {filename}  # to view current content"
        ],
        "note": "File editing requires manual terminal access to the container"
    }
