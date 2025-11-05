#!/usr/bin/env python3
"""
Simple script to send a task to CUA agents and run them.
Takes user input, sends it to the chat server, and starts all three agents.

Can run as:
1. CLI script: python run_task.py [task]
2. API server: python run_task.py --api
"""

import subprocess
import sys
import os
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add CUA directory to path for storage integration
sys.path.insert(0, str(Path(__file__).parent / "CUA"))

# Try to import storage integration
try:
    from storage_integration import store_task
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    store_task = None
    print("⚠️  Warning: storage_integration.py not available. Tasks will not be stored in database.")

# Configuration
CHAT_SERVER_URL = os.getenv("CHAT_SERVER_URL", "http://localhost:8000")
AGENT_IDS = ["agent1-cua", "agent2-cua", "agent3-cua"]
PROJECT_ROOT = Path(__file__).parent

# Global state for API mode
_running_processes: Dict[str, subprocess.Popen] = {}
_seen_responses: Dict[str, Set[Path]] = {agent_id: set() for agent_id in AGENT_IDS}
_stop_monitoring = threading.Event()
_monitor_threads: List[threading.Thread] = []


# Import traj-sorter functions
def is_agent_response(filename: str, data: Dict) -> bool:
    """Check if a file is an agent response based on filename and content."""
    name = filename.lower()
    if "agent_response" in name or "agent-response" in name:
        return True
    # Heuristic: messages from agent/assistant
    if isinstance(data, dict):
        # CUA logs often have a list under "output" with type/message
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content", [])
                    if content:
                        return True
        # Check response.output structure
        response = data.get("response", {})
        if isinstance(response, dict):
            output = response.get("output", [])
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict) and item.get("type") == "message":
                        content = item.get("content", [])
                        if content:
                            return True
        # Lite logs may contain role-based messages
        role = data.get("role")
        if role == "assistant":
            return True
    return False


def extract_agent_response_text(data: Dict) -> Optional[str]:
    """Extract text content from an agent response JSON."""
    # Check response.output structure (most common)
    response = data.get("response", {})
    if isinstance(response, dict):
        output = response.get("output", [])
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content", [])
                    if isinstance(content, list):
                        for content_item in content:
                            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                text = content_item.get("text")
                                if text:
                                    return text
    # Check direct output structure
    output = data.get("output", [])
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") == "message":
                content = item.get("content", [])
                if isinstance(content, list):
                    for content_item in content:
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            text = content_item.get("text")
                            if text:
                                return text
    return None


def get_latest_trajectory_folder(agent_id: str) -> Optional[Path]:
    """Get the latest trajectory folder for an agent."""
    trajectories_dir = PROJECT_ROOT / "agents" / agent_id / "trajectories"
    if not trajectories_dir.exists():
        return None
    
    # Get all trajectory folders (they're named with timestamps)
    folders = [d for d in trajectories_dir.iterdir() if d.is_dir()]
    if not folders:
        return None
    
    # Sort by modification time (most recent first)
    folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return folders[0]


def monitor_agent_responses(agent_id: str, seen_files: Set[Path], stop_event: threading.Event):
    """Monitor trajectory folder for new agent responses."""
    while not stop_event.is_set():
        try:
            latest_folder = get_latest_trajectory_folder(agent_id)
            if not latest_folder:
                time.sleep(2)
                continue
            
            # Collect all JSON files in the latest trajectory folder
            json_files = list(latest_folder.rglob("*.json"))
            
            for json_file in json_files:
                # Skip if we've already seen this file
                if json_file in seen_files:
                    continue
                
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Check if this is an agent response
                    if is_agent_response(json_file.name, data):
                        seen_files.add(json_file)
                        # Extract and print the response text
                        response_text = extract_agent_response_text(data)
                        if response_text:
                            print(f"\n[{agent_id}] {response_text}")
                        else:
                            # If we can't extract text, at least notify
                            print(f"\n[{agent_id}] Agent response detected (file: {json_file.name})")
                
                except (json.JSONDecodeError, IOError) as e:
                    # Skip files that can't be read
                    continue
            
            time.sleep(1)  # Check every second
        
        except Exception as e:
            print(f"⚠️  Error monitoring {agent_id}: {e}")
            time.sleep(2)


def get_agent_responses() -> Dict[str, List[Dict]]:
    """Get all agent responses from trajectory folders (for API)."""
    responses = {}
    
    for agent_id in AGENT_IDS:
        latest_folder = get_latest_trajectory_folder(agent_id)
        if not latest_folder:
            responses[agent_id] = []
            continue
        
        # Collect all agent response JSON files
        json_files = list(latest_folder.rglob("*.json"))
        agent_responses = []
        
        for json_file in json_files:
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if is_agent_response(json_file.name, data):
                    response_text = extract_agent_response_text(data)
                    if response_text:
                        agent_responses.append({
                            "text": response_text,
                            "file": str(json_file.relative_to(PROJECT_ROOT)),
                            "timestamp": json_file.stat().st_mtime
                        })
            except Exception:
                continue
        
        # Sort by timestamp (newest first)
        agent_responses.sort(key=lambda x: x["timestamp"], reverse=True)
        responses[agent_id] = agent_responses
    
    return responses


