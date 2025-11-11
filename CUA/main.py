import asyncio
import logging
import os
import traceback
import signal
from datetime import datetime

from computer import Computer, VMProviderType

# Import the unified agent class and types
from agent import ComputerAgent

# Import utility functions
from utils import load_dotenv_files, handle_sigint

# Import storage integration (optional)
try:
    from storage_integration import execute_task_with_storage, initialize_storage_adapters
    STORAGE_INTEGRATION_AVAILABLE = True
except ImportError:
    STORAGE_INTEGRATION_AVAILABLE = False
    print("Note: Storage integration not available (storage adapters not found)")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_required_env_vars():
    """Validate that all required environment variables are present.

    Raises:
        ValueError: If any required environment variables are missing.
    """
    required_keys = [
        "CUA_API_KEY",
        "CUA_SANDBOX_NAME",
        "OPENAI_API_KEY"
    ]

    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_keys)}. "
            f"Please check your .env file and ensure all keys from .env.example are set."
        )


async def _poll_and_process_tasks(agent, storage_adapters: dict, agent_id: str, poll_interval: float = 5.0):
    """
    Poll Postgres for tasks assigned to this agent and process them.
    - Expects pg adapter methods: get_tasks(agent_id=..., status=..., limit=...), update_task_status(...), add_progress_update(...)
    - Expects mongo adapter method: write_log(level, message, task_id, metadata)
    """
    pg_adapter = storage_adapters.get("pg") if storage_adapters else None
    mongo_adapter = storage_adapters.get("mongo") if storage_adapters else None
    minio_adapter = storage_adapters.get("minio") if storage_adapters else None

    if not pg_adapter:
        print("⚠️  Poller disabled: Postgres adapter not available")
        return

    print(f"🔁 Starting task poller for agent '{agent_id}', interval={poll_interval}s")
    while True:
        try:
            # Fetch tasks assigned to this agent that are pending/assigned
            tasks = []
            try:
                tasks = pg_adapter.get_tasks(agent_id=agent_id, status="assigned", limit=10) or []
            except Exception:
                # fallback: try pending
                try:
                    tasks = pg_adapter.get_tasks(agent_id=agent_id, status="pending", limit=10) or []
                except Exception:
                    tasks = []

            for t in tasks:
                # Normalize task id and description
                task_id = t.get("id") or t.get("task_id") or t.get("taskId") or t.get("_id")
                description = t.get("description") or t.get("title") or ""
                if not task_id or not description:
                    continue

                # Avoid double-processing: check status again
                current = pg_adapter.get_task(task_id) if hasattr(pg_adapter, "get_task") else None
                cur_status = (current.get("status") if current else t.get("status")) or ""
                if cur_status in ("in_progress", "completed"):
                    continue

                # Mark as in_progress
                try:
                    pg_adapter.update_task_status(
                        task_id=task_id,
                        status="in_progress",
                        metadata={"started_at": datetime.utcnow().isoformat(), "agent_id": agent_id}
                    )
                except Exception as e:
                    print(f"⚠️  Failed to mark task {task_id} in_progress: {e}")

                # Add a progress update
                try:
                    pg_adapter.add_progress_update(
                        task_id=task_id,
                        agent_id=agent_id,
                        progress_percent=1,
                        message="Agent picked up task",
                        data={"description": description}
                    )
                except Exception:
                    pass

                # Run the agent on the task (message-based history)
                history = [{"role": "user", "content": description}]
                collected_texts = []
                try:
                    async for result in agent.run(history, stream=False):
                        output_items = result.get("output", []) or []
                        # Process outputs and log them
                        for item in output_items:
                            itype = item.get("type", "")
                            if itype == "message":
                                content_parts = item.get("content", []) or []
                                for cp in content_parts:
                                    text = cp.get("text") if isinstance(cp, dict) else None
                                    if text:
                                        collected_texts.append(text)
                                        # Log message to MongoDB if available
                                        try:
                                            if mongo_adapter:
                                                mongo_adapter.write_log(
                                                    level="info",
                                                    message=text[:1000],
                                                    task_id=str(task_id),
                                                    metadata={"agent_id": agent_id, "output_type": "message"}
                                                )
                                        except Exception:
                                            pass
                            elif itype == "computer_call" and mongo_adapter:
                                # store a short log about the action
                                try:
                                    mongo_adapter.write_log(
                                        level="info",
                                        message=f"computer_call: {item.get('action', {}).get('type', '')}"[:1000],
                                        task_id=str(task_id),
                                        metadata={"agent_id": agent_id, "action": item.get("action", {})}
                                    )
                                except Exception:
                                    pass

                        # Periodic progress update
                        try:
                            pg_adapter.add_progress_update(
                                task_id=task_id,
                                agent_id=agent_id,
                                progress_percent=50,
                                message="Agent produced partial output",
                                data={"partial_outputs": len(collected_texts)}
                            )
                        except Exception:
                            pass

                    # After streaming completes, assemble final response
                    final_response = "\n\n".join(collected_texts).strip() if collected_texts else "(no textual output)"
                except Exception as e:
                    # Mark failed and log
                    final_response = None
                    err_text = str(e)
                    try:
                        pg_adapter.update_task_status(
                            task_id=task_id,
                            status="failed",
                            metadata={"error": err_text, "failed_at": datetime.utcnow().isoformat(), "agent_id": agent_id}
                        )
                        pg_adapter.add_progress_update(
                            task_id=task_id,
                            agent_id=agent_id,
                            progress_percent=100,
                            message=f"Task failed: {err_text}",
                            data={"error": err_text}
                        )
                        if mongo_adapter:
                            mongo_adapter.write_log(level="error", message=f"Task failed: {err_text}", task_id=str(task_id), metadata={"agent_id": agent_id})
                    except Exception:
                        pass
                    print(f"❌ Error executing task {task_id}: {err_text}")
                    continue

                # Persist final result and mark completed
                try:
                    result_meta = {
                        "response_text": final_response,
                        "completed_at": datetime.utcnow().isoformat(),
                        "agent_id": agent_id,
                        "processing_method": "cua_agent_poll"
                    }
                    pg_adapter.update_task_status(
                        task_id=task_id,
                        status="completed",
                        metadata={"result": result_meta, "completed_at": result_meta["completed_at"]}
                    )
                    pg_adapter.add_progress_update(
                        task_id=task_id,
                        agent_id=agent_id,
                        progress_percent=100,
                        message="Task completed",
                        data={"result": result_meta}
                    )
                    if mongo_adapter:
                        mongo_adapter.write_log(level="info", message=f"Task completed: {final_response[:1000]}", task_id=str(task_id), metadata={"agent_id": agent_id})
                except Exception as e:
                    print(f"⚠️  Failed to persist completion for task {task_id}: {e}")

        except Exception as e:
            print(f"⚠️  Poller error: {e}")
        await asyncio.sleep(poll_interval)


