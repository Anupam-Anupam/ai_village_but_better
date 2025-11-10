#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to test CUA agent with Playwright screenshot capture.
Sends a task to write "hello world" in terminal and captures periodic screenshots using Playwright.
Screenshots are saved to the local machine's root directory (/app/screenshots/ in container).
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
TASK_TEXT = 'Write "hello world" in the terminal and take a screenshot of it. if the terminal is full delete what exists and write "hellow world". do not return with any questions, be decisive.'

def check_services():
    """Check if required services are running."""
    print("="*60)
    print("Checking Services")
    print("="*60)
    
    services_ok = True
    
    # Check server
    try:
        response = requests.get(f"{SERVER_URL}/tasks", timeout=5)
        if response.status_code == 200:
            print("[OK] Server is running")
        else:
            print(f"[WARN] Server returned status {response.status_code}")
            services_ok = False
    except Exception as e:
        print(f"[ERROR] Cannot connect to server: {e}")
        print(f"   Make sure server is running at {SERVER_URL}")
        services_ok = False
    
    # Check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="hub",
            password="hubpassword",
            database="hub",
            connect_timeout=5
        )
        conn.close()
        print("[OK] PostgreSQL is accessible")
    except Exception as e:
        print(f"[ERROR] Cannot connect to PostgreSQL: {e}")
        services_ok = False
    
    # MinIO check removed - screenshots are now saved locally
    
    # Check agent_worker
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=agent_worker", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"[OK] agent_worker is running: {result.stdout.strip()}")
        else:
            print("[WARN] agent_worker may not be running")
            print("   Start it with: docker-compose up -d agent_worker")
    except Exception as e:
        print(f"[WARN] Could not check agent_worker status: {e}")
    
    return services_ok


def create_task(task_text: str):
    """Create a task via the server API."""
    print("\n" + "="*60)
    print("Creating Task")
    print("="*60)
    print(f"Task: {task_text}")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/task",
            json={"text": task_text},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"[OK] Task created successfully")
            print(f"   Task ID: {task_id}")
            return task_id
        else:
            print(f"[ERROR] Failed to create task: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error creating task: {e}")
        import traceback
        traceback.print_exc()
        return None


def wait_for_task_completion(task_id: int, timeout: int = 180):
    """Wait for task to complete and return the result."""
    print("\n" + "="*60)
    print(f"Waiting for Task {task_id} to Complete")
    print("="*60)
    print(f"Timeout: {timeout} seconds")
    print("   (This may take a while as the CUA agent needs to:")
    print("    1. Connect to the VM")
    print("    2. Write 'hello world' in terminal")
    print("    3. Playwright captures periodic screenshots every 5 seconds)")
    
    start_time = time.time()
    last_status = None
    last_progress = None
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{SERVER_URL}/task/{task_id}", timeout=5)
            if response.status_code == 200:
                task = response.json()
                status = task.get("status", "unknown")
                
                # Check progress updates
                progress = task.get("progress", [])
                if progress:
                    latest_progress = progress[-1]
                    progress_msg = latest_progress.get("message", "")
                    if progress_msg != last_progress:
                        print(f"   Progress: {progress_msg}")
                        last_progress = progress_msg
                
                if status != last_status:
                    print(f"   Status: {status}")
                    last_status = status
                
                if status == "completed":
                    print(f"[OK] Task completed!")
                    return task
                elif status == "failed":
                    print(f"[ERROR] Task failed!")
                    return task
                elif status in ["pending", "assigned", "in_progress"]:
                    # Still processing
                    pass
                else:
                    print(f"   Status: {status}")
                    
            else:
                print(f"[WARN] Failed to get task status: {response.status_code}")
                
        except Exception as e:
            print(f"[WARN] Error checking task status: {e}")
        
        time.sleep(3)
    
    print(f"[ERROR] Task did not complete within {timeout} seconds")
    return None


