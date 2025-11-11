#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify agent worker response to tasks.
This script:
1. Creates a task in PostgreSQL
2. Monitors the agent worker to pick it up
3. Tracks progress updates
4. Retrieves and displays the final response

Usage:
    python test_agent_response.py "Your task description here"
    or
    python test_agent_response.py  # Uses default test task
"""

import os
import sys
import time
import json
from datetime import datetime

# Set UTF-8 encoding for stdout to handle any special characters
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 doesn't have reconfigure
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add storage to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'storage'))

from storage.postgres_adapter import PostgresAdapter


def print_section(title: str):
    """Print a formatted section header."""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()


def get_task_description() -> str:
    """Get task description from command line or use default."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    else:
        return "Open a web browser and search for 'Python programming tutorials'"


def main():
    print_section("AGENT WORKER RESPONSE TEST")
    
    # Get task description
    task_description = get_task_description()
    print(f"Task Description: {task_description}")
    print()
    
    # Connect to PostgreSQL
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://hub:hubpassword@localhost:5433/hub")
    print(f"Connecting to PostgreSQL...")
    try:
        pg = PostgresAdapter(connection_string=postgres_url)
        print("[OK] Connected to PostgreSQL")
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
        print(f"\nMake sure Docker containers are running:")
        print(f"  docker-compose up -d postgres")
        print(f"\nOr check your POSTGRES_URL environment variable")
        return 1
    
    print_section("CREATING TASK")
    
    # Create a test task
    try:
        task_id = pg.create_task(
            agent_id="test_user",
            title=f"Test Task: {task_description[:50]}...",
            description=task_description,
            status="pending",
            metadata={"test": True, "source": "test_agent_response", "created_at": datetime.utcnow().isoformat()}
        )
        print(f"[OK] Created task with ID: {task_id}")
        print(f"  Title: Test Task: {task_description[:50]}...")
        print(f"  Description: {task_description}")
    except Exception as e:
        print(f"[ERROR] Failed to create task: {e}")
        return 1
    
    print_section("MONITORING TASK EXECUTION")
    
    print("Waiting for agent worker to pick up task...")
    print("(Watch worker logs with: docker-compose logs -f agent_worker)")
    print()
    
    max_wait_time = 300  # 5 minutes max
    check_interval = 2  # Check every 2 seconds
    start_time = time.time()
    last_progress = -1
    task_completed = False
    
    while time.time() - start_time < max_wait_time:
        elapsed = int(time.time() - start_time)
        
        try:
            # Get task details
            task = pg.get_task(task_id)
            if not task:
                print(f"[{elapsed}s] Task not found (may have been deleted)")
                break
            
            # Get progress updates
            progress_updates = pg.get_task_progress(task_id, limit=10)
            
            # Get latest progress
            if progress_updates:
                latest = progress_updates[0]
                current_progress = latest.get('progress_percent') or 0
                message = latest.get('message', 'N/A')
                
                # Only print if progress changed
                if current_progress != last_progress:
                    print(f"[{elapsed}s] Progress: {current_progress}% - {message}")
                    last_progress = current_progress
                
                # Check if task is completed
                if current_progress >= 100:
                    task_completed = True
                    print(f"\n[OK] Task completed!")
                    break
            else:
                if elapsed % 10 == 0:  # Print every 10 seconds if no progress
                    print(f"[{elapsed}s] Waiting for agent worker to start...")
            
            # Check task status
            status = task.get('status', 'unknown')
            if status in ['completed', 'failed']:
                task_completed = True
                print(f"\n[OK] Task finished with status: {status}")
                break
                
        except Exception as e:
            print(f"[{elapsed}s] Error checking progress: {e}")
        
        time.sleep(check_interval)
    
    if not task_completed:
        print(f"\n[WARNING] Task did not complete within {max_wait_time} seconds")
        print("   The agent worker may still be processing the task.")
        print("   Check logs: docker-compose logs -f agent_worker")
    
    print_section("TASK RESULTS")
    
    # Get final task details
    try:
        task = pg.get_task(task_id)
        if task:
            print(f"Task ID: {task['id']}")
            print(f"Title: {task.get('title', 'N/A')}")
            print(f"Status: {task.get('status', 'N/A')}")
            print(f"Created: {task.get('created_at', 'N/A')}")
            print(f"Updated: {task.get('updated_at', 'N/A')}")
            
            # Get metadata (which may contain the response)
            # PostgresAdapter returns 'metadata' not 'task_metadata'
            metadata = task.get('metadata', {}) or task.get('task_metadata', {}) or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            # Check for response in metadata
            response = metadata.get('response') or metadata.get('last_response')
            if response:
                print()
                print("Agent Response:")
                print("-" * 60)
                print(response)
                print("-" * 60)
            else:
                print()
                print("No response found in task metadata")
                print("Metadata keys:", list(metadata.keys()) if metadata else "None")
        else:
            print("Task not found")
    except Exception as e:
        print(f"Error retrieving task: {e}")
    
    # Get all progress updates
    print()
    print("Progress Updates:")
    print("-" * 60)
    try:
        progress_updates = pg.get_task_progress(task_id, limit=20)
        if progress_updates:
            for update in reversed(progress_updates):  # Show oldest first
                progress = update.get('progress_percent', 0)
                # Convert to int if it's a float
                if progress is not None:
                    progress = int(float(progress))
                else:
                    progress = 0
                message = update.get('message', 'N/A')
                timestamp = update.get('timestamp', update.get('created_at', 'N/A'))
                print(f"[{progress:3d}%] {timestamp} - {message}")
        else:
            print("No progress updates found")
    except Exception as e:
        print(f"Error retrieving progress: {e}")
    
    print()
    print_section("NEXT STEPS")
    
    print("To view agent worker logs:")
    print("  docker-compose logs -f agent_worker")
    print()
    print("To check task in database:")
    print(f"  docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \"SELECT * FROM tasks WHERE id = {task_id};\"")
    print()
    print("To check progress updates:")
    print(f"  docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \"SELECT * FROM task_progress WHERE task_id = {task_id} ORDER BY timestamp DESC LIMIT 10;\"")
    print()
    print("To check MongoDB logs:")
    print("  docker exec -it ai_village_but_better-mongodb-1 mongosh -u admin -p password --authenticationDatabase admin --eval \"use agent_logs_db; db.agent_logs.find().sort({timestamp: -1}).limit(5).pretty()\"")
    print()
    
    return 0 if task_completed else 1


if __name__ == "__main__":
    sys.exit(main())