async def run_agent_example():
    """Run example of using the ComputerAgent with different models."""
    print("\n=== Example: ComputerAgent with different models ===")

    try:
        # Create a remote Linux computer with Cua
        computer = Computer(
            os_type="linux",
            api_key=os.getenv("CUA_API_KEY"),
            name=os.getenv("CUA_SANDBOX_NAME"),
            provider_type=VMProviderType.CLOUD,
        )

        # Create ComputerAgent with OpenAI CUA
        # If you wish to change the model, please refer to the following documentation: https://docs.cua.ai/docs/agent-sdk/supported-model-providers
        agent = ComputerAgent(
            model="omniparser+openai/gpt-4o",
            tools=[computer],
            only_n_most_recent_images=3,
            verbosity=logging.DEBUG,
            trajectory_dir="trajectories",
            use_prompt_caching=True,
            max_trajectory_budget=1.0,
        )

        # Example tasks to demonstrate the agent
        tasks = [
              "how tall is the empire state building?"
          ]

        # Initialize storage adapters if available
        storage_adapters = None
        agent_id = os.getenv("AGENT_ID", "cua_agent")
        
        if STORAGE_INTEGRATION_AVAILABLE:
            storage_adapters = initialize_storage_adapters(agent_id=agent_id)
            if any(storage_adapters.values()):
                print(f"\n✓ Storage integration enabled (agent_id: {agent_id})")
                if storage_adapters["mongo"]:
                    print("  - MongoDB logging: enabled")
                if storage_adapters["pg"]:
                    print("  - PostgreSQL task tracking: enabled")
                if storage_adapters["minio"]:
                    print("  - MinIO screenshot storage: enabled")
            else:
                print("\n⚠ Storage adapters not configured (set MONGODB_URL, POSTGRES_URL, MINIO_ENDPOINT)")
                storage_adapters = None
        else:
            print("\n⚠ Storage integration not available")
        
        # Start background poller only when Postgres adapter exists
        if storage_adapters and storage_adapters.get("pg"):
            # spawn the poller but don't block the example main flow
            asyncio.create_task(_poll_and_process_tasks(agent, storage_adapters, agent_id, poll_interval=float(os.getenv("TASK_POLL_INTERVAL", "5.0"))))
            print("🔁 Task poller started in background")

        # Use message-based conversation history
        history = []
        
        for i, task in enumerate(tasks):
            print(f"\nExecuting task {i+1}/{len(tasks)}: {task}")
            
            # Execute with storage integration if available
            if storage_adapters and any(storage_adapters.values()):
                try:
                    result = await execute_task_with_storage(
                        task_text=task,
                        agent=agent,
                        history=history,
                        mongo_adapter=storage_adapters["mongo"],
                        pg_adapter=storage_adapters["pg"],
                        minio_adapter=storage_adapters["minio"],
                        agent_id=agent_id
                    )
                    
                    # Update history from result
                    history = result.get("history", history)
                    
                    print(f"✅ Task {i+1}/{len(tasks)} completed: {task}")
                    if result.get("task_id"):
                        print(f"  Task ID: {result.get('task_id')}")
                    print(f"  Logs written: {result.get('logs_written', 0)}")
                    print(f"  Screenshots uploaded: {result.get('screenshots_uploaded', 0)}")
                    print(f"  Progress updates: {result.get('progress_updates', 0)}")
                    
                except Exception as e:
                    logger.error(f"Error executing task with storage: {e}")
                    traceback.print_exc()
                    raise
            else:
                # Fallback to original execution without storage
                # Add user message to history
                history.append({"role": "user", "content": task})
                
                # Run agent with conversation history
                async for result in agent.run(history, stream=False):
                    # Add agent outputs to history
                    history += result.get("output", [])
                    
                    # Print output for debugging
                    for item in result.get("output", []):
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            for content_part in content:
                                if content_part.get("text"):
                                    print(f"Agent: {content_part.get('text')}")
                        elif item.get("type") == "computer_call":
                            action = item.get("action", {})
                            action_type = action.get("type", "")
                            print(f"Computer Action: {action_type}({action})")
                        elif item.get("type") == "computer_call_output":
                            print("Computer Output: [Screenshot/Result]")
                            
                print(f"✅ Task {i+1}/{len(tasks)} completed: {task}")

    except Exception as e:
        logger.error(f"Error in run_agent_example: {e}")
        traceback.print_exc()
        raise


def main():
    """Run the ComputerAgent example with OpenAI CUA and Cloud VM."""
    try:
        load_dotenv_files()

        # Validate all required environment variables are present
        validate_required_env_vars()

        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, handle_sigint)

        asyncio.run(run_agent_example())
    except Exception as e:
        print(f"Error running example: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()