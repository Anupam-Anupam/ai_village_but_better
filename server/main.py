"""
Simple AI Village Server
========================
Accepts terminal input and sends messages to all agents.
Stores messages in server database and each agent's database.
"""

import asyncio
import httpx
import json
import base64
from io import BytesIO
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
from minio import Minio
from minio.error import S3Error
from urllib.parse import urlparse

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_NAME = "screenshots"

# Initialize MinIO client
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    
    # Create bucket if it doesn't exist
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        print(f"✅ Created MinIO bucket: {BUCKET_NAME}")
    
    print(f"✅ Connected to MinIO at {MINIO_ENDPOINT}")
except Exception as e:
    print(f"❌ Failed to connect to MinIO: {e}")
    minio_client = None

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

async def send_to_agent(agent_name, url, task_data, task_text, task_id):
    """Send task to a single agent and handle the response"""
    try:
        # Format the task data for the agent's API
        agent_request = {
            "type": task_data.get("type", "browse"),
            "command": task_data.get("command", "https://www.example.com"),
            "task": task_data.get("task", ""),
            "task_id": task_data.get("task_id", ""),
            "timestamp": task_data.get("timestamp", datetime.now().isoformat())
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=agent_request, timeout=30.0)
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Response from {agent_name}: {response_data}")
                
                # Check if the response includes a screenshot
                if isinstance(response_data, dict) and 'screenshot' in response_data:
                    # Save the screenshot to MinIO
                    screenshot_url = save_screenshot(
                        agent_name,
                        response_data['screenshot'],
                        task_id
                    )
                    if screenshot_url:
                        print(f"Saved screenshot from {agent_name} to {screenshot_url}")
                        # Add the screenshot URL to the response
                        if isinstance(response_data, dict):
                            response_data['screenshot_url'] = screenshot_url
                
                # Store the agent's response in the database
                if mongo_client is not None:
                    response_doc = {
                        "agent": agent_name,
                        "task_id": task_id,
                        "task": task_text,
                        "response": response_data,
                        "timestamp": datetime.now()
                    }
                    server_db.agent_responses.insert_one(response_doc)
                
                return {"agent": agent_name, "status": "success", "response": response_data}
            else:
                error_msg = f"Error from {agent_name} at {url}: {response.status_code} - {response.text}"
                print(error_msg)
                
                # Store the error in the database
                if mongo_client is not None:
                    error_doc = {
                        "agent": agent_name,
                        "task_id": task_id,
                        "task": task_text,
                        "error": error_msg,
                        "timestamp": datetime.now()
                    }
                    server_db.agent_responses.insert_one(error_doc)
                
                return {"agent": agent_name, "status": "error", "error": error_msg}
                
    except Exception as e:
        error_msg = f"Error sending to {agent_name} at {url}: {e}"
        print(error_msg)
        
        # Store the error in the database
        if mongo_client is not None:
            error_doc = {
                "agent": agent_name,
                "task_id": task_id,
                "task": task_text,
                "error": str(e),
                "timestamp": datetime.now()
            }
            server_db.agent_responses.insert_one(error_doc)
        
        return {"agent": agent_name, "status": "error", "error": str(e)}

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
    """Get all agent responses from the database"""
    responses = {}
    # Get messages from each agent's database
    for agent_name in AGENT_URLS.keys():
        try:
            agent_db = mongo_client[f"{agent_name}db"]
            agent_responses = list(agent_db.responses.find().sort("timestamp", -1).limit(10))
            
            # Convert ObjectId to string and format timestamps
            formatted_responses = []
            for resp in agent_responses:
                resp["_id"] = str(resp["_id"])
                resp["timestamp"] = resp.get("timestamp", datetime.now()).timestamp()
                formatted_responses.append({
                    "text": resp.get("response", "No response"),
                    "file": resp.get("file", "unknown"),
                    "timestamp": resp["timestamp"]
                })
            
            responses[agent_name] = formatted_responses
        except Exception as e:
            print(f"Error getting responses for {agent_name}: {e}")
            responses[agent_name] = []
    
    return {"responses": responses}