def write_task_to_file(task_content: str):
    """Write task to the shared tasks file."""
    tasks_file = PROJECT_ROOT / "tasks.txt"
    print(f"📝 Writing task to file: {task_content[:60]}...")
    
    try:
        with open(tasks_file, "w") as f:
            f.write(task_content + "\n")
        print(f"✅ Task written to {tasks_file}")
    except Exception as e:
        print(f"❌ Failed to write task: {e}")
        sys.exit(1)


def start_agent(agent_id: str) -> subprocess.Popen:
    """Start a CUA agent process."""
    agent_dir = PROJECT_ROOT / "agents" / agent_id
    main_py = agent_dir / "main.py"
    
    if not main_py.exists():
        print(f"⚠️  Warning: {main_py} not found, skipping {agent_id}")
        return None
    
    env = os.environ.copy()
    env["CHAT_SERVER_URL"] = CHAT_SERVER_URL
    env["AGENT_ID"] = agent_id
    env["CHAT_POLL_INTERVAL"] = "5.0"
    
    print(f"🚀 Starting {agent_id}...")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(main_py)],
            cwd=str(agent_dir),
            env=env,
            stdout=subprocess.DEVNULL,  # avoid PIPE buffer blocking
            stderr=subprocess.DEVNULL,
        )
        print(f"   ✅ {agent_id} started (PID: {proc.pid})")
        return proc
    except Exception as e:
        print(f"   ❌ Failed to start {agent_id}: {e}")
        return None




def main():
    """Main function."""
    print("=" * 60)
    print("AI Village CUA Agent Task Runner")
    print("=" * 60)
    print()
    
    # Get user input
    if len(sys.argv) > 1:
        task_content = " ".join(sys.argv[1:])
    else:
        print("Enter your task for the CUA agents:")
        task_content = input("> ").strip()
    
    if not task_content:
        print("❌ No task provided. Exiting.")
        sys.exit(1)
    
    print()
    
    # Store task in database
    if STORAGE_AVAILABLE and store_task:
        task_id = store_task(task_content, agent_id="task_runner")
        if task_id:
            print(f"💾 Task stored in database (task_id: {task_id})")
    
    # Write task to file
    write_task_to_file(task_content)
    
    # Start all agents
    print(f"\n🤖 Starting all agents...")
    processes = []
    for agent_id in AGENT_IDS:
        proc = start_agent(agent_id)
        if proc:
            processes.append((agent_id, proc))
    
    if not processes:
        print("❌ No agents started. Exiting.")
        sys.exit(1)
    
    print(f"\n✅ {len(processes)} agent(s) running")
    print(f"   Agents will poll for tasks every 5 seconds")
    print(f"   Press Ctrl+C to stop agents\n")
    
    # Wait a bit for agents to start
    time.sleep(3)
    
    print(f"\n💡 Agents will read tasks from tasks.txt and process them.")
    
    # Start monitoring agent responses in background threads
    print(f"\n📡 Starting response monitoring for all agents...")
    stop_monitoring = threading.Event()
    seen_files: Dict[str, Set[Path]] = {agent_id: set() for agent_id in AGENT_IDS}
    monitor_threads = []
    
    for agent_id in AGENT_IDS:
        thread = threading.Thread(
            target=monitor_agent_responses,
            args=(agent_id, seen_files[agent_id], stop_monitoring),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
    
    print(f"   ✅ Monitoring {len(monitor_threads)} agents for responses\n")
    
    # Keep running until interrupted
    try:
        print(f"\n💡 Agents are running in the background.")
        print(f"   They will continuously check tasks.txt for new tasks.")
        print(f"   Agent responses will appear here as they come in.")
        print(f"   Press Ctrl+C to stop all agents.\n")
        
        # Wait for all processes
        while True:
            time.sleep(1)
            # Check if any process died unexpectedly
            processes_to_remove = []
            for agent_id, proc in processes:
                if proc.poll() is not None:
                    exit_code = proc.returncode
                    if exit_code != 0:
                        print(f"⚠️  {agent_id} process ended unexpectedly (exit code: {exit_code})")
                        processes_to_remove.append((agent_id, proc))
                    # If exit code is 0, agent is still running (continuous loop)
            
            # Remove dead processes
            for item in processes_to_remove:
                processes.remove(item)
    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopping all agents and monitoring...")
        # Stop monitoring threads
        stop_monitoring.set()
        for thread in monitor_threads:
            thread.join(timeout=1)
        
        # Stop agent processes
        for agent_id, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"   ✅ {agent_id} stopped")
            except:
                proc.kill()
                print(f"   ⚠️  {agent_id} force-killed")
        print("\n✅ All agents stopped. Exiting.")


