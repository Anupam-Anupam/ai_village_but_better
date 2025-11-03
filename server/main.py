"""
Simple AI Village Server
========================
Accepts terminal input and sends messages to all agents.
Stores messages in server database and each agent's database.
"""

import asyncio
import httpx
import json
from fastapi import FastAPI, Request
from pymongo import MongoClient
from datetime import datetime
import os
from .middleware.request_logger import log_requests
from .db import init_db

app = FastAPI()

# Initialize database tables
init_db()

# Add request logging middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    async with log_requests(request, call_next) as response:
        return response

# MongoDB connection for server database
mongo_client = MongoClient(os.getenv("MONGODB_URL", "mongodb://admin:password@mongodb:27017/serverdb?authSource=admin"))
server_db = mongo_client.serverdb

# Agent URLs
AGENT_URLS = {
    "agent1": "http://172.19.0.4:8001/execute",
    "agent2": "http://172.19.0.5:8001/execute", 
    "agent3": "http://172.19.0.3:8001/execute"
}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
