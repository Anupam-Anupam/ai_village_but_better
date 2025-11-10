"""
AI Village Server
=================
Manages tasks and agent communication.
Uses PostgreSQL for task management and MongoDB for logs.
"""

import os
import json
import httpx
import asyncio
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List, Union
from pymongo import MongoClient

# Import storage adapters
from storage.postgres_adapter import PostgresAdapter
from storage.mongo_adapter import MongoAdapter

# Add CUA to path
import sys
sys.path.append(str(Path(__file__).parent.parent / 'CUA'))

# Import CUA components
CUA_AVAILABLE = False
try:
    # Add parent directory to path for CUA imports
    cua_path = Path(__file__).parent.parent / 'CUA'
    if cua_path.exists():
        sys.path.insert(0, str(cua_path))
        from storage_integration import execute_task_with_storage, initialize_storage_adapters
        from main import run_agent_example, ComputerAgent
        CUA_AVAILABLE = True
        print("✅ CUA components imported successfully")
    else:
        print(f"⚠️  CUA directory not found at {cua_path}")
except ImportError as e:
    print(f"⚠️  Could not import CUA components: {e}")

# Import storage adapters
try:
    from storage import PostgresAdapter
except ImportError as e:
    print(f"⚠️  Could not import storage adapters: {e}")
    raise

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PostgreSQL
pg = PostgresAdapter()

# Initialize MinIO adapter for generating screenshot URLs
try:
    minio_adapter = MinIOAdapter(agent_id="frontend_viewer", postgres_adapter=pg)
    MINIO_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Warning: Failed to initialize MinIO adapter: {e}")
    minio_adapter = None
    MINIO_AVAILABLE = False