def check_screenshots(task_id: int):
    """Check for screenshots related to this task."""
    print("\n" + "="*60)
    print("Checking Screenshots")
    print("="*60)
    
    try:
        # Check PostgreSQL for screenshot metadata
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="hub",
            password="hubpassword",
            database="hub",
            connect_timeout=5
        )
        cursor = conn.cursor()
        
        # Check task_progress for screenshot messages
        cursor.execute("""
            SELECT message, timestamp 
            FROM task_progress 
            WHERE task_id = %s AND message LIKE '%%screenshot%%'
            ORDER BY timestamp DESC
        """, (task_id,))
        
        progress_rows = cursor.fetchall()
        if progress_rows:
            print(f"Found {len(progress_rows)} screenshot-related progress messages:")
            for message, timestamp in progress_rows[:5]:
                print(f"  - {message} ({timestamp})")
        else:
            print("[INFO] No screenshot messages found in task_progress")
        
        cursor.close()
        conn.close()
        
        # Check local filesystem for screenshots
        print("\nChecking local filesystem for screenshots...")
        screenshot_dirs = [
            Path("./screenshots"),  # Local directory
            Path("/app/screenshots"),  # Container directory (if accessible)
        ]
        
        found_screenshots = []
        for screenshot_dir in screenshot_dirs:
            if screenshot_dir.exists() and screenshot_dir.is_dir():
                print(f"Checking directory: {screenshot_dir}")
                # Look for periodic screenshots
                screenshot_files = list(screenshot_dir.glob("periodic_screenshot_*.png"))
                if screenshot_files:
                    # Sort by modification time, most recent first
                    screenshot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    found_screenshots.extend(screenshot_files[:10])  # Get up to 10 most recent
                    print(f"  Found {len(screenshot_files)} screenshot file(s) in {screenshot_dir}")
        
        # Also check inside container via docker exec
        print("\nChecking container /app/screenshots directory...")
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "exec", "ai_village_but_better-agent_worker-1", "ls", "-la", "/app/screenshots"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("Container screenshots directory contents:")
                print(result.stdout)
                
                # Try to get file list
                result2 = subprocess.run(
                    ["docker", "exec", "ai_village_but_better-agent_worker-1", "find", "/app/screenshots", "-name", "*.png", "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result2.returncode == 0 and result2.stdout.strip():
                    files = result2.stdout.strip().split('\n')
                    print(f"  Found {len(files)} screenshot file(s) in container:")
                    for f in files[:5]:  # Show first 5
                        print(f"    - {f}")
                    found_screenshots.extend([Path(f) for f in files])
        except Exception as e:
            print(f"  Could not check container directory: {e}")
        
        if found_screenshots:
            # Remove duplicates and sort by modification time
            unique_screenshots = list(set(found_screenshots))
            print(f"\n[OK] Found {len(unique_screenshots)} screenshot file(s) total:")
            for screenshot_path in unique_screenshots[:5]:  # Show first 5
                try:
                    if screenshot_path.exists():
                        size = screenshot_path.stat().st_size
                        mtime = datetime.fromtimestamp(screenshot_path.stat().st_mtime)
                        print(f"  - {screenshot_path} ({size} bytes, modified: {mtime})")
                except:
                    print(f"  - {screenshot_path} (in container)")
            return True
        else:
            print("[WARN] No screenshot files found in local directories")
            return False
        
    except Exception as e:
        print(f"[ERROR] Error checking screenshots: {e}")
        import traceback
        traceback.print_exc()
        return False


def view_screenshots():
    """Provide instructions to view screenshots."""
    print("\n" + "="*60)
    print("View Screenshots")
    print("="*60)
    print("Screenshots are saved to the local machine's root directory:")
    print("  - In container: /app/screenshots/")
    print("  - Locally: ./screenshots/")
    print("\nTo view screenshots from container:")
    print("  1. Copy from container: docker cp ai_village_but_better-agent_worker-1:/app/screenshots ./screenshots")
    print("  2. Or exec into container: docker exec -it ai_village_but_better-agent_worker-1 ls -la /app/screenshots")
    print("\nTo view local screenshots:")
    print("  1. Check ./screenshots/ directory")
    print("  2. Open any .png file with an image viewer")


def check_agent_worker_logs():
    """Check agent_worker logs for screenshot upload messages."""
    print("\n" + "="*60)
    print("Agent Worker Logs (Recent Screenshot Messages)")
    print("="*60)
    
    try:
        import subprocess
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", "50", "agent_worker"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_root)
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            screenshot_lines = [line for line in lines if 'screenshot' in line.lower() or 'uploaded' in line.lower()]
            
            if screenshot_lines:
                print("Recent screenshot-related log messages:")
                for line in screenshot_lines[-10:]:  # Last 10
                    print(f"  {line}")
            else:
                print("[INFO] No screenshot-related messages in recent logs")
        else:
            print(f"[WARN] Could not get agent_worker logs: {result.stderr}")
    except Exception as e:
        print(f"[WARN] Could not check agent_worker logs: {e}")


def main():
    """Main test function."""
    print("="*60)
    print("CUA AGENT SCREENSHOT TEST (Playwright)")
    print("="*60)
    print(f"Task: {TASK_TEXT}")
    print(f"Server: {SERVER_URL}")
    print("\nNote: Screenshots are captured using Playwright every 5 seconds")
    print("      and saved to /app/screenshots/ in container (./screenshots/ locally).")
    
    # Step 1: Check services
    if not check_services():
        print("\n[ERROR] Some services are not running. Please start them first:")
        print("   docker-compose up -d postgres mongodb server agent_worker")
        return 1
    
    # Step 2: Create task
    task_id = create_task(TASK_TEXT)
    if not task_id:
        print("\n[ERROR] Failed to create task")
        return 1
    
    # Step 3: Wait for completion
    print(f"\nWaiting for agent_worker to pick up and execute task {task_id}...")
    print("   (This may take 1-3 minutes)")
    task_result = wait_for_task_completion(task_id, timeout=300)  # 5 minutes timeout
    if not task_result:
        print("\n[ERROR] Task did not complete within timeout")
        print("   Check agent_worker logs: docker-compose logs agent_worker")
        return 1
    
    # Step 4: Check screenshots
    has_screenshots = check_screenshots(task_id)
    
    # Step 5: Check agent_worker logs
    check_agent_worker_logs()
    
    # Step 6: Provide viewing instructions
    view_screenshots()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Task ID: {task_id}")
    print(f"Status: {task_result.get('status', 'unknown')}")
    print(f"Screenshots found: {'Yes' if has_screenshots else 'No'}")
    
    if has_screenshots:
        print("\n[SUCCESS] Screenshots were captured using Playwright and saved locally!")
        print("   Location: /app/screenshots/ in container or ./screenshots/ locally")
        print("   Screenshots are captured every 5 seconds during task execution")
        print("\nTo copy screenshots from container:")
        print("   docker cp ai_village_but_better-agent_worker-1:/app/screenshots ./screenshots")
    else:
        print("\n[WARN] No screenshots found. This could mean:")
        print("   1. Playwright couldn't connect to the Computer's display URL")
        print("   2. Screenshots are being processed")
        print("   3. Check agent_worker logs for errors:")
        print("      docker-compose logs agent_worker | Select-String -Pattern 'screenshot|Playwright'")
        print("   4. Check if Computer object has a display_url attribute")
        print("   5. Check container directory: docker exec ai_village_but_better-agent_worker-1 ls -la /app/screenshots")
    
    return 0 if has_screenshots else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
