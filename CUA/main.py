import asyncio
import logging
import os
import traceback
import signal

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