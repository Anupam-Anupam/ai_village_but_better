from fastapi import FastAPI, Request, HTTPException
from db import SessionLocal
from models import Agent, Task, Memory
import uuid
from sqlalchemy import desc

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Hub running!"}

@app.post("/query")
async def create_task(request: Request):
    data = await request.json()
    text = data["text"]

    # simulate parsing intent
    intent = {"target": "web_agent", "action": "research"}

    db = SessionLocal()
    new_task = Task(input_text=text, parsed_intent=intent, status="pending")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    db.close()

    return {"task_id": str(new_task.id), "intent": intent, "status": "queued"}

# Agent Communication Endpoints
@app.get("/agent/{agent_id}/tasks")
async def get_agent_tasks(agent_id: int):
    """Get pending tasks for an agent"""
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(
            Task.agent_id == agent_id,
            Task.status == "pending"
        ).all()
        return {"tasks": [{"id": t.id, "title": t.title, "description": t.description, "input_data": t.input_data} for t in tasks]}
    finally:
        db.close()

@app.get("/agent/{agent_id}/memory")
async def get_agent_memory(agent_id: int):
    """Get agent's memory window"""
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        memories = db.query(Memory).filter(
            Memory.agent_id == agent_id
        ).order_by(desc(Memory.created_at)).limit(agent.memory_window_size).all()
        
        return {"memories": [{"content": m.content, "type": m.memory_type, "created_at": m.created_at} for m in memories]}
    finally:
        db.close()

@app.post("/agent/{agent_id}/memory")
async def add_agent_memory(agent_id: int, request: Request):
    """Add a memory to agent's memory window"""
    data = await request.json()
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        memory = Memory(
            content=data["content"],
            memory_type=data.get("type", "general"),
            agent_id=agent_id,
            task_id=data.get("task_id")
        )
        db.add(memory)
        db.commit()
        
        # Clean up old memories if over limit
        memories = db.query(Memory).filter(Memory.agent_id == agent_id).order_by(desc(Memory.created_at)).all()
        if len(memories) > agent.memory_window_size:
            for old_memory in memories[agent.memory_window_size:]:
                db.delete(old_memory)
            db.commit()
        
        return {"status": "success", "memory_id": memory.id}
    finally:
        db.close()

@app.post("/agent/{agent_id}/task/{task_id}/complete")
async def complete_task(agent_id: int, task_id: int, request: Request):
    """Mark a task as completed with output"""
    data = await request.json()
    db = SessionLocal()
    try:
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.agent_id == agent_id
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.status = "completed"
        task.output_data = data.get("output")
        db.commit()
        
        # Add task result to memory
        memory = Memory(
            content=f"Completed task: {task.title}. Output: {data.get('output', 'No output')}",
            memory_type="task_result",
            agent_id=agent_id,
            task_id=task_id
        )
        db.add(memory)
        db.commit()
        
        return {"status": "success"}
    finally:
        db.close()

@app.post("/agent/{agent_id}/register")
async def register_agent(agent_id: int, request: Request):
    """Register an agent with container ID"""
    data = await request.json()
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent.container_id = data.get("container_id")
        agent.memory_window_size = data.get("memory_window_size", 10)
        db.commit()
        
        return {"status": "success", "agent_id": agent_id}
    finally:
        db.close()
