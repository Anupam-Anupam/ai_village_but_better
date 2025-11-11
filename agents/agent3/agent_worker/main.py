# Main entrypoint: sets up clients and starts the agent worker with graceful shutdown
"""Main entrypoint for agent worker."""

import signal
import sys
import os
from typing import Optional

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from .config import Config
from .db_adapters import PostgresClient, MongoClientWrapper
from .storage import MinioClientWrapper
from .runner import AgentRunner


class GracefulShutdown:
    """Handle graceful shutdown on SIGTERM."""
    
    def __init__(self, runner: AgentRunner):
        self.runner = runner
        self.shutdown_requested = False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signal."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.shutdown_requested = True
        self.runner.stop()


def main():
    """Main entrypoint for agent worker."""
    postgres_client = None
    mongo_client = None
    config = None
    
    try:
        # Load configuration
        config = Config.from_env()
        
        print(f"[{config.agent_id}] Starting agent worker...")
        print(f"[{config.agent_id}] Configuration:")
        print(f"  - PostgreSQL: {config.postgres_dsn[:50]}...")
        print(f"  - MongoDB: {config.mongo_uri[:50]}...")
        print(f"  - MinIO: {config.minio_endpoint}")
        print(f"  - Poll interval: {config.poll_interval_seconds}s")
        print(f"  - Task timeout: {config.run_task_timeout_seconds}s")
        
        # Initialize clients
        try:
            postgres_client = PostgresClient(config.postgres_dsn)
            print(f"[{config.agent_id}] Connected to PostgreSQL")
        except Exception as e:
            print(f"[{config.agent_id}] ERROR: Failed to connect to PostgreSQL: {e}")
            sys.exit(1)
        
        try:
            mongo_client = MongoClientWrapper(config.mongo_uri, config.agent_id)
            print(f"[{config.agent_id}] Connected to MongoDB")
        except Exception as e:
            print(f"[{config.agent_id}] ERROR: Failed to connect to MongoDB: {e}")
            if postgres_client:
                postgres_client.close()
            sys.exit(1)
        
        try:
            minio_client = MinioClientWrapper(
                config.minio_endpoint,
                config.minio_access_key,
                config.minio_secret_key,
                config.minio_secure,
                config.agent_id
            )
            print(f"[{config.agent_id}] Connected to MinIO")
        except Exception as e:
            print(f"[{config.agent_id}] ERROR: Failed to connect to MinIO: {e}")
            if postgres_client:
                postgres_client.close()
            if mongo_client:
                mongo_client.close()
            sys.exit(1)
        
        # Create runner
        runner = AgentRunner(
            config=config,
            postgres_client=postgres_client,
            mongo_client=mongo_client,
            minio_client=minio_client
        )
        
        # Setup graceful shutdown
        shutdown_handler = GracefulShutdown(runner)
        signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)
        signal.signal(signal.SIGINT, shutdown_handler.signal_handler)
        
        # Start polling loop
        try:
            runner.poll_loop()
        except KeyboardInterrupt:
            print(f"\n[{config.agent_id}] Interrupted by user")
            runner.stop()
        except Exception as e:
            print(f"[{config.agent_id}] ERROR: Fatal error in poll loop: {e}")
            runner.stop()
            raise
        
    except Exception as e:
        print(f"ERROR: Failed to start agent worker: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup
        if postgres_client:
            try:
                postgres_client.close()
            except:
                pass
        if mongo_client:
            try:
                mongo_client.close()
            except:
                pass
        if config:
            print(f"[{config.agent_id}] Agent worker stopped")
        else:
            print("Agent worker stopped")


if __name__ == "__main__":
    main()

