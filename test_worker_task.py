#!/usr/bin/env python3
"""
Simple test script to create a task and verify the worker picks it up.
Run this from your local machine (not inside Docker).
"""

import os
import sys
import time

# Add storage to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'storage'))

from storage.postgres_adapter import PostgresAdapter

def main():
    print("=" * 60)
    print("AGENT WORKER TEST")
    print("=" * 60)
    print()
    
    # Use localhost:5433 for local connections
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://hub:hubpassword@localhost:5433/hub")
    
    print(f"Connecting to PostgreSQL at: {postgres_url[:50]}...")
    pg = PostgresAdapter(connection_string=postgres_url)
    print("✓ Connected to PostgreSQL")
    print()
    
    # Create a test task
    print("Creating test task...")
    task_id = pg.create_task(
        agent_id="agent1",
        title="Test Task: Print Hello World",
        description="This is a test task to verify the agent worker is working.",
        status="pending",
        metadata={"test": True, "source": "test_script"}
    )
    print(f"✓ Created test task with ID: {task_id}")
    print()
    
    # Wait and check progress
    print("Waiting 10 seconds for worker to pick up task...")
    print("(Watch worker logs with: docker-compose logs -f agent_worker)")
    print()
    
    for i in range(10):
        time.sleep(1)
        progress_updates = pg.get_task_progress(task_id, limit=5)
        if progress_updates:
            latest = progress_updates[0]
            progress = latest.get('progress_percent') or 0
            print(f"[{i+1}s] Progress: {progress}% - {latest.get('message', 'N/A')}")
            if progress >= 100:
                print("\n✓ Task completed!")
                break
    
    print()
    print("=" * 60)
    print("Task Details:")
    print("=" * 60)
    task = pg.get_task(task_id)
    if task:
        print(f"ID: {task['id']}")
        print(f"Title: {task['title']}")
        print(f"Status: {task['status']}")
        print(f"Created: {task['created_at']}")
        print(f"Updated: {task.get('updated_at', 'N/A')}")
    
    print()
    print("To view worker logs:")
    print("  docker-compose logs -f agent_worker")
    print()
    print("To check task progress:")
    print(f"  docker exec -it ai_village_but_better-postgres-1 psql -U hub -d hub -c \"SELECT * FROM task_progress WHERE task_id = {task_id} ORDER BY timestamp DESC LIMIT 5;\"")
    print()

if __name__ == "__main__":
    main()

