"""
AI Village Server
=================
Manages tasks and agent communication.
Uses PostgreSQL for task management and MongoDB for logs.
"""

import asyncio
import json
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage import PostgresAdapter
from storage.minio_adapter import MinIOAdapter

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
    # Use the service name from docker-compose
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

# Agent URLs - using Docker service names
AGENT_URLS = {
    "agent1": "http://agent1:8001/execute",
    "agent2": "http://agent2:8001/execute",
    "agent3": "http://agent3:8001/execute"
}


def _serialize_datetime(value):
    if not value:
        return None
    try:
        return value.isoformat()
    except AttributeError:
        return value

@app.post("/task")
async def create_task(request: Request):
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
            
        # Notify agents
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                client.post(url, json={
                    "task_id": task_id,
                    "input_text": task_text,
                    "task_type": "user_task"
                })
                for url in AGENT_URLS.values()
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"task_id": task_id, "status": "created"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return {"task_id": task_id, "status": "created"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
