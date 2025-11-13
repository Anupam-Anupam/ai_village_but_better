"""
AI Village Server
=================
Manages tasks and agent communication.
Uses PostgreSQL for task management and MongoDB for logs.
"""

import os
import sys
import json
import httpx
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List, Union
from pymongo import MongoClient

# Add project root to path so we can import storage and CUA
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / 'CUA'))

# Import storage adapters
from storage.postgres_adapter import PostgresAdapter
from storage.mongo_adapter import MongoAdapter
from storage.minio_adapter import MinIOAdapter

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
# Use localhost:5433 for local development, postgres:5432 for Docker
postgres_url = os.getenv(
    "POSTGRES_URL",
    "postgresql://hub:hubpassword@localhost:5433/hub"  # Default to localhost for local dev
)
pg = PostgresAdapter(connection_string=postgres_url)

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
    # Use localhost for local dev, mongodb for Docker
    mongo_uri = os.getenv(
        "MONGODB_URL",
        "mongodb://admin:password@localhost:27017/serverdb?authSource=admin"
    )
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Force a connection test
    server_db = mongo_client.serverdb
    print("✅ Successfully connected to MongoDB")
    print(f"Connection URL: {mongo_uri}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print("Make sure MongoDB service is running and accessible")
    server_db = None

# Agent configurations
AGENTS = [
    {"id": "agent1-cua", "url": "http://host.docker.internal:8001/execute"},
    {"id": "agent2-cua", "url": "http://host.docker.internal:8002/execute"},
    {"id": "agent3-cua", "url": "http://host.docker.internal:8003/execute"}
]
AGENT_IDS = [agent["id"] for agent in AGENTS]

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
                # Note: ComputerAgent requires 'model' and 'tools' parameters
                # We skip initialization here since agents run independently via agent_worker
                # This initialization is optional and mainly for testing
                if 'ComputerAgent' in globals():
                    print("⚠️  ComputerAgent initialization skipped - agents run via agent_worker")
                    print("    ComputerAgent requires 'model' and 'tools' parameters")
                    # Don't initialize here - agents are managed by agent_worker processes
                    continue
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


def _serialize_datetime(dt):
    """Serialize datetime object to ISO format string, handling None."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


@app.get("/agents/live")
async def get_agents_live(limit_per_agent: int = 3):
    """Return aggregated live data for each agent."""

    if limit_per_agent < 1:
        limit_per_agent = 1

    agents = {}

    for agent_id in AGENT_IDS:
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
    
    # Track which (task_id, agent_id) combinations we've already included to avoid duplicates
    seen_combinations = set()

    for record in records:
        task = record.get("task")
        task_id = record.get("task_id")
        agent_id = record.get("agent_id")
        
        # Create a unique key for this task-agent combination
        combination_key = (task_id, agent_id)
        
        # Skip if we've already included this combination (prefer responses over progress messages)
        if combination_key in seen_combinations:
            continue
        
        # Extract the actual agent response from task metadata if available
        agent_response = None
        if task and task.get("metadata"):
            agent_response = task.get("metadata", {}).get("response")
        
        # Use the agent response if available, otherwise use the progress message
        message_text = agent_response if agent_response else record.get("message")
        
        # Only include messages that have actual content (skip empty progress updates for completed tasks)
        # Show progress messages for in-progress tasks, but prefer responses for completed tasks
        if message_text and (agent_response or not task or task.get("status") != "completed"):
            messages.append({
                "id": record.get("id"),
                "agent_id": agent_id,
                "task_id": task_id,
                "message": message_text,
                "progress_percent": record.get("progress_percent"),
                "data": record.get("data") or {},
                "timestamp": _serialize_datetime(record.get("timestamp")),
                "task": task,
            })
            seen_combinations.add(combination_key)

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