# MongoDB connection for logs
try:
    # Use the service name fr   om docker-compose
    mongo_uri = "mongodb://admin:password@mongodb:27017/serverdb?authSource=admin"
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Force a connection test
    server_db = mongo_client.serverdb
    print("✅ Successfully connected to MongoDB")
    print(f"Connection URL: {mongo_uri}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print("Make sure MongoDB service is running and accessible at mongodb:27017")
    server_db = None

# Agent configurations
AGENTS = [
    {"id": "agent1-cua", "url": "http://host.docker.internal:8001/execute"},
    {"id": "agent2-cua", "url": "http://host.docker.internal:8002/execute"},
    {"id": "agent3-cua", "url": "http://host.docker.internal:8003/execute"}
]

# Initialize CUA agent instances
cua_agents = {}
if CUA_AVAILABLE:
    try:
        print("\n=== Initializing CUA agents ===")
        print(f"Found {len(AGENTS)} agent configurations")
        
        for agent in AGENTS:
            agent_id = agent["id"]
            print(f"\n--- Initializing agent: {agent_id} ---")
            
            try:
                # Initialize storage adapters for each agent
                storage = {}
                if 'initialize_storage_adapters' in globals():
                    print("Initializing storage adapters...")
                    try:
                        storage = initialize_storage_adapters(agent_id=agent_id)
                        print(f"✅ Storage initialized for {agent_id}")
                        print(f"Storage adapters: {', '.join(storage.keys()) if storage else 'None'}")
                    except Exception as storage_error:
                        print(f"⚠️  Failed to initialize storage: {str(storage_error)}")
                
                # Create agent instance
                if 'ComputerAgent' in globals():
                    print("Creating ComputerAgent instance...")
                    try:
                        cua_agent = ComputerAgent(
                            agent_id=agent_id,
                            storage=storage or None
                        )
                        cua_agents[agent_id] = {
                            "agent": cua_agent,
                            "storage": storage
                        }
                        print(f"✅ Successfully initialized CUA agent: {agent_id}")
                    except Exception as agent_error:
                        print(f"❌ Failed to create ComputerAgent: {str(agent_error)}")
                        raise
                else:
                    print("⚠️  ComputerAgent class not found in globals()")
                    print("Available globals:", ", ".join([g for g in globals() if not g.startswith('__')]))
                    
            except Exception as agent_error:
                print(f"❌ Error initializing agent {agent_id}: {str(agent_error)}")
                print("Traceback:", traceback.format_exc())
                continue
        
        print("\n=== Agent Initialization Summary ===")
        if cua_agents:
            print(f"✅ Successfully initialized {len(cua_agents)}/{len(AGENTS)} CUA agents")
            print("Agent IDs:", ", ".join(cua_agents.keys()))
        else:
            print("❌ No CUA agents were initialized successfully")
            CUA_AVAILABLE = False
            
    except Exception as e:
        print(f"\n❌ Critical error during CUA agent initialization: {str(e)}")
        print("Traceback:", traceback.format_exc())
        CUA_AVAILABLE = False
        
    # Print debug information
    print("\n=== Debug Information ===")
    print(f"CUA_AVAILABLE: {CUA_AVAILABLE}")
    print(f"AGENTS: {AGENTS}")
    print(f"cua_agents: {list(cua_agents.keys())}")
    print("sys.path:", sys.path)
    
    # Check if required modules are importable
    try:
        import storage_integration
        print("✅ storage_integration is importable")
    except ImportError as e:
        print(f"❌ Error importing storage_integration: {str(e)}")
        
    try:
        from main import ComputerAgent
        print("✅ ComputerAgent is importable")
    except ImportError as e:
        print(f"❌ Error importing ComputerAgent: {str(e)}")
        
    print("======================\n")
    
else:
    print("⚠️  CUA components not available, falling back to simple task processing")

# Add project root so we can import run_task.py
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import run_task
    RUN_TASK_AVAILABLE = True
    print("✅ run_task module available")
except Exception as e:
    RUN_TASK_AVAILABLE = False
    print(f"⚠️ run_task import failed: {e}")

async def run_task_script(task_text: str, agent_id: str):
    """Run the task using the run_task.py script"""
    try:
        # Import the run_task module
        import sys
        from pathlib import Path
        import asyncio
        
        # Add the project root to the Python path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # Import the run_task module
        import run_task
        
        # Write the task to the shared tasks file
        run_task.write_task_to_file(task_text)
        
        # Start the agent if not already running
        run_task.start_agent(agent_id)
        
        # Return a simple response since we're running asynchronously
        return {
            "status": "started",
            "message": f"Task submitted to {agent_id}",
            "execution_time": 0
        }
        
    except Exception as e:
        print(f"Error running task: {str(e)}")
        print("Traceback:", traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "execution_time": 0
        }

async def run_task_and_wait_for_response(task_text: str, agent_id: str, timeout: int = 30):
    """
    Use run_task utilities to write the task and optionally start agent,
    then poll for a matching agent response. Returns the agent text or raises.
    """
    if not RUN_TASK_AVAILABLE:
        raise RuntimeError("run_task module not available")

    # write task for agents to pick up
    try:
        run_task.write_task_to_file(task_text)
    except Exception as e:
        raise RuntimeError(f"failed to write task file: {e}")

    # ensure agent process started (best-effort; in containerized setups agents may be separate)
    try:
        run_task.start_agent(agent_id)
    except Exception:
        # non-fatal: start_agent is best-effort
        pass

    # initial snapshot timestamps for this agent
    snapshot = run_task.get_agent_responses()
    initial_ts = 0
    agent_list = snapshot.get(agent_id, [])
    if agent_list:
        initial_ts = max(r.get("timestamp", 0) for r in agent_list)

    # poll until we see a newer response
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            responses = run_task.get_agent_responses()
            agent_resps = responses.get(agent_id, [])
            # find the first response newer than initial_ts
            for r in agent_resps:
                ts = r.get("timestamp", 0)
                text = r.get("text", "")
                if ts and ts > initial_ts and text:
                    return {"text": text, "file": r.get("file"), "timestamp": ts}
        except Exception:
            pass
        await asyncio.sleep(1)
    raise TimeoutError("no agent response within timeout")

async def process_task_with_cua(task_id: int, task_text: str, agent_id: str):
    """Process a task using run_task.py routing and store the real agent response."""
    print(f"\n=== Processing task {task_id} with agent {agent_id} ===")
    try:
        # mark in_progress
        pg.update_task_status(
            task_id=task_id,
            status="in_progress",
            metadata={"started_at": datetime.utcnow().isoformat()}
        )

        # Use run_task to submit and wait for the agent response
        try:
            resp = await run_task_and_wait_for_response(task_text, agent_id, timeout=30)
        except TimeoutError as te:
            pg.update_task_status(
                task_id=task_id,
                status="failed",
                metadata={"error": "agent timeout", "failed_at": datetime.utcnow().isoformat()}
            )
            pg.add_progress_update(
                task_id=task_id,
                agent_id=agent_id,
                progress_percent=100,
                message=f"Task failed: no response from {agent_id} within timeout",
                data={"error": str(te)}
            )
            print(f"Task {task_id} timed out waiting for agent response")
            return

        # Persist the actual agent response as result and mark completed
        result_payload = {
            "status": "ok",
            "response_text": resp.get("text"),
            "file": resp.get("file"),
            "timestamp": datetime.utcfromtimestamp(resp.get("timestamp")).isoformat() if resp.get("timestamp") else datetime.utcnow().isoformat()
        }

        pg.update_task_status(
            task_id=task_id,
            status="completed",
            metadata={
                "completed_at": datetime.utcnow().isoformat(),
                "result": result_payload,
                "agent_used": agent_id,
                "processing_method": "run_task_routing"
            }
        )

        # Add a final progress update with the response
        pg.add_progress_update(
            task_id=task_id,
            agent_id=agent_id,
            progress_percent=100,
            message=f"Agent response: {result_payload['response_text']}",
            data=result_payload
        )

        print(f"Task {task_id} completed; stored agent response")
        return

    except Exception as e:
        print(f"❌ Task processing failed for task {task_id}: {e}")
        pg.update_task_status(
            task_id=task_id,
            status="failed",
            metadata={"error": str(e), "failed_at": datetime.utcnow().isoformat()}
        )
        pg.add_progress_update(
            task_id=task_id,
            agent_id=agent_id,
            progress_percent=100,
            message=f"Task failed: {str(e)}",
            data={"error": str(e)}
        )
        return

@app.post("/task")
async def create_task(request: Request, background_tasks: BackgroundTasks):
    """Create a new task and assign to agents"""
    try:
        # Log raw request body
        body_bytes = await request.body()
        print(f"Raw request body: {body_bytes}")
        
        # Try to parse JSON
        try:
            data = await request.json()
            print(f"Parsed JSON data: {data}")  # Debug log
        except json.JSONDecodeError as je:
            print(f"Failed to parse JSON: {je}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(je)}")
        
        if not data or not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Invalid request body")
            
        task_text = data.get("text", "") or data.get("task", "")
        
        if not task_text:
            print(f"No task text found in data: {data}")  # Debug log
            raise HTTPException(status_code=400, detail="Task text is required")
        
        # Create task in PostgreSQL
        task_id = pg.create_task(
            agent_id="frontend",
            title=f"Task: {task_text[:50]}...",
            description=task_text,
            status="pending",
            metadata={"type": "user_task"}
        )
        
        # Assign task to an agent (round-robin)
        agent = AGENTS[task_id % len(AGENTS)]
        agent_id = agent["id"]
        
        # Update task with assigned agent
        pg.update_task_status(
            task_id=task_id,
            status="assigned",
            metadata={"assigned_agent_id": agent_id}
        )
        
        # Don't process the task here - let agent_worker pick it up from PostgreSQL
        # The agent_worker polls PostgreSQL for pending tasks and executes them
        # No background task needed - agent_worker will handle it
        
        # Log to MongoDB if available
        if server_db is not None:
            try:
                server_db.messages.insert_one({
                    "task_id": task_id,
                    "message": f"Created task: {task_text}",
                    "timestamp": datetime.utcnow(),
                    "level": "info"
                })
            except Exception as e:
                print(f"Warning: Failed to log to MongoDB: {str(e)}")
            
        # Return immediately; frontend will receive actual results via the tasks polling endpoint
        return {"task_id": task_id, "status": "created"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/tasks")
async def get_tasks(agent_id: str = None, status: str = None, limit: int = 10):
    """Get tasks with optional filtering"""
    tasks = pg.get_tasks(agent_id=agent_id, status=status, limit=limit)
    return {"tasks": tasks}


@app.get("/agents/live")
async def get_agents_live(limit_per_agent: int = 3):
    """Return aggregated live data for each agent."""

    if limit_per_agent < 1:
        limit_per_agent = 1

    agents = {}

    for agent_id in AGENT_URLS.keys():
        agents[agent_id] = {
            "agent_id": agent_id,
            "screenshots": [],
            "latest_progress": None,
            "progress_updates": []
        }

    # Gather recent screenshot metadata
    screenshot_limit = limit_per_agent * max(len(agents), 1) * 2
    metadata_records = pg.get_binary_files(bucket="screenshots", limit=screenshot_limit)
    metadata_by_path = {record.get("object_path"): record for record in metadata_records}

    screenshot_objects = []
    if MINIO_AVAILABLE and minio_adapter:
        try:
            screenshot_objects = minio_adapter.list_objects(
                "screenshots",
                limit=screenshot_limit * 2 or 50
            )
        except Exception as e:
            print(f"⚠️  Warning: Failed to list screenshots from MinIO: {e}")
    else:
        print("ℹ️  MinIO not available, falling back to metadata cache only")

    if screenshot_objects:
        from datetime import datetime as _dt

        def _sort_key(obj):
            last_modified = obj.get("last_modified")
            if isinstance(last_modified, _dt):
                return last_modified
            return _dt.min

        for obj in sorted(screenshot_objects, key=_sort_key, reverse=True):
            object_path = obj.get("object_name")
            if not object_path:
                continue

            agent_id = object_path.split("/", 1)[0] if "/" in object_path else object_path.split("-", 1)[0]
            agent_id = agent_id or "unknown"

            agent_entry = agents.setdefault(
                agent_id,
                {
                    "agent_id": agent_id,
                    "screenshots": [],
                    "latest_progress": None,
                    "progress_updates": []
                }
            )

            if len(agent_entry["screenshots"]) >= limit_per_agent:
                continue

            metadata = metadata_by_path.get(object_path, {})

            presigned_url = None
            try:
                presigned_url = minio_adapter.get_presigned_url(
                    "screenshots",
                    object_path,
                    expires_seconds=300
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to generate presigned URL for {object_path}: {e}")

            uploaded_at = metadata.get("uploaded_at")
            if not uploaded_at:
                uploaded_at = obj.get("last_modified")

            agent_entry["screenshots"].append({
                "object_path": object_path,
                "url": presigned_url,
                "task_id": metadata.get("task_id"),
                "uploaded_at": _serialize_datetime(uploaded_at),
                "metadata": metadata.get("metadata") or {},
                "size_bytes": obj.get("size")
            })
    else:
        for record in metadata_records:
            agent_id = record.get("agent_id") or "unknown"
            agent_entry = agents.setdefault(
                agent_id,
                {
                    "agent_id": agent_id,
                    "screenshots": [],
                    "latest_progress": None,
                    "progress_updates": []
                }
            )

            if len(agent_entry["screenshots"]) >= limit_per_agent:
                continue

            agent_entry["screenshots"].append({
                "object_path": record.get("object_path"),
                "url": None,
                "task_id": record.get("task_id"),
                "uploaded_at": _serialize_datetime(record.get("uploaded_at")),
                "metadata": record.get("metadata") or {}
            })

    # Gather recent progress updates
    progress_limit = limit_per_agent * max(len(agents), 1) * 4
    progress_records = pg.get_recent_progress(limit=progress_limit)

    for update in progress_records:
        agent_id = update.get("agent_id") or "unknown"
        agent_entry = agents.setdefault(
            agent_id,
            {
                "agent_id": agent_id,
                "screenshots": [],
                "latest_progress": None,
                "progress_updates": []
            }
        )

        progress_payload = {
            "task_id": update.get("task_id"),
            "message": update.get("message"),
            "progress_percent": update.get("progress_percent"),
            "timestamp": _serialize_datetime(update.get("timestamp")),
            "data": update.get("data") or {}
        }

        if not agent_entry["latest_progress"]:
            agent_entry["latest_progress"] = progress_payload

        if len(agent_entry["progress_updates"]) < limit_per_agent:
            agent_entry["progress_updates"].append(progress_payload)

    # Sort agents alphabetically for deterministic responses
    agent_list = sorted(agents.values(), key=lambda item: item["agent_id"])

    return {
        "agents": agent_list,
        "generated_at": datetime.utcnow().isoformat(),
        "minio_available": MINIO_AVAILABLE
    }


@app.get("/chat/agent-responses")
async def get_agent_responses(limit: int = 50):
    """Expose recent agent responses captured via progress updates."""

    if limit < 1:
        limit = 1
    limit = min(limit, 200)

    records = pg.get_recent_agent_messages(limit=limit)
    messages = []

    for record in records:
        messages.append({
            "id": record.get("id"),
            "agent_id": record.get("agent_id"),
            "task_id": record.get("task_id"),
            "message": record.get("message"),
            "progress_percent": record.get("progress_percent"),
            "data": record.get("data") or {},
            "timestamp": _serialize_datetime(record.get("timestamp")),
            "task": record.get("task"),
        })

    return {
        "messages": messages,
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/task/{task_id}")
async def get_task(task_id: int):
    """Get task details with progress"""
    task = pg.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    progress = pg.get_task_progress(task_id)
    task["progress"] = progress
    return task

@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent logs from MongoDB"""
    if not server_db:
        return {"logs": [], "warning": "MongoDB not available"}
        
    logs = list(server_db.messages.find()
               .sort("timestamp", -1)
               .limit(limit))
    
    # Convert ObjectId to string and format datetime
    for log in logs:
        log["_id"] = str(log["_id"])
        log["timestamp"] = log["timestamp"].isoformat()
        
    return {"logs": logs}

async def run_task(task_id: int) -> Any:
    """
    Route the task to its configured CUA agent, store the agent response in DB,
    and return the response.
    """
    row = await _fetch_task(task_id)
    task_status = row["status"]
    if task_status == "completed":
        # return stored result if already completed
        if not _db_pool:
            raise HTTPException(status_code=500, detail="database not configured")
        stored = await _db_pool.fetchrow("SELECT result FROM tasks WHERE id=$1", task_id)
        return stored["result"] if stored else None

    # mark processing
    await _update_task_status(task_id, "processing")

    agent_url = row.get("agent_url")
    if not agent_url:
        await _update_task_status(task_id, "failed", {"error": "missing agent_url"})
        raise HTTPException(status_code=400, detail="task missing agent_url")

    # Format the task payload for the agent - this was missing!
    task_text = row.get("description", "")
    payload = {
        "type": "shell" if row.get("payload", {}).get("type") == "shell" else "execute",
        "input_text": task_text,  # This is key - send the actual task text
        "task_type": "general"
    }

    # POST to CUA agent and capture response
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(agent_url, json=payload)
            try:
                resp_data = resp.json()
                # Extract the actual agent response text - this was missing!
                agent_response = None
                if isinstance(resp_data, dict):
                    # Try different response formats
                    if "response" in resp_data:
                        agent_response = resp_data["response"].get("text") or resp_data["response"]
                    elif "output" in resp_data:
                        output = resp_data["output"]
                        if isinstance(output, list):
                            # Look for message type outputs
                            for item in output:
                                if item.get("type") == "message" and item.get("content"):
                                    for content in item["content"]:
                                        if content.get("text"):
                                            agent_response = content["text"]
                                            break
                                    if agent_response:
                                        break
                
                # Use extracted response or fallback to raw response
                result_payload = {
                    "status": "ok",
                    "response": agent_response or str(resp_data),
                    "raw_response": resp_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                result_payload = {
                    "status": "error",
                    "error": f"Failed to parse agent response: {str(e)}",
                    "raw_response": resp.text,
                    "timestamp": datetime.utcnow().isoformat()
                }
    except Exception as e:
        err = {"error": str(e)}
        await _update_task_status(task_id, "failed", err)
        raise HTTPException(status_code=502, detail=err)

    # store final response and mark completed
    await _update_task_status(task_id, "completed", result_payload)
    return result_payload

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
