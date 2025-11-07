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
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
from typing import Optional
import sys
from minio import Minio
from minio.error import S3Error

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage import PostgresAdapter

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

# Initialize MinIO client
minio_client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)
BUCKET_NAME = "screenshots"

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

# Run task API URL (the canonical source for agent responses)
RUN_TASK_API = os.getenv("RUN_TASK_API", "http://localhost:8001")

@app.post("/message")
async def send_message(request: Request):
    """Send message to all agents and store in databases"""
    data = await request.json()
    message = data.get("message", "")
    
    if not message:
        return {"error": "No message provided"}
    
    # Store in server database
    if server_db:
        server_db.messages.insert_one({
            "message": message,
            "timestamp": datetime.now(),
            "source": "server"
        })
    
    # Send to all agents
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            client.post(url, json={
                "input_text": message,
                "task_type": "general"
            })
            for url in AGENT_URLS.values()
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    results = {}
    for name, response in zip(AGENT_URLS.keys(), responses):
        if isinstance(response, Exception):
            results[name] = {"error": str(response)}
        else:
            results[name] = response.json()
    
    return {
        "message": message,
        "server_stored": True,
        "agent_responses": results
    }

@app.get("/messages")
async def get_messages():
    """Get all messages from server database"""
    if not server_db:
        return {"messages": []}
    messages = list(server_db.messages.find().sort("timestamp", -1).limit(10))
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        msg["timestamp"] = msg["timestamp"].isoformat()
    return {"messages": messages}

@app.get("/agent-responses")
async def get_agent_responses():
    """Proxy to run_task.py API for agent responses.
    
    This endpoint proxies to the canonical source (run_task.py on port 8001)
    which reads directly from trajectory folders.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RUN_TASK_API}/agent-responses")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        print(f"Error proxying to run_task API: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach run_task API at {RUN_TASK_API}. Make sure run_task.py is running with --api flag."
        )
    except httpx.HTTPStatusError as e:
        print(f"HTTP error from run_task API: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

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

@app.get("/agent-screenshot/{agent_id}")
async def get_agent_screenshot(agent_id: str):
    """
    Get the latest screenshot for an agent.
    
    First tries to proxy to run_task.py (filesystem), then falls back to MinIO if configured.
    """
    # First, try to get from run_task.py (filesystem)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{RUN_TASK_API}/agent-screenshot/{agent_id}",
                follow_redirects=True
            )
            if response.status_code == 200:
                # Stream the response back
                return StreamingResponse(
                    response.iter_bytes(),
                    media_type="image/png",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"run_task API unavailable or screenshot not found: {e}")
        # Fall through to MinIO fallback
    
    # Fallback: Try MinIO (if configured)
    response = None
    try:
        # Try different possible paths in MinIO
        possible_paths = [
            f"{agent_id}/screenshots/latest.png",  # agent1-cua/screenshots/latest.png
            f"{agent_id}/latest.png",              # agent1-cua/latest.png
            f"screenshots/{agent_id}/latest.png"    # screenshots/agent1-cua/latest.png
        ]
        
        for object_path in possible_paths:
            try:
                # Get the object from MinIO
                response = minio_client.get_object(BUCKET_NAME, object_path)
                
                # If we get here, the object was found
                return StreamingResponse(
                    response,
                    media_type="image/png",
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
                
            except S3Error as e:
                if e.code == "NoSuchKey":
                    print(f"MinIO path not found: {object_path}")
                    continue
                print(f"MinIO error: {e}")
                raise
                
        # If we get here, none of the paths worked
        print(f"Screenshot not found for {agent_id} in MinIO. Tried paths: {possible_paths}")
        raise HTTPException(
            status_code=404,
            detail=f"Screenshot not found for {agent_id}. Checked filesystem (via run_task API) and MinIO."
        )
        
    except Exception as e:
        print(f"Error getting screenshot: {e}")
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail="Failed to get screenshot")
        raise
        
    finally:
        if response:
            response.close()
            response.release_conn()

@app.get("/tasks")
async def get_tasks(agent_id: str = None, status: str = None, limit: int = 10):
    """Get tasks with optional filtering"""
    tasks = pg.get_tasks(agent_id=agent_id, status=status, limit=limit)
    return {"tasks": tasks}

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
