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
