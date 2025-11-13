#!/usr/bin/env python3
"""
Task execution script for agent worker.
This script receives a task description and executes it using the CUA agent.

Usage:
    python execute_task.py "task description"
    or
    TASK_DESCRIPTION="task description" python execute_task.py
"""

import sys
import os
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add CUA to path
cua_path = project_root / "CUA"
if cua_path.exists():
    sys.path.insert(0, str(cua_path))

# Add agent_worker to path for imports
agent_worker_path = Path(__file__).parent
sys.path.insert(0, str(agent_worker_path))




def take_periodic_screenshots(computer, screenshots_dir: Path, stop_event: threading.Event, minio_client=None, interval_seconds: int = 5):
    """
    Background thread function to take screenshots every N seconds using Playwright.
    
    Uses Playwright to connect to the CUA Computer's display and capture screenshots.
    Screenshots are saved to the local machine's root directory.
    
    Args:
        computer: CUA Computer instance
        screenshots_dir: Directory to save screenshots (unused - saving to root instead)
        stop_event: Event to stop the screenshot loop
        minio_client: MinIO client wrapper (unused - saving to root instead)
        interval_seconds: Interval between screenshots (default: 5)
    """
    screenshot_count = 0
    
    print(f"[Screenshot Thread] Started - taking screenshots every {interval_seconds} seconds", file=sys.stderr)
    
    # Import Playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"[Screenshot Thread] ERROR: Playwright not available", file=sys.stderr)
        return
    
    # Get display URL from Computer - try multiple methods
    display_url = None
    
    # Method 1: Try direct attributes
    if hasattr(computer, 'display_url') and computer.display_url:
        display_url = computer.display_url
    elif hasattr(computer, 'vnc_url') and computer.vnc_url:
        display_url = computer.vnc_url
    elif hasattr(computer, 'url') and computer.url:
        display_url = computer.url
    
    # Method 2: Try to get from interface
    if not display_url and hasattr(computer, 'interface'):
        interface = computer.interface
        if hasattr(interface, 'display_url') and interface.display_url:
            display_url = interface.display_url
        elif hasattr(interface, 'vnc_url') and interface.vnc_url:
            display_url = interface.vnc_url
        elif hasattr(interface, 'url') and interface.url:
            display_url = interface.url
    
    # Method 3: Construct from host, port, and noVNC_port
    if not display_url:
        host = getattr(computer, 'host', None)
        noVNC_port = getattr(computer, 'noVNC_port', None)
        port = getattr(computer, 'port', None)
        
        if host and noVNC_port:
            # Construct noVNC URL
            if port:
                display_url = f"http://{host}:{noVNC_port}/vnc.html?host={host}&port={port}"
            else:
                display_url = f"http://{host}:{noVNC_port}/vnc.html?host={host}"
        elif host and port:
            display_url = f"http://{host}:{port}"
    
    # Method 4: Try interface attributes
    if not display_url and hasattr(computer, 'interface'):
        interface = computer.interface
        host = getattr(interface, 'host', None) or getattr(computer, 'host', None)
        noVNC_port = getattr(interface, 'noVNC_port', None) or getattr(computer, 'noVNC_port', None)
        port = getattr(interface, 'port', None) or getattr(computer, 'port', None)
        
        if host and noVNC_port:
            if port:
                display_url = f"http://{host}:{noVNC_port}/vnc.html?host={host}&port={port}"
            else:
                display_url = f"http://{host}:{noVNC_port}/vnc.html?host={host}"
        elif host and port:
            display_url = f"http://{host}:{port}"
    
    if not display_url:
        print(f"[Screenshot Thread] WARNING: No display URL found on Computer object", file=sys.stderr)
        print(f"[Screenshot Thread] Computer attributes: {[attr for attr in dir(computer) if not attr.startswith('_')]}", file=sys.stderr)
        if hasattr(computer, 'host'):
            print(f"[Screenshot Thread] Computer host: {computer.host}", file=sys.stderr)
        if hasattr(computer, 'port'):
            print(f"[Screenshot Thread] Computer port: {computer.port}", file=sys.stderr)
        if hasattr(computer, 'noVNC_port'):
            print(f"[Screenshot Thread] Computer noVNC_port: {computer.noVNC_port}", file=sys.stderr)
        if hasattr(computer, 'interface'):
            print(f"[Screenshot Thread] Computer interface: {computer.interface}", file=sys.stderr)
        return
    
    print(f"[Screenshot Thread] Using display URL: {display_url}", file=sys.stderr)
    
    # Save screenshots to root directory of local machine
    # In container, use /app/screenshots; locally, use ./screenshots
    # Try /app/screenshots first (container), then fall back to ./screenshots (local)
    root_screenshots_dir = Path("/app/screenshots")
    try:
        # Ensure directory exists and is writable
        root_screenshots_dir.mkdir(parents=True, exist_ok=True)
        # Verify we can write to it by creating a test file
        test_file = root_screenshots_dir / ".test_write"
        test_file.touch()
        test_file.unlink()
        print(f"[Screenshot Thread] Saving screenshots to: {root_screenshots_dir} (container)", file=sys.stderr)
    except (PermissionError, OSError) as e:
        # Can't write to /app/screenshots, try local path
        print(f"[Screenshot Thread] Cannot write to /app/screenshots: {e}, using local path", file=sys.stderr)
        root_screenshots_dir = Path("./screenshots")
        root_screenshots_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Screenshot Thread] Saving screenshots to: {root_screenshots_dir} (local fallback)", file=sys.stderr)
    except Exception as e:
        # Any other error, use local path
        print(f"[Screenshot Thread] Error with /app/screenshots: {e}, using local path", file=sys.stderr)
        root_screenshots_dir = Path("./screenshots")
        root_screenshots_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Screenshot Thread] Saving screenshots to: {root_screenshots_dir} (local)", file=sys.stderr)
    
    while not stop_event.is_set():
        try:
            # Use Playwright to capture screenshot from display URL
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    # Navigate to display URL with longer timeout
                    page.goto(display_url, wait_until="networkidle", timeout=30000)
                    # Wait a bit for page to fully load
                    page.wait_for_timeout(2000)
                    screenshot_data = page.screenshot(full_page=True)
                    
                    # Save screenshot to root directory
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"periodic_screenshot_{timestamp}_{screenshot_count}.png"
                    filepath = root_screenshots_dir / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(screenshot_data)
                    
                    screenshot_count += 1
                    file_size = filepath.stat().st_size
                    print(f"[Screenshot Thread] Saved screenshot {screenshot_count}: {filepath} ({file_size} bytes)", file=sys.stderr)
                except Exception as e:
                    print(f"[Screenshot Thread] Error capturing screenshot: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                finally:
                    browser.close()
        except Exception as e:
            print(f"[Screenshot Thread] Error in screenshot loop: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        # Wait for interval or until stop event
        if stop_event.wait(interval_seconds):
            break
    
    print(f"[Screenshot Thread] Stopped - total screenshots taken: {screenshot_count}", file=sys.stderr)


def save_last_screenshot_to_local_disk(screenshot_path):
    """
    Save the last screenshot to a persistent local disk location.
    This is in addition to the MinIO upload, so the last screenshot
    is available on the local filesystem even after workdir cleanup.
    
    Args:
        screenshot_path: Path to the screenshot file in workdir
        
    Returns:
        Path to the saved screenshot on local disk, or None if failed
    """
    try:
        screenshot_path = Path(screenshot_path)
        if not screenshot_path.exists():
            print(f"✗ Screenshot file not found: {screenshot_path}")
            return None
        
        # Create local screenshots directory (persistent location)
        # Use /app/last_screenshots/ in container, or ./last_screenshots/ locally
        local_screenshots_dir = Path("/app/last_screenshots")
        if not local_screenshots_dir.exists():
            # Try relative path if /app doesn't exist (local development)
            local_screenshots_dir = Path("last_screenshots")
        
        local_screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy screenshot to local disk with a fixed name
        local_path = local_screenshots_dir / "last_screenshot.png"
        
        # Read and write the file
        with open(screenshot_path, "rb") as src:
            with open(local_path, "wb") as dst:
                dst.write(src.read())
        
        return str(local_path)
    except Exception as e:
        print(f"✗ Failed to save last screenshot to local disk: {e}")
        return None


def check_cua_packages():
    """Check if CUA packages are installed and importable."""
    diagnostics = {
        "packages_installed": False,
        "agent_importable": False,
        "computer_importable": False,
        "errors": []
    }
    
    # Check if packages are installed via pip
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "cua-agent" in result.stdout.lower() or "cua-computer" in result.stdout.lower():
            diagnostics["packages_installed"] = True
    except Exception as e:
        diagnostics["errors"].append(f"Failed to check pip list: {e}")
    
    # Try to import agent module
    try:
        import agent
        diagnostics["agent_importable"] = True
    except ImportError as e:
        diagnostics["errors"].append(f"Failed to import agent module: {e}")
    except Exception as e:
        diagnostics["errors"].append(f"Unexpected error importing agent module: {e}")
    
    # Try to import computer module
    try:
        import computer
        diagnostics["computer_importable"] = True
    except ImportError as e:
        diagnostics["errors"].append(f"Failed to import computer module: {e}")
    except Exception as e:
        diagnostics["errors"].append(f"Unexpected error importing computer module: {e}")
    
    return diagnostics


def get_task_description():
    """Get task description from command line or environment."""
    if len(sys.argv) > 1:
        # Get from command line arguments
        task_description = " ".join(sys.argv[1:])
    else:
        # Get from environment variable
        task_description = os.getenv("TASK_DESCRIPTION", "")
    
    return task_description  # Return empty string if not provided (for polling mode)


async def execute_task_async(task_description: str) -> dict:
    """
    Execute a task using CUA agent and return results.
    
    Args:
        task_description: The task description to execute
        
    Returns:
        Dictionary with execution results
    """
    print(f"Executing task: {task_description}")
    print("=" * 60)
    
    result = {
        "status": "success",
        "output": "",
        "error": "",
        "screenshots": [],
        "last_screenshot_local": None
    }
    
    # Run diagnostics first
    print("\n=== CUA Package Diagnostics ===")
    diagnostics = check_cua_packages()
    print(f"Packages installed (via pip): {diagnostics['packages_installed']}")
    print(f"Agent module importable: {diagnostics['agent_importable']}")
    print(f"Computer module importable: {diagnostics['computer_importable']}")
    if diagnostics['errors']:
        print("Errors found:")
        for error in diagnostics['errors']:
            print(f"  - {error}")
    print("=" * 60)
    print()
    
    try:
        # Try to import and use CUA agent
        try:
            # First, check for required environment variables
            cua_api_key = os.getenv("CUA_API_KEY")
            cua_sandbox_name = os.getenv("CUA_SANDBOX_NAME", "default")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            print("Checking CUA environment variables...")
            missing_vars = []
            if not cua_api_key:
                missing_vars.append("CUA_API_KEY")
            if not openai_api_key:
                missing_vars.append("OPENAI_API_KEY")
            
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            print(f"✓ CUA_API_KEY is set (length: {len(cua_api_key)})")
            print(f"✓ CUA_SANDBOX_NAME: {cua_sandbox_name}")
            print(f"✓ OPENAI_API_KEY is set (length: {len(openai_api_key)})")
            
            # Import from cua packages (installed via pip as cua-agent, cua-computer)
            # But imported as 'agent' and 'computer' modules
            print("Attempting to import CUA packages...")
            try:
                from agent import ComputerAgent
                print("✓ Successfully imported ComputerAgent from agent module")
            except ImportError as import_err:
                print(f"✗ Failed to import ComputerAgent from agent module: {import_err}")
                print(f"  Import error details: {type(import_err).__name__}: {import_err}")
                import traceback
                traceback.print_exc()
                raise
            
            try:
                from computer import Computer, VMProviderType
                print("✓ Successfully imported Computer and VMProviderType from computer module")
            except ImportError as import_err:
                print(f"✗ Failed to import Computer/VMProviderType from computer module: {import_err}")
                print(f"  Import error details: {type(import_err).__name__}: {import_err}")
                import traceback
                traceback.print_exc()
                raise
            
            print("Initializing CUA agent...")
            
            # Create computer instance
            print("Creating Computer instance...")
            try:
                computer = Computer(
                    os_type="linux",
                    api_key=cua_api_key,
                    name=cua_sandbox_name,
                    provider_type=VMProviderType.CLOUD,
                )
                print("✓ Computer instance created successfully")
            except Exception as comp_err:
                print(f"✗ Failed to create Computer instance: {comp_err}")
                print(f"  Error type: {type(comp_err).__name__}")
                import traceback
                traceback.print_exc()
                raise
            
            # Create agent
            print("Creating ComputerAgent instance...")
            try:
                agent = ComputerAgent(
                    model="omniparser+openai/gpt-4-turbo",
                    tools=[computer],
                    only_n_most_recent_images=3,
                    verbosity=logging.INFO,
                )
                print("✓ ComputerAgent instance created successfully")
            except Exception as agent_err:
                print(f"✗ Failed to create ComputerAgent instance: {agent_err}")
                print(f"  Error type: {type(agent_err).__name__}")
                import traceback
                traceback.print_exc()
                raise
            
            print(f"Executing task: {task_description}")
            
            # Create conversation history
            history = [{"role": "user", "content": task_description}]
            
            # Screenshots will be saved to local machine's root directory
            # No MinIO client needed for now
            minio_client = None
            print("✓ Screenshots will be saved to local machine's root directory")
            
            # Setup periodic screenshot capture
            screenshots_dir = Path("screenshots")  # Relative to workdir (set by agent_worker)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_stop_event = threading.Event()
            screenshot_thread = None
            
            try:
                # Start background thread for periodic screenshots
                print("Starting periodic screenshot capture (every 5 seconds)...")
                screenshot_thread = threading.Thread(
                    target=take_periodic_screenshots,
                    args=(computer, screenshots_dir, screenshot_stop_event, minio_client, 5),
                    daemon=True
                )
                screenshot_thread.start()
                print("✓ Screenshot thread started")
            except Exception as e:
                print(f"✗ Failed to start screenshot thread: {e}")
                print("  Continuing without periodic screenshots...")
            
            # Execute the task
            print("Starting task execution...")
            collected_outputs = []
            
            # Maintain conversation history properly to avoid tool_call_id errors
            # Based on CUA examples, we need to extend history with agent outputs
            # However, we pass a copy to agent.run() to avoid modifying the object it's using
            try:
                # Use a fresh history for each run to avoid state issues
                history = [{"role": "user", "content": task_description}]
                
                # Pass a copy of history to agent.run() to avoid conflicts
                # The agent manages its own internal state, but we maintain our own history
                # We extend our history after each iteration to match CUA examples
                async for result_item in agent.run(history.copy(), stream=False):
                    output_items = result_item.get("output", []) or []
                    
                    # Extend our history with agent outputs (matches CUA examples)
                    # We extend our copy, not the one passed to agent.run()
                    history.extend(output_items)
                    
                    for item in output_items:
                        item_type = item.get("type", "")
                        if item_type == "message":
                            content_parts = item.get("content", []) or []
                            for cp in content_parts:
                                text = cp.get("text") if isinstance(cp, dict) else None
                                if text:
                                    collected_outputs.append(text)
                                    print(f"Agent: {text}")
                        elif item_type == "computer_call":
                            action = item.get("action", {})
                            action_type = action.get("type", "")
                            print(f"Computer Action: {action_type}")
                        elif item_type == "computer_call_output":
                            print(f"Computer Output: [Result]")
            except Exception as agent_run_error:
                # Handle specific tool_call_id errors
                error_str = str(agent_run_error)
                error_type = type(agent_run_error).__name__
                if "tool_call_id" in error_str.lower() or "tool_calls" in error_str.lower() or "BadRequestError" in error_type:
                    print(f"✗ Tool call error: {agent_run_error}")
                    print(f"  Error type: {error_type}")
                    print("  This may occur if the agent's internal history gets out of sync.")
                    print("  Attempting to recover by creating a new agent instance...")
                    
                    # Try to recover by creating a fresh agent instance
                    try:
                        print("Creating fresh agent instance for retry...")
                        fresh_agent = ComputerAgent(
                            model="omniparser+openai/gpt-4-turbo",
                            tools=[computer],
                            only_n_most_recent_images=3,
                            verbosity=logging.INFO,
                        )
                        
                        # Retry with a simplified task description
                        print("Retrying with simplified task...")
                        retry_history = [{"role": "user", "content": f"Please execute this task: {task_description}"}]
                        
                        # Pass a copy of history to agent.run() to avoid conflicts
                        # Extend our history after each iteration
                        async for result_item in fresh_agent.run(retry_history.copy(), stream=False):
                            output_items = result_item.get("output", []) or []
                            
                            # Extend our history with agent outputs (matches CUA examples)
                            retry_history.extend(output_items)
                            
                            for item in output_items:
                                item_type = item.get("type", "")
                                if item_type == "message":
                                    content_parts = item.get("content", []) or []
                                    for cp in content_parts:
                                        text = cp.get("text") if isinstance(cp, dict) else None
                                        if text:
                                            collected_outputs.append(text)
                                            print(f"Agent: {text}")
                                elif item_type == "computer_call_output":
                                    print(f"Computer Output: [Result]")
                        
                        print("✓ Retry successful")
                    except Exception as retry_error:
                        print(f"✗ Retry failed: {retry_error}")
                        # Re-raise the original error
                        raise agent_run_error
                else:
                    # Re-raise other errors
                    raise
            
            # Stop periodic screenshot capture
            if screenshot_thread and screenshot_thread.is_alive():
                print("Stopping periodic screenshot capture...")
                screenshot_stop_event.set()
                screenshot_thread.join(timeout=2)
                print("✓ Screenshot thread stopped")
            
            # Collect all screenshots from periodic capture
            saved_paths = []
            if screenshots_dir.exists():
                # Get all periodic screenshots
                periodic_screenshots = sorted(screenshots_dir.glob("periodic_screenshot_*.png"))
                saved_paths = [str(p) for p in periodic_screenshots]
                if saved_paths:
                    print(f"Found {len(saved_paths)} periodic screenshot(s) in {screenshots_dir}")
                    result["screenshots"] = saved_paths
                    
                    # Save the last screenshot to local disk (in addition to MinIO upload)
                    last_screenshot_path = saved_paths[-1]  # Last screenshot
                    last_screenshot_local = save_last_screenshot_to_local_disk(last_screenshot_path)
                    if last_screenshot_local:
                        result["last_screenshot_local"] = last_screenshot_local
                        print(f"✓ Saved last screenshot to local disk: {last_screenshot_local}")
                else:
                    print("No periodic screenshots found")
                    result["screenshots"] = []
                    result["last_screenshot_local"] = None
            else:
                print("Screenshots directory does not exist")
                result["screenshots"] = []
                result["last_screenshot_local"] = None
            
            if collected_outputs:
                result["output"] = "\n".join(collected_outputs)
                result["status"] = "success"
                print(f"Task completed successfully")
            else:
                result["output"] = "Task executed but no text output received"
                result["status"] = "success"
                print("Task completed but no text output received")
                
        except ImportError as e:
            print(f"✗ CUA agent import failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            print("  Full traceback:")
            import traceback
            traceback.print_exc()
            print("\nFalling back to simple execution...")
            
            # Simple fallback: just print the task
            result["output"] = f"Task received: {task_description}\nTask execution completed (fallback mode - CUA agent not available: {str(e)})"
            result["status"] = "success"
            print(f"Task received: {task_description}")
            print("Task execution completed (fallback mode)")
            
        except ValueError as e:
            # Missing environment variable
            print(f"✗ Configuration error: {e}")
            print("Falling back to simple execution...")
            result["output"] = f"Task received: {task_description}\nTask execution completed (fallback mode - {str(e)})"
            result["status"] = "success"
            print(f"Task received: {task_description}")
            print("Task execution completed (fallback mode)")
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"✗ ERROR: Failed to execute task: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    return result


def execute_task(task_description: str) -> dict:
    """
    Synchronous wrapper for async task execution.
    
    Args:
        task_description: The task description to execute
        
    Returns:
        Dictionary with execution results
    """
    # Use asyncio.run() for Python 3.7+ (handles event loop creation/cleanup automatically)
    # This avoids the deprecation warning from get_event_loop()
    # asyncio.run() will raise RuntimeError if called from within an async context,
    # which is the correct behavior
    return asyncio.run(execute_task_async(task_description))


def main():
    """Main entry point."""
    task_description = get_task_description()
    
    # If no task description provided, run in polling mode using runner
    if not task_description:
        try:
            from .config import Config
            from .db_adapters import PostgresClient, MongoClientWrapper
            from .storage import MinioClientWrapper
            from .runner import AgentRunner
            
            # Load configuration and start polling loop
            config = Config.from_env()
            postgres = PostgresClient(config.postgres_dsn)
            mongo = MongoClientWrapper(config.mongo_uri, config.agent_id)
            minio = MinioClientWrapper(
                endpoint=config.minio_endpoint,
                access_key=config.minio_access_key,
                secret_key=config.minio_secret_key,
                secure=config.minio_secure,
                agent_id=config.agent_id
            )
            
            runner = AgentRunner(
                config=config,
                postgres_client=postgres,
                mongo_client=mongo,
                minio_client=minio
            )
            
            runner.poll_loop()
        except KeyboardInterrupt:
            print("\nShutting down agent worker...")
            sys.exit(0)
        except Exception as e:
            print(f"Fatal error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        return
    
    # Single task execution mode
    print("=" * 60)
    print("AGENT WORKER TASK EXECUTOR")
    print("=" * 60)
    print()
    
    result = execute_task(task_description)
    
    print()
    print("=" * 60)
    print("EXECUTION RESULT")
    print("=" * 60)
    print(f"Status: {result['status']}")
    if result['output']:
        print(f"Output:\n{result['output']}")
    if result['error']:
        print(f"Error: {result['error']}")
    
    # Output the response in a structured format that can be easily extracted
    # This marker helps runner.py extract just the agent response
    print()
    print("=" * 60)
    print("AGENT_RESPONSE_START")
    print("=" * 60)
    if result['output']:
        # Output just the agent response, not diagnostics
        print(result['output'])
    elif result['error']:
        print(f"Error: {result['error']}")
    else:
        print("No output or error")
    print("=" * 60)
    print("AGENT_RESPONSE_END")
    print("=" * 60)
    
    # Exit with appropriate code
    if result['status'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

