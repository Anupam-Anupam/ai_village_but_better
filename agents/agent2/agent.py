"""
Agent 2 - Claude AI Agent with Embedded MongoDB Database
=======================================================

This agent runs in its own Docker container with:
- Embedded MongoDB database (agent2db)
- FastAPI web server for task processing
- Claude AI integration (using OpenAI API for now)
- Memory management and task tracking
- Complete isolation from other agents

Database: Each agent has its own MongoDB instance
- Agent 1: mongodb://localhost:27017/agent1db
- Agent 2: mongodb://localhost:27017/agent2db  
- Agent 3: mongodb://localhost:27017/agent3db

API Endpoints:
- POST /execute: Process tasks with Claude AI
- GET /tasks: Get agent's tasks
- GET /memory: Get agent's memory
- GET /config: Get agent configuration
- GET /logs: Get agent logs
"""

import os
import sys
from fastapi import FastAPI, Request, HTTPException
from openai import OpenAI
from dotenv import load_dotenv

# Add shared directory to path for database models
sys.path.append('/app/shared')

from shared.models import AgentDatabase

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# Get OpenAI API key from environment
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Please set it in your .env file or as an environment variable.")

# Initialize OpenAI client (using Claude via OpenAI API)
client = OpenAI(api_key=API_KEY)

# Initialize FastAPI application
app = FastAPI()

# Initialize database connection
# This connects to this agent's own MongoDB database (agent2db)
db = AgentDatabase()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """
    Initialize agent database with default configuration.
    This runs when the agent container starts up.
    """
    # Set default configuration for this agent
    db.set_config("memory_window_size", 15, "Maximum number of memories to keep")
    db.set_config("task_timeout", 300, "Task timeout in seconds")
    db.set_config("learning_enabled", True, "Enable learning from completed tasks")
    
    # Log agent startup
    db.log("info", "Agent 2 database initialized!")
    print("🤖 Agent 2 database initialized!")

@app.post("/execute")
async def execute_task(req: Request):
    """
    Main task execution endpoint.
    
    Receives a task, processes it with Claude AI, stores in this agent's database,
    and returns the result. Uses agent's memory for context.
    
    Process:
    1. Create task record in agent's database
    2. Get agent's memory for context
    3. Process with Claude AI using memory context
    4. Store result in database
    5. Add to agent's memory
    6. Clean up old memories (memory window management)
    7. Log activity
    """
    try:
        # Parse task payload
        task_payload = await req.json()
        input_text = task_payload.get("input_text", "")
        task_type = task_payload.get("task_type", "general")
        
        # Create task record in this agent's database
        task_id = db.create_task(
            title=f"Task: {task_type}",
            description=input_text,
            input_data=task_payload,
            status="in_progress"
        )
        
        # Get agent's memory for context (from this agent's database only)
        memories = db.get_memories(limit=5)
        memory_context = "\n".join([mem["content"] for mem in memories])
        
        # Build prompt with memory context
        system_prompt = "You are Agent 2, a specialized Claude AI assistant. Use your memory for context."
        if memory_context:
            system_prompt += f"\n\nYour recent memories:\n{memory_context}"
        
        # Process with Claude AI (using OpenAI API for now)
        completion = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Using GPT-4 for now, can be changed to Claude
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ]
        )
        
        response = completion.choices[0].message.content
        
        # Update task with result in this agent's database
        db.update_task(task_id, {
            "status": "completed",
            "output_data": {"response": response, "model": "claude-ai"}
        })
        
        # Add result to this agent's memory
        db.add_memory(
            content=f"Completed {task_type} task: {input_text[:50]}... Result: {response[:100]}...",
            memory_type="task_result",
            task_id=task_id
        )
        
        # Clean up old memories (memory window management)
        memory_window_size = db.get_config("memory_window_size", 15)
        db.cleanup_old_memories(memory_window_size)
        
        # Log the activity in this agent's database
        db.log("info", f"Completed task {task_id}", task_id)
        
        return {
            "response": response,
            "task_id": task_id,
            "status": "completed"
        }
        
    except Exception as e:
        # Log error in this agent's database
        db.log("error", f"Task execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def get_tasks():
    """
    Get all tasks for this agent from its own database.
    
    Returns:
        dict: List of tasks from this agent's database only
    """
    tasks = db.get_tasks(limit=10)
    return {"tasks": [{"id": str(t["_id"]), "title": t["title"], "status": t["status"], "created_at": t["created_at"]} for t in tasks]}

@app.get("/memory")
async def get_memory():
    """
    Get this agent's memory from its own database.
    
    Returns:
        dict: List of memories from this agent's database only
    """
    memories = db.get_memories(limit=10)
    return {"memories": [{"content": m["content"], "type": m["memory_type"], "created_at": m["created_at"]} for m in memories]}

@app.get("/config")
async def get_config():
    """
    Get this agent's configuration from its own database.
    
    Returns:
        dict: Configuration settings from this agent's database only
    """
    configs = db.config.find()
    return {"config": {c["key"]: c["value"] for c in configs}}

@app.get("/logs")
async def get_logs():
    """
    Get this agent's logs from its own database.
    
    Returns:
        dict: List of log entries from this agent's database only
    """
    logs = db.get_logs(limit=50)
    return {"logs": [{"level": l["level"], "message": l["message"], "created_at": l["created_at"]} for l in logs]}