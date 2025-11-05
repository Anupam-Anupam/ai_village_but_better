#!/usr/bin/env python3
"""
Simple script to send a task to CUA agents and run them.
Takes user input, sends it to the chat server, and starts all three agents.
"""

import subprocess
import sys
import os
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set

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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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


if __name__ == "__main__":
    main()