# API Models
class TaskRequest(BaseModel):
    task: str


# FastAPI app setup
api_app = FastAPI(title="AI Village Task Runner API")

# Add CORS middleware
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_app.post("/task")
async def create_task(request: TaskRequest):
    """Create a task by writing to tasks.txt and optionally starting agents."""
    task_content = request.task.strip()
    
    if not task_content:
        raise HTTPException(status_code=400, detail="No task provided")
    
    # Store task in database
    task_id = None
    if STORAGE_AVAILABLE and store_task:
        task_id = store_task(task_content, agent_id="task_runner")
    
    # Write task to file
    try:
        write_task_to_file(task_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write task: {str(e)}")
    
    # Start agents if not already running
    started_agents = []
    for agent_id in AGENT_IDS:
        if agent_id not in _running_processes or _running_processes[agent_id].poll() is not None:
            proc = start_agent(agent_id)
            if proc:
                _running_processes[agent_id] = proc
                started_agents.append(agent_id)
    
    # Start monitoring if not already started
    if not _monitor_threads:
        for agent_id in AGENT_IDS:
            thread = threading.Thread(
                target=monitor_agent_responses,
                args=(agent_id, _seen_responses[agent_id], _stop_monitoring),
                daemon=True
            )
            thread.start()
            _monitor_threads.append(thread)
    
    return {
        "success": True,
        "task": task_content,
        "task_id": task_id,
        "started_agents": started_agents,
        "message": "Task written to tasks.txt. Agents will pick it up on their next poll."
    }


@api_app.get("/agent-responses")
async def get_responses():
    """Get latest agent responses from trajectory folders."""
    return {"responses": get_agent_responses()}


@api_app.get("/agents/status")
async def get_agents_status():
    """Get status of running agents."""
    status = {}
    for agent_id in AGENT_IDS:
        if agent_id in _running_processes:
            proc = _running_processes[agent_id]
            is_running = proc.poll() is None
            status[agent_id] = {
                "running": is_running,
                "pid": proc.pid if is_running else None,
            }
        else:
            status[agent_id] = {
                "running": False,
                "pid": None,
            }
    return {"agents": status}


@api_app.post("/agents/start")
async def start_all_agents():
    """Manually start all agents."""
    started = []
    for agent_id in AGENT_IDS:
        if agent_id not in _running_processes or _running_processes[agent_id].poll() is not None:
            proc = start_agent(agent_id)
            if proc:
                _running_processes[agent_id] = proc
                started.append(agent_id)
    
    # Start monitoring if not already started
    if not _monitor_threads:
        for agent_id in AGENT_IDS:
            thread = threading.Thread(
                target=monitor_agent_responses,
                args=(agent_id, _seen_responses[agent_id], _stop_monitoring),
                daemon=True
            )
            thread.start()
            _monitor_threads.append(thread)
    
    return {"started": started, "message": f"Started {len(started)} agent(s)"}


@api_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@api_app.get("/")
async def root():
    """Root endpoint to avoid 404 and show basic API info."""
    return {
        "name": "AI Village Task Runner API",
        "status": "ok",
        "endpoints": [
            {"method": "POST", "path": "/task", "desc": "Create a task and start agents if needed"},
            {"method": "GET", "path": "/agent-responses", "desc": "Get latest agent responses"},
            {"method": "GET", "path": "/agents/status", "desc": "Get running agents status"},
            {"method": "POST", "path": "/agents/start", "desc": "Start all agents"},
            {"method": "GET", "path": "/health", "desc": "Health check"},
        ]
    }


@api_app.get("/favicon.ico")
async def favicon():
    """Placeholder to prevent 404 noise for browsers requesting favicon."""
    from fastapi import Response
    return Response(content=b"", media_type="image/x-icon")


if __name__ == "__main__":
    # Check if running in API mode
    if "--api" in sys.argv or os.getenv("RUN_TASK_API", "").lower() == "true":
        import uvicorn
        import socket
        
        # Find an available port starting from 8001
        def find_free_port(start_port=8001):
            for port in range(start_port, start_port + 10):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('', port))
                        return port
                except OSError:
                    continue
            return start_port  # Fallback to start_port if all are busy
        
        port = int(os.getenv("RUN_TASK_PORT", "0"))
        if port == 0:
            port = find_free_port()
        
        print(f"🚀 Starting run_task.py API server on port {port}")
        print(f"   Endpoints:")
        print(f"   - POST /task - Create a task")
        print(f"   - GET /agent-responses - Get agent responses")
        print(f"   - GET /agents/status - Get agent status")
        print(f"   - POST /agents/start - Start all agents")
        print(f"   - GET /health - Health check")
        print(f"   - Frontend should connect to: http://localhost:{port}")
        uvicorn.run(api_app, host="0.0.0.0", port=port)
    else:
        # Run as CLI script
        main()

