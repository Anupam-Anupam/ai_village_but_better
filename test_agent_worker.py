#!/usr/bin/env python3
"""
Test script to verify the agent worker is picking up and executing tasks.

This script:
1. Creates a test task in PostgreSQL
2. Monitors the worker logs
3. Checks task progress updates
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Add storage to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'storage'))

try:
    from storage.postgres_adapter import PostgresAdapter
except ImportError:
    print("ERROR: Could not import PostgresAdapter")
    print("Make sure you're running from the project root")
    sys.exit(1)


def create_test_task():
    """Create a test task in PostgreSQL."""
    print("=" * 60)
    print("Creating test task in PostgreSQL...")
    print("=" * 60)
    
    # Use localhost:5433 for local connections (outside Docker)
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://hub:hubpassword@localhost:5433/hub")
    
    # Initialize PostgreSQL adapter
    pg = PostgresAdapter(connection_string=postgres_url)
    
    # Create a test task
    task_id = pg.create_task(
        agent_id="agent1",
        title="Test Task: Print Hello World",
        description="This is a test task to verify the agent worker is working. The task should print 'Hello from test task!'",
        status="pending",
        metadata={"test": True, "created_at": datetime.utcnow().isoformat()}
    )
    
    print(f"✓ Created test task with ID: {task_id}")
    print(f"  Title: Test Task: Print Hello World")
    print(f"  Description: This is a test task to verify the agent worker is working.")
    print()
    
    return task_id, pg


def monitor_task_progress(pg, task_id, timeout=60):
    """Monitor task progress updates."""
    print("=" * 60)
    print(f"Monitoring task {task_id} progress (timeout: {timeout}s)...")
    print("=" * 60)
    
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < timeout:
        # Get task progress
        progress_updates = pg.get_task_progress(task_id, limit=10)
        
        if progress_updates:
            latest = progress_updates[0]
            current_progress = latest.get("progress_percent", 0)
            
            if current_progress != last_progress:
                print(f"[{time.time() - start_time:.1f}s] Progress: {current_progress}% - {latest.get('message', 'N/A')}")
                last_progress = current_progress
                
                if current_progress >= 100:
                    print("\n✓ Task completed!")
                    return True
        else:
            if time.time() - start_time < 5:
                print(f"[{time.time() - start_time:.1f}s] Waiting for progress updates...")
        
        time.sleep(2)
    
    print(f"\n⚠ Timeout reached ({timeout}s). Task may still be processing.")
    return False


def check_worker_logs():
    """Check if worker logs show activity."""
    print("=" * 60)
    print("Checking agent worker logs...")
    print("=" * 60)
    
    try:
        # Get recent logs
        result = subprocess.run(
            ["docker", "logs", "--tail", "20", "ai_village_but_better-agent_worker-1"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("Recent worker logs:")
            print("-" * 60)
            print(result.stdout)
            print("-" * 60)
        else:
            print("Could not retrieve logs (container may not be running)")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error checking logs: {e}")


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("AGENT WORKER TEST")
    print("=" * 60)
    print()
    
    # Check if worker container is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=agent_worker", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "agent_worker" not in result.stdout:
            print("⚠ WARNING: agent_worker container does not appear to be running")
            print("Start it with: docker-compose up -d agent_worker")
            print()
    except Exception as e:
        print(f"⚠ Could not check container status: {e}")
        print()
    
    # Create test task
    task_id, pg = create_test_task()
    
    # Wait a moment for worker to pick it up
    print("Waiting 3 seconds for worker to pick up task...")
    time.sleep(3)
    
    # Check worker logs
    check_worker_logs()
    print()
    
    # Monitor progress
    completed = monitor_task_progress(pg, task_id, timeout=120)
    
    # Final status
    print()
    print("=" * 60)
    print("FINAL STATUS")
    print("=" * 60)
    
    if completed:
        print("✓ Test PASSED: Task was picked up and completed by worker")
    else:
        print("⚠ Test INCOMPLETE: Task may still be processing or worker may not be running")
        print("Check logs with: docker-compose logs -f agent_worker")
    
    # Get final task info
    task = pg.get_task(task_id)
    if task:
        print(f"\nTask Details:")
        print(f"  ID: {task['id']}")
        print(f"  Status: {task['status']}")
        print(f"  Created: {task['created_at']}")
        print(f"  Updated: {task.get('updated_at', 'N/A')}")
    
    print()
    print("To view worker logs in real-time:")
    print("  docker-compose logs -f agent_worker")
    print()
    print("To check task progress in database:")
    print(f"  docker exec -it postgres psql -U hub -d hub -c \"SELECT * FROM task_progress WHERE task_id = {task_id} ORDER BY timestamp DESC LIMIT 5;\"")
    print()


if __name__ == "__main__":
    main()

