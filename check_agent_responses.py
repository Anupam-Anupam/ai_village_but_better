#!/usr/bin/env python3
"""Check if agent responses are being stored in PostgreSQL."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from storage.postgres_adapter import PostgresAdapter
import json

def main():
    postgres_url = os.getenv(
        "POSTGRES_URL",
        "postgresql://hub:hubpassword@localhost:5433/hub"
    )
    
    pg = PostgresAdapter(postgres_url)
    
    print("=" * 60)
    print("CHECKING AGENT RESPONSES IN POSTGRESQL")
    print("=" * 60)
    print()
    
    # Check completed tasks
    print("📋 Completed Tasks with Responses:")
    print("-" * 60)
    tasks = pg.get_tasks(status='completed', limit=10)
    
    for task in tasks[:5]:
        print(f"\nTask {task['id']}: {task.get('title', '')[:60]}...")
        print(f"  Status: {task.get('status')}")
        metadata = task.get('metadata', {})
        response = metadata.get('response')
        if response:
            print(f"  ✅ Response found ({len(str(response))} chars):")
            print(f"     {str(response)[:200]}...")
        else:
            print(f"  ❌ No response in metadata")
            print(f"  Metadata keys: {list(metadata.keys())}")
    
    print("\n" + "=" * 60)
    print("📨 Recent Agent Messages (from get_recent_agent_messages):")
    print("-" * 60)
    
    messages = pg.get_recent_agent_messages(limit=10)
    
    for msg in messages[:5]:
        print(f"\nMessage ID {msg['id']}, Task {msg['task_id']}:")
        print(f"  Agent: {msg['agent_id']}")
        print(f"  Progress Message: {str(msg['message'])[:150]}...")
        
        task = msg.get('task')
        if task:
            task_metadata = task.get('metadata', {})
            task_response = task_metadata.get('response')
            if task_response:
                print(f"  ✅ Task metadata has response ({len(str(task_response))} chars):")
                print(f"     {str(task_response)[:200]}...")
            else:
                print(f"  ❌ No response in task metadata")
                print(f"  Task status: {task.get('status')}")
                print(f"  Task metadata keys: {list(task_metadata.keys())}")

if __name__ == "__main__":
    main()

