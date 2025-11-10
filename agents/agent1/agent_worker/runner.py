# Agent runner: orchestrates task polling, execution, and progress tracking
"""Agent runner that polls for tasks and executes run_task.py."""

import os
import subprocess
import time
import threading
import shutil
from pathlib import Path
from typing import Optional, Set, List
from datetime import datetime
from uuid import uuid4

from .config import Config
from .db_adapters import PostgresClient, MongoClientWrapper
from .storage import MinioClientWrapper


def list_new_screenshots(before: Set[str], after: Set[str]) -> List[str]:
    """
    Helper function to detect newly created screenshot files.
    
    Args:
        before: Set of filenames before task execution
        after: Set of filenames after task execution
        
    Returns:
        List of new filenames
    """
    return list(after - before)


class AgentRunner:
    """Agent runner that polls for tasks and executes them."""
    
    def __init__(
        self,
        config: Config,
        postgres_client: PostgresClient,
        mongo_client: MongoClientWrapper,
        minio_client: MinioClientWrapper
    ):
        """
        Initialize agent runner.
        
        Args:
            config: Configuration object
            postgres_client: PostgreSQL client
            mongo_client: MongoDB client
            minio_client: MinIO client
        """
        self.config = config
        self.postgres = postgres_client
        self.mongo = mongo_client
        self.minio = minio_client
        self.running = False
        self.current_workdir: Optional[str] = None
    
    def poll_loop(self):
        """Main polling loop that runs indefinitely."""
        self.running = True
        self.mongo.write_log(
            task_id=None,
            level="info",
            message=f"Agent worker started (agent_id={self.config.agent_id})"
        )
        print(f"[{self.config.agent_id}] Agent worker started")
        
        while self.running:
            try:
                # Poll for current task
                task = self.postgres.get_current_task()
                
                if not task:
                    # No task available, sleep and continue
                    print(f"[{self.config.agent_id}] No task found, polling again in {self.config.poll_interval_seconds}s...")
                    time.sleep(self.config.poll_interval_seconds)
                    continue
                
                task_id = task["id"]
                
                # Check progress
                progress = self.postgres.get_task_progress_max_percent(task_id)
                
                if progress >= 100:
                    # Task already completed, skip
                    time.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Task found and not completed, execute it
                self._execute_task(task)
                
            except Exception as e:
                # Log error and continue polling
                error_msg = f"Error in poll loop: {str(e)}"
                print(f"[{self.config.agent_id}] ERROR: {error_msg}")
                self.mongo.write_log(
                    task_id=None,
                    level="error",
                    message=error_msg,
                    meta={"exc_info": str(e)}
                )
                time.sleep(self.config.poll_interval_seconds)
        
        self.mongo.write_log(
            task_id=None,
            level="info",
            message="Agent worker stopped"
        )
        print(f"[{self.config.agent_id}] Agent worker stopped")
    
    def _execute_task(self, task: dict):
        """
        Execute a task by running run_task.py.
        
        Args:
            task: Task dictionary from database
        """
        task_id = task["id"]
        workdir = None
        original_cwd = os.getcwd()  # Save original working directory early
        
        try:
            # Create unique working directory
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            workdir = f"/tmp/agent_work/{self.config.agent_id}/{task_id}/{timestamp}"
            workdir_path = Path(workdir)
            workdir_path.mkdir(parents=True, exist_ok=True)
            self.current_workdir = workdir
            
            # Create screenshots directory
            screenshots_dir = workdir_path / "screenshots"
            screenshots_dir.mkdir(exist_ok=True)
            
            # Log task picked
            self.mongo.write_log(
                task_id=task_id,
                level="info",
                message=f"Task picked: {task.get('title', 'Unknown')}",
                meta={"task_id": task_id, "title": task.get("title")}
            )
            print(f"[{self.config.agent_id}] Task {task_id} picked: {task.get('title', 'Unknown')}")
            
            # Insert initial progress
            self.postgres.insert_progress(
                task_id=task_id,
                agent_id=self.config.agent_id,
                percent=0,
                message="Task started"
            )
            
            # Snapshot existing files in screenshots directory
            screenshots_before = set()
            if screenshots_dir.exists():
                screenshots_before = {f.name for f in screenshots_dir.iterdir() if f.is_file()}
            
            # Find run_task.py script
            
            # Look for run_task.py in various locations
            run_task_script = None
            possible_paths = [
                Path("run_task.py"),  # Current directory
                Path("../run_task.py"),  # Parent directory
                Path(__file__).parent.parent / "run_task.py",  # Agent directory
                Path(__file__).parent.parent.parent / "run_task.py",  # Project root
            ]
            
            for path in possible_paths:
                if path.exists() and path.is_file():
                    run_task_script = path.resolve()
                    break
            
            if not run_task_script:
                error_msg = "run_task.py not found in any expected location"
                print(f"[{self.config.agent_id}] ERROR: {error_msg}")
                self.mongo.write_log(
                    task_id=task_id,
                    level="error",
                    message=error_msg
                )
                self.postgres.insert_progress(
                    task_id=task_id,
                    agent_id=self.config.agent_id,
                    percent=0,
                    message=error_msg
                )
                return
            
            # Start heartbeat thread for progress updates
            heartbeat_stop = threading.Event()
            heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                args=(task_id, heartbeat_stop),
                daemon=True
            )
            heartbeat_thread.start()
            
            # Get task description
            task_description = task.get("description", "") or task.get("title", "")
            if not task_description:
                task_description = f"Task {task_id}"
            
            # Execute task using execute_task.py script
            # First, try to find execute_task.py in the agent_worker directory
            execute_task_script = Path(__file__).parent / "execute_task.py"
            if not execute_task_script.exists():
                # Fallback to run_task.py if execute_task.py doesn't exist
                execute_task_script = run_task_script
            
            start_time = time.time()
            try:
                # Pass task description as environment variable or argument
                env = os.environ.copy()
                env["TASK_DESCRIPTION"] = task_description
                
                result = subprocess.run(
                    ["python", str(execute_task_script), task_description],
                    cwd=str(workdir_path),
                    capture_output=True,
                    text=True,
                    timeout=self.config.run_task_timeout_seconds,
                    env=env
                )
                end_time = time.time()
                duration = end_time - start_time
                
                # Stop heartbeat
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)
                
                # Get stdout and stderr
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                return_code = result.returncode
                
                # Log execution result
                self.mongo.write_log(
                    task_id=task_id,
                    level="info" if return_code == 0 else "error",
                    message=f"run_task.py completed (return_code={return_code}, duration={duration:.2f}s)",
                    meta={
                        "return_code": return_code,
                        "duration": duration,
                        "stdout_length": len(stdout),
                        "stderr_length": len(stderr)
                    }
                )
                
                # Write full stdout/stderr to logs
                if stdout:
                    self.mongo.write_log(
                        task_id=task_id,
                        level="info",
                        message="run_task.py stdout",
                        meta={"stdout": stdout}
                    )
                if stderr:
                    self.mongo.write_log(
                        task_id=task_id,
                        level="warning" if return_code == 0 else "error",
                        message="run_task.py stderr",
                        meta={"stderr": stderr}
                    )
                
                # Detect newly created screenshots
                screenshots_after = set()
                if screenshots_dir.exists():
                    screenshots_after = {f.name for f in screenshots_dir.iterdir() if f.is_file()}
                
                new_screenshots = list_new_screenshots(screenshots_before, screenshots_after)
                
                # Upload new screenshots
                uploaded_paths = []
                for filename in new_screenshots:
                    try:
                        screenshot_path = screenshots_dir / filename
                        
                        # Check if file exists and has content
                        if not screenshot_path.exists():
                            print(f"[{self.config.agent_id}] WARNING: Screenshot file not found: {screenshot_path}")
                            continue
                        
                        file_size = screenshot_path.stat().st_size
                        if file_size == 0:
                            print(f"[{self.config.agent_id}] WARNING: Screenshot file is empty: {screenshot_path}")
                            continue
                        
                        print(f"[{self.config.agent_id}] Uploading screenshot: {filename} ({file_size} bytes)")
                        object_path = self.minio.upload_file(str(screenshot_path))
                        uploaded_paths.append(object_path)
                        
                        # Verify upload by checking if object exists in MinIO
                        try:
                            # Try to stat the object to verify it exists
                            from minio import Minio
                            minio_client = self.minio.client
                            stat = minio_client.stat_object("screenshots", object_path)
                            print(f"[{self.config.agent_id}] Verified screenshot in MinIO: {object_path} ({stat.size} bytes)")
                        except Exception as verify_error:
                            print(f"[{self.config.agent_id}] WARNING: Could not verify screenshot in MinIO: {verify_error}")
                        
                        # Log upload
                        self.mongo.write_log(
                            task_id=task_id,
                            level="info",
                            message=f"Screenshot uploaded: {object_path}",
                            meta={"filename": filename, "object_path": object_path, "file_size": file_size}
                        )
                        print(f"[{self.config.agent_id}] Uploaded screenshot: {object_path}")
                        
                        # Insert progress update for upload
                        self.postgres.insert_progress(
                            task_id=task_id,
                            agent_id=self.config.agent_id,
                            percent=None,
                            message=f"uploaded screenshot: {object_path}"
                        )
                    except Exception as e:
                        error_msg = f"Failed to upload screenshot {filename}: {str(e)}"
                        print(f"[{self.config.agent_id}] ERROR: {error_msg}")
                        import traceback
                        traceback.print_exc()
                        self.mongo.write_log(
                            task_id=task_id,
                            level="error",
                            message=error_msg,
                            meta={"filename": filename, "exc_info": str(e)}
                        )
                
                # Determine final progress percent
                # If return_code is 0, set to 100; otherwise use heuristics
                if return_code == 0:
                    final_percent = 100
                else:
                    # Heuristic: if we uploaded screenshots, consider it partial success
                    final_percent = 50 if uploaded_paths else 0
                
                # Insert final progress
                self.postgres.insert_progress(
                    task_id=task_id,
                    agent_id=self.config.agent_id,
                    percent=final_percent,
                    message=f"completed (return_code={return_code}, screenshots={len(uploaded_paths)})"
                )
                
                # Update task response
                # Extract agent response from stdout (between AGENT_RESPONSE_START and AGENT_RESPONSE_END markers)
                response_text = ""
                if "AGENT_RESPONSE_START" in stdout and "AGENT_RESPONSE_END" in stdout:
                    # Extract response between markers
                    start_idx = stdout.find("AGENT_RESPONSE_START")
                    end_idx = stdout.find("AGENT_RESPONSE_END")
                    if start_idx != -1 and end_idx != -1:
                        # Get content between markers
                        response_section = stdout[start_idx:end_idx]
                        # Extract lines between the markers (skip the marker lines themselves)
                        lines = response_section.split('\n')
                        response_lines = []
                        in_response = False
                        separator = "=" * 60
                        for line in lines:
                            if "AGENT_RESPONSE_START" in line or separator in line:
                                in_response = True
                                continue
                            if "AGENT_RESPONSE_END" in line:
                                break
                            if in_response and line.strip() and separator not in line:
                                response_lines.append(line)
                        response_text = '\n'.join(response_lines).strip()
                
                # Fallback: use entire stdout if markers not found
                if not response_text:
                    response_text = stdout.strip()
                
                # Final fallback: use summary if stdout is empty
                if not response_text:
                    response_text = f"Task completed (return_code={return_code}, duration={duration:.2f}s, screenshots={len(uploaded_paths)})"
                
                # Update task status to completed
                try:
                    self.postgres.update_task_status(
                        task_id=task_id,
                        status="completed" if return_code == 0 else "failed",
                        metadata={"completed_at": datetime.utcnow().isoformat(), "return_code": return_code, "screenshots": len(uploaded_paths)}
                    )
                except Exception as e:
                    print(f"[{self.config.agent_id}] Warning: Failed to update task status: {e}")
                
                # Update task response (wrap in try/except to handle transaction errors gracefully)
                try:
                    self.postgres.update_task_response(
                        task_id=task_id,
                        agent_id=self.config.agent_id,
                        response_text=response_text
                    )
                except Exception as e:
                    # Log error but don't fail the task execution
                    print(f"[{self.config.agent_id}] Warning: Failed to update task response: {e}")
                    self.mongo.write_log(
                        task_id=task_id,
                        level="warning",
                        message=f"Failed to update task response: {str(e)}"
                    )
                
                # Insert final 100% progress if not already
                if final_percent < 100:
                    self.postgres.insert_progress(
                        task_id=task_id,
                        agent_id=self.config.agent_id,
                        percent=100,
                        message="completed"
                    )
                
                print(f"[{self.config.agent_id}] Task {task_id} completed (return_code={return_code})")
                
            except subprocess.TimeoutExpired:
                # Task timed out
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)
                
                error_msg = f"run_task.py timed out after {self.config.run_task_timeout_seconds} seconds"
                print(f"[{self.config.agent_id}] ERROR: {error_msg}")
                self.mongo.write_log(
                    task_id=task_id,
                    level="error",
                    message=error_msg
                )
                
                self.postgres.insert_progress(
                    task_id=task_id,
                    agent_id=self.config.agent_id,
                    percent=0,
                    message=error_msg
                )
                
                # Update task status to failed
                try:
                    self.postgres.update_task_status(
                        task_id=task_id,
                        status="failed",
                        metadata={"failed_at": datetime.utcnow().isoformat(), "error": error_msg}
                    )
                except Exception as e:
                    print(f"[{self.config.agent_id}] Warning: Failed to update task status: {e}")
                
                # Update task response (wrap in try/except to handle transaction errors gracefully)
                try:
                    self.postgres.update_task_response(
                        task_id=task_id,
                        agent_id=self.config.agent_id,
                        response_text=error_msg
                    )
                except Exception as e:
                    # Log error but don't fail the task execution
                    print(f"[{self.config.agent_id}] Warning: Failed to update task response: {e}")
            
            finally:
                # Restore original working directory
                try:
                    os.chdir(original_cwd)
                except:
                    pass
        
        except Exception as e:
            # Log error
            error_msg = f"Error executing task {task_id}: {str(e)}"
            print(f"[{self.config.agent_id}] ERROR: {error_msg}")
            self.mongo.write_log(
                task_id=task_id,
                level="error",
                message=error_msg,
                meta={"exc_info": str(e)}
            )
            
            # Insert error progress
            try:
                self.postgres.insert_progress(
                    task_id=task_id,
                    agent_id=self.config.agent_id,
                    percent=0,
                    message=error_msg
                )
            except:
                pass
            
            # Update task status to failed
            try:
                self.postgres.update_task_status(
                    task_id=task_id,
                    status="failed",
                    metadata={"failed_at": datetime.utcnow().isoformat(), "error": error_msg}
                )
            except:
                pass
        
        finally:
            # Cleanup workdir
            if workdir and os.path.exists(workdir):
                try:
                    shutil.rmtree(workdir)
                except Exception as e:
                    print(f"[{self.config.agent_id}] Warning: Failed to cleanup workdir {workdir}: {e}")
            self.current_workdir = None
    
    def _heartbeat_loop(self, task_id: int, stop_event: threading.Event):
        """
        Heartbeat loop that writes progress updates while task is running.
        
        Args:
            task_id: Task identifier
            stop_event: Event to stop the heartbeat
        """
        while not stop_event.is_set():
            try:
                self.postgres.insert_progress(
                    task_id=task_id,
                    agent_id=self.config.agent_id,
                    percent=None,
                    message="working..."
                )
            except:
                pass  # Ignore errors in heartbeat
            
            # Sleep for poll interval, or until stop event
            if stop_event.wait(self.config.poll_interval_seconds):
                break
    
    def stop(self):
        """Stop the polling loop gracefully."""
        self.running = False

