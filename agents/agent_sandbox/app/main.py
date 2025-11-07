import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from .executor import run_shell_command, browse_url, write_file, read_file, generate_file, render_file_screenshot
from .screenshot_service import screenshot_loop

# Background task for taking screenshots
screenshot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the screenshot service
    global screenshot_task
    screenshot_task = asyncio.create_task(screenshot_loop(30))  # Take a screenshot every 30 seconds
    
    yield
    
    # Shutdown: Cancel the screenshot task
    if screenshot_task:
        screenshot_task.cancel()
        try:
            await screenshot_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="Agent Sandbox", version="0.1", lifespan=lifespan)

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
