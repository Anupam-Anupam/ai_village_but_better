"""
Storage Integration for CUA Agent
==================================

Wraps CUA agent execution with storage adapters to automatically log
agent activity to MongoDB, PostgreSQL, and MinIO.
"""

import os
import sys
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

# Add parent directory to path to import storage adapters
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from storage import MongoAdapter, PostgresAdapter, MinIOAdapter
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    # Create dummy types for type hints when storage is not available
    MongoAdapter = None  # type: ignore
    PostgresAdapter = None  # type: ignore
    MinIOAdapter = None  # type: ignore


async def execute_task_with_storage(
    task_text: str,
    agent,
    history: List[Dict[str, Any]],
    mongo_adapter: Optional[Any] = None,
    pg_adapter: Optional[Any] = None,
    minio_adapter: Optional[Any] = None,
    agent_id: str = "cua_agent"
) -> Dict[str, Any]:
    """
    Execute a CUA agent task with automatic storage logging.
    
    Args:
        task_text: The task description/prompt
        agent: ComputerAgent instance
        history: Conversation history
        mongo_adapter: Optional MongoDB adapter for logging
        pg_adapter: Optional PostgreSQL adapter for task tracking
        minio_adapter: Optional MinIO adapter for screenshots
        agent_id: Agent identifier
        
    Returns:
        Dictionary with execution results and storage info
    """
    task_id = None
    screenshot_count = 0
    log_count = 0
    progress_count = 0
    
    # Create task record in PostgreSQL if adapter available
    if pg_adapter:
        try:
            task_id = pg_adapter.create_task(
                agent_id=agent_id,
                title=f"CUA Task: {task_text[:50]}...",
                description=task_text,
                status="in_progress",
                metadata={"source": "cua_agent", "task_type": "cua_execution"}
            )
            if mongo_adapter:
                mongo_adapter.write_log(
                    level="info",
                    message=f"Started task: {task_text}",
                    task_id=str(task_id),
                    metadata={"agent_id": agent_id, "task_text": task_text}
                )
                log_count += 1
        except Exception as e:
            print(f"Warning: Failed to create task in PostgreSQL: {e}")
    
    # Add user message to history
    history.append({"role": "user", "content": task_text})
    
    # Execute agent and capture results
    try:
        async for result in agent.run(history, stream=False):
            output_items = result.get("output", [])
            
            # Process each output item
            for item in output_items:
                item_type = item.get("type", "")
                
                # Log messages to MongoDB
                if item_type == "message" and mongo_adapter:
                    try:
                        content_parts = item.get("content", [])
                        for content_part in content_parts:
                            if content_part.get("text"):
                                mongo_adapter.write_log(
                                    level="info",
                                    message=content_part.get("text", "")[:500],
                                    task_id=str(task_id) if task_id else None,
                                    metadata={
                                        "agent_id": agent_id,
                                        "output_type": "message",
                                        "role": item.get("role", "assistant")
                                    }
                                )
                                log_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to log message to MongoDB: {e}")
                
                # Log computer calls
                elif item_type == "computer_call" and mongo_adapter:
                    try:
                        action = item.get("action", {})
                        action_type = action.get("type", "")
                        mongo_adapter.write_log(
                            level="info",
                            message=f"Computer action: {action_type}",
                            task_id=str(task_id) if task_id else None,
                            metadata={
                                "agent_id": agent_id,
                                "output_type": "computer_call",
                                "action": action_type,
                                "action_details": str(action)[:200]
                            }
                        )
                        log_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to log computer call: {e}")
                
                # Extract and store screenshots
                elif item_type == "computer_call_output" and minio_adapter:
                    try:
                        screenshots = _extract_images_from_output([item])
                        for screenshot_data in screenshots:
                            if screenshot_data:
                                object_path = minio_adapter.upload_screenshot(
                                    file_data=screenshot_data,
                                    task_id=task_id,
                                    metadata={
                                        "agent_id": agent_id,
                                        "source": "cua_agent",
                                        "output_type": "computer_call_output"
                                    }
                                )
                                screenshot_count += 1
                                
                                # Log screenshot upload
                                if mongo_adapter:
                                    mongo_adapter.write_log(
                                        level="info",
                                        message=f"Screenshot uploaded: {object_path}",
                                        task_id=str(task_id) if task_id else None,
                                        metadata={
                                            "agent_id": agent_id,
                                            "screenshot_path": object_path
                                        }
                                    )
                                    log_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to store screenshot: {e}")
                
                # Add to history
                history.append(item)
            
            # Update progress in PostgreSQL
            if pg_adapter and task_id:
                try:
                    # Calculate progress (rough estimate based on output items)
                    progress_percent = min(90, progress_count * 10)  # Rough estimate
                    progress_id = pg_adapter.add_progress_update(
                        task_id=task_id,
                        agent_id=agent_id,
                        progress_percent=progress_percent,
                        message=f"Processed {len(output_items)} output items",
                        data={"output_items_count": len(output_items)}
                    )
                    progress_count += 1
                except Exception as e:
                    print(f"Warning: Failed to update progress: {e}")
        
        # Mark task as completed
        if pg_adapter and task_id:
            try:
                pg_adapter.update_task_status(
                    task_id=task_id,
                    status="completed",
                    metadata={"completed_at": datetime.now(UTC).isoformat()}
                )
                
                # Final progress update
                pg_adapter.add_progress_update(
                    task_id=task_id,
                    agent_id=agent_id,
                    progress_percent=100.0,
                    message="Task completed",
                    data={"final": True}
                )
                progress_count += 1
                
                if mongo_adapter:
                    mongo_adapter.write_log(
                        level="info",
                        message=f"Task completed: {task_text}",
                        task_id=str(task_id),
                        metadata={"agent_id": agent_id, "status": "completed"}
                    )
                    log_count += 1
            except Exception as e:
                print(f"Warning: Failed to mark task as completed: {e}")
    
    except Exception as e:
        # Mark task as failed
        if pg_adapter and task_id:
            try:
                pg_adapter.update_task_status(task_id, "failed")
                if mongo_adapter:
                    mongo_adapter.write_log(
                        level="error",
                        message=f"Task failed: {str(e)}",
                        task_id=str(task_id),
                        metadata={"agent_id": agent_id, "error": str(e)}
                    )
                    log_count += 1
            except:
                pass
        raise
    
    return {
        "task_id": task_id,
        "logs_written": log_count,
        "screenshots_uploaded": screenshot_count,
        "progress_updates": progress_count,
        "history": history
    }