def save_screenshot(agent_name: str, image_data: str, task_id: str = None):
    """Save screenshot to MinIO"""
    if not minio_client:
        print("⚠️ MinIO client not available, cannot save screenshot")
        return None
    
    try:
        # Extract image data (handle both base64 and raw bytes)
        if ',' in image_data:
            # Handle data URL format: data:image/png;base64,...
            header, encoded = image_data.split(',', 1)
            image_bytes = base64.b64decode(encoded)
        else:
            # Assume raw base64
            image_bytes = base64.b64decode(image_data)
        
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent_name}/screenshot_{timestamp}.png"
        
        # Upload to MinIO
        image_stream = BytesIO(image_bytes)
        minio_client.put_object(
            BUCKET_NAME,
            filename,
            image_stream,
            length=len(image_bytes),
            content_type='image/png'
        )
        
        # Generate public URL (or presigned URL if needed)
        url = f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{filename}"
        
        # Store reference in MongoDB if we have a task_id
        if mongo_client and task_id:
            server_db.screenshots.insert_one({
                "agent": agent_name,
                "task_id": task_id,
                "filename": filename,
                "url": url,
                "timestamp": datetime.now()
            })
        
        return url
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return None

@app.get("/screenshots/list")
async def list_screenshots():
    """List all available screenshots with public URLs"""
    if not minio_client:
        raise HTTPException(status_code=500, detail="MinIO client not available")
    
    try:
        screenshots = {}
        for agent in ["agent1", "agent2", "agent3"]:
            try:
                # List objects for this agent
                objects = list(minio_client.list_objects(BUCKET_NAME, prefix=f"{agent}/screenshots/", recursive=True))
                if objects:
                    # Get the most recent screenshot for this agent
                    latest = max(objects, key=lambda o: o.last_modified)
                    
                    # Generate a presigned URL for the screenshot
                    # The frontend will access this URL directly
                    screenshot_url = f"http://localhost:9000/{BUCKET_NAME}/{latest.object_name}"
                    
                    screenshots[agent] = {
                        "url": screenshot_url,
                        "lastModified": latest.last_modified.isoformat()
                    }
                    
            except Exception as e:
                print(f"Error listing screenshots for {agent}: {e}")
        
        return screenshots
    except Exception as e:
        print(f"Error listing screenshots: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing screenshots: {str(e)}")

@app.post("/task")
async def create_task(request: Request):
    """Create a new task and send to all agents"""
    try:
        data = await request.json()
        task_text = data.get("task", "")
        
        if not task_text:
            return {"error": "No task provided"}
            
        # Store task in database
        task_doc = {
            "task": task_text,
            "timestamp": datetime.now(),
            "status": "pending"
        }
        
        if mongo_client is not None:  # Check if MongoDB client is initialized
            result = server_db.tasks.insert_one(task_doc)
            task_id = str(result.inserted_id)
        else:
            print("⚠️ MongoDB client not initialized, running in limited mode")
            task_id = "no-db-connection"
        
        # Prepare task data for agents
        task_data = {
            "type": "browse",  # Using 'browse' as it's one of the allowed types
            "command": "https://www.example.com",  # URL to browse (uses 'command' field for URL in browse type)
            "task": task_text,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send a simple test request to agent1 to debug the API
        test_url = "http://agent1:8001/execute"
        test_data = {
            "type": "browse",
            "command": "https://www.example.com"
        }
        
        print(f"Sending test request to {test_url} with data: {test_data}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(test_url, json=test_data, timeout=30.0)
                print(f"Response from agent1: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error sending test request: {e}")
        
        # Send task to all agents asynchronously
        async with httpx.AsyncClient() as client:
            tasks = []
            for agent_name, url in AGENT_URLS.items():
                try:
                    # Add agent-specific data
                    agent_task = task_data.copy()
                    agent_task["agent"] = agent_name
                    
                    # Send the task
                    task = asyncio.create_task(
                        send_to_agent(agent_name, url, agent_task, task_text, task_id)
                    )
                    tasks.append(task)
                    
                except Exception as e:
                    print(f"Error creating task for {agent_name}: {e}")
            
            # Wait for all tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update task status to completed
        if mongo_client is not None and 'result' in locals():
            server_db.tasks.update_one(
                {"_id": result.inserted_id},
                {"$set": {"status": "completed"}}
            )
        
        return {
            "status": "Task sent to all agents", 
            "task_id": task_id
        }
        
    except json.JSONDecodeError:
        return {"error": "Invalid JSON data"}
    except Exception as e:
        print(f"Error in create_task: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
