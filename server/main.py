"""
Simple AI Village Server
========================
Accepts terminal input and sends messages to all agents.
Stores messages in server database and each agent's database.
"""

import asyncio
import httpx
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from minio import Minio
from minio.error import S3Error
import io
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
from typing import Optional

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MinIO client
minio_client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)
BUCKET_NAME = "screenshots"

# MongoDB connection for server database
# MongoDB connection parameters
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
MONGODB_USER = "admin"
MONGODB_PASS = "password"
MONGODB_DB = "serverdb"

MONGODB_URL = f"mongodb://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DB}?authSource=admin"

print(f"🔌 Attempting to connect to MongoDB at {MONGODB_HOST}:{MONGODB_PORT}")

# Initialize MongoDB client and database
mongo_client = None
server_db = None

try:
    mongo_client = MongoClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Test the connection
    mongo_client.server_info()
    print(f"✅ Successfully connected to MongoDB at {MONGODB_HOST}:{MONGODB_PORT}")
    
    # Get or create the database
    server_db = mongo_client[MONGODB_DB]
    
    # Create collections if they don't exist
    required_collections = ['messages', 'tasks', 'agent_responses']
    existing_collections = server_db.list_collection_names()
    
    for collection in required_collections:
        if collection not in existing_collections:
            server_db.create_collection(collection)
            print(f"✅ Created collection: {collection}")
    
    print("✅ Database initialization complete")
    
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print(f"Make sure MongoDB service is running and accessible at {MONGODB_HOST}:{MONGODB_PORT}")
    print(f"Connection URL: {MONGODB_URL}")
    server_db = None

# Agent URLs - using container names for Docker networking
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
    """Create a new task and send to all agents"""
    try:
        data = await request.json()
        task_text = data.get("task", "")
        
        if not task_text:
            return JSONResponse(
                status_code=400,
                content={"detail": "Task text is required"}
            )
        
        # Store task in database
        task = {
            "task": task_text,
            "timestamp": datetime.now(),
            "status": "pending"
        }
        
        print(f"New task received: {task_text}")
        
        # Store in database
        result = server_db.tasks.insert_one(task)
        task["_id"] = str(result.inserted_id)
        
        # Forward task to all agents asynchronously
        async def send_to_agent(agent_name, url):
            try:
                # Format the task as a shell command to echo the task text
                command = f"echo 'Task received: {task_text}'"
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json={
                            "type": "shell",
                            "command": command
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # Store the agent's response in the database
                    try:
                        if mongo_client is not None:  # Check if MongoDB client is initialized
                            response_doc = {
                                "agent": agent_name,
                                "task_id": str(result.inserted_id),
                                "task": task_text,
                                "response": response_data,
                                "timestamp": datetime.now()
                            }
                            server_db.agent_responses.insert_one(response_doc)
                    except Exception as db_error:
                        print(f"Error storing response in database: {db_error}")
                    
                    return {"agent": agent_name, "status": "success", "response": response_data}
            except Exception as e:
                error_msg = f"Error sending to {agent_name} at {url}: {e}"
                print(error_msg)
                
                # Store the error in the database
                try:
                    if mongo_client is not None:  # Check if MongoDB client is initialized
                        error_doc = {
                            "agent": agent_name,
                            "task_id": str(result.inserted_id) if 'result' in locals() else None,
                            "task": task_text,
                            "error": str(e),
                            "timestamp": datetime.now()
                        }
                        server_db.agent_responses.insert_one(error_doc)
                except Exception as db_error:
                    print(f"Error storing error in database: {db_error}")
                
                return {"agent": agent_name, "status": "error", "error": str(e)}
        
        # Send to all agents in parallel
        tasks = [send_to_agent(name, url) for name, url in AGENT_URLS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update task status
        server_db.tasks.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "sent_to_agents"}}
        )
        
        return {
            "message": "Task received and sent to all agents",
            "task_id": str(result.inserted_id),
            "agent_responses": results
        }
        
    except Exception as e:
        print(f"Error processing task: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error processing task: {str(e)}"}
        )

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