def _extract_images_from_output(output_items: List[Dict[str, Any]]) -> List[bytes]:
    """
    Extract base64-encoded images from agent output items.
    
    Args:
        output_items: List of output items from agent
        
    Returns:
        List of image bytes
    """
    images = []
    
    for item in output_items:
        if item.get("type") == "computer_call_output":
            content = item.get("content", [])
            for content_part in content:
                if isinstance(content_part, dict):
                    # Check for base64 image data
                    if content_part.get("type") == "image":
                        image_data = content_part.get("image")
                        if image_data:
                            # Could be base64 string or already bytes
                            try:
                                if isinstance(image_data, str):
                                    # Remove data URL prefix if present
                                    if "," in image_data:
                                        image_data = image_data.split(",", 1)[1]
                                    image_bytes = base64.b64decode(image_data)
                                    images.append(image_bytes)
                                elif isinstance(image_data, bytes):
                                    images.append(image_data)
                            except Exception as e:
                                print(f"Warning: Failed to decode image: {e}")
                    # Also check for screenshot_path or similar
                    elif "screenshot" in content_part or "image" in content_part:
                        # Try to extract base64 if present
                        for key in ["screenshot", "image", "image_data", "base64"]:
                            if key in content_part:
                                try:
                                    data = content_part[key]
                                    if isinstance(data, str) and "," in data:
                                        data = data.split(",", 1)[1]
                                    if isinstance(data, str):
                                        image_bytes = base64.b64decode(data)
                                        images.append(image_bytes)
                                except:
                                    pass
    
    return images


def initialize_storage_adapters(agent_id: str = "cua_agent") -> Dict[str, Any]:
    """
    Initialize storage adapters from environment variables.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Dictionary with adapters (or None if not available)
    """
    if not STORAGE_AVAILABLE:
        return {"mongo": None, "pg": None, "minio": None}
    
    adapters = {}
    
    # MongoDB adapter
    try:
        mongo_url = os.getenv("MONGODB_URL")
        if mongo_url:
            adapters["mongo"] = MongoAdapter(agent_id=agent_id, connection_string=mongo_url)
        else:
            adapters["mongo"] = None
    except Exception as e:
        print(f"Warning: Failed to initialize MongoDB adapter: {e}")
        adapters["mongo"] = None
    
    # PostgreSQL adapter
    try:
        pg_url = os.getenv("POSTGRES_URL")
        if pg_url:
            adapters["pg"] = PostgresAdapter(connection_string=pg_url)
        else:
            adapters["pg"] = None
    except Exception as e:
        print(f"Warning: Failed to initialize PostgreSQL adapter: {e}")
        adapters["pg"] = None
    
    # MinIO adapter (requires PostgreSQL for metadata)
    try:
        minio_endpoint = os.getenv("MINIO_ENDPOINT")
        if minio_endpoint and adapters["pg"]:
            adapters["minio"] = MinIOAdapter(
                agent_id=agent_id,
                postgres_adapter=adapters["pg"],
                endpoint=minio_endpoint
            )
        else:
            adapters["minio"] = None
    except Exception as e:
        print(f"Warning: Failed to initialize MinIO adapter: {e}")
        adapters["minio"] = None
    
    return adapters


def store_task(task_content: str, agent_id: str = "task_runner") -> Optional[int]:
    """
    Store a task from run_task.py into the database.
    
    Args:
        task_content: The task description/prompt
        agent_id: Agent identifier (default: "task_runner")
        
    Returns:
        Task ID if successful, None otherwise
    """
    if not STORAGE_AVAILABLE:
        return None
    
    try:
        # Initialize storage adapters
        adapters = initialize_storage_adapters(agent_id=agent_id)
        pg_adapter = adapters.get("pg")
        mongo_adapter = adapters.get("mongo")
        
        if not pg_adapter:
            return None
        
        # Create task in PostgreSQL
        task_id = pg_adapter.create_task(
            agent_id=agent_id,
            title=f"Task: {task_content[:50]}...",
            description=task_content,
            status="pending",
            metadata={"source": "run_task.py", "task_type": "cua_execution"}
        )
        
        # Log to MongoDB if available
        if mongo_adapter:
            try:
                mongo_adapter.write_log(
                    level="info",
                    message=f"Task created from run_task.py: {task_content}",
                    task_id=str(task_id),
                    metadata={"agent_id": agent_id, "task_text": task_content, "source": "run_task.py"}
                )
            except Exception as e:
                print(f"Warning: Failed to log to MongoDB: {e}")
        
        return task_id
    except Exception as e:
        print(f"Warning: Failed to store task in database: {e}")
        return None

