"""
Full CUA Agent Storage Integration Test
=======================================

Tests end-to-end: Executes a CUA agent task and verifies that logs,
progress, and screenshots appear in MongoDB, PostgreSQL, and MinIO.
"""

import os
import sys
import time
import asyncio
from datetime import datetime, UTC

# Add storage directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'storage'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'CUA'))

from storage import MongoAdapter, PostgresAdapter, MinIOAdapter

# CUA imports (will fail gracefully if CUA SDK not available)
try:
    from computer import Computer, VMProviderType
    from agent import ComputerAgent
    from CUA.storage_integration import execute_task_with_storage, initialize_storage_adapters
    CUA_AVAILABLE = True
except ImportError as e:
    print(f"⚠ CUA SDK not available: {e}")
    print("  Install CUA SDK or set CUA_API_KEY environment variable")
    CUA_AVAILABLE = False

# Test configuration
AGENT_ID = os.getenv("AGENT_ID", "cua_agent")
TASK_TEXT = os.getenv("CUA_TEST_TASK", "Create a file named test_cua.txt with content 'Hello from CUA agent test'")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017/agent1db?authSource=admin")


class CUAStorageTest:
    """Test suite for CUA agent with storage integration."""
    
    def __init__(self):
        """Initialize test suite."""
        print("=" * 70)
        print("CUA Agent Full Storage Integration Test")
        print("=" * 70)
        
        if not CUA_AVAILABLE:
            print("\n✗ CUA SDK not available. Cannot run test.")
            sys.exit(1)
        
        # Initialize storage adapters
        print("\n[1/6] Initializing storage adapters...")
        try:
            self.mongo = MongoAdapter(agent_id=AGENT_ID, connection_string=MONGODB_URL)
            self.pg = PostgresAdapter()
            self.minio = MinIOAdapter(agent_id=AGENT_ID, postgres_adapter=self.pg)
            print("✓ Storage adapters initialized")
        except Exception as e:
            print(f"✗ Failed to initialize storage adapters: {e}")
            raise
        
        # Initialize CUA agent
        print("\n[2/6] Initializing CUA agent...")
        try:
            self.computer = Computer(
                os_type="linux",
                api_key=os.getenv("CUA_API_KEY"),
                name=os.getenv("CUA_SANDBOX_NAME"),
                provider_type=VMProviderType.CLOUD,
            )
            
            import logging
            self.agent = ComputerAgent(
                model="omniparser+openai/gpt-4o",
                tools=[self.computer],
                only_n_most_recent_images=3,
                verbosity=logging.INFO,
                trajectory_dir="trajectories",
                use_prompt_caching=True,
                max_trajectory_budget=1.0,
            )
            print("✓ CUA agent initialized")
        except Exception as e:
            print(f"✗ Failed to initialize CUA agent: {e}")
            print(f"  Make sure CUA_API_KEY and CUA_SANDBOX_NAME are set")
            raise
    
    def get_baseline_counts(self):
        """Get current record counts before test."""
        print("\n[3/6] Recording baseline counts...")
        
        baseline = {}
        
        # MongoDB logs
        try:
            logs = self.mongo.read_logs(limit=1000)
            baseline["mongodb_logs"] = len(logs)
            print(f"  MongoDB logs: {baseline['mongodb_logs']}")
        except Exception as e:
            print(f"  Warning: Failed to count MongoDB logs: {e}")
            baseline["mongodb_logs"] = 0
        
        # PostgreSQL tasks
        try:
            tasks = self.pg.get_tasks(agent_id=AGENT_ID, limit=1000)
            baseline["postgresql_tasks"] = len(tasks)
            print(f"  PostgreSQL tasks: {baseline['postgresql_tasks']}")
        except Exception as e:
            print(f"  Warning: Failed to count PostgreSQL tasks: {e}")
            baseline["postgresql_tasks"] = 0
        
        # PostgreSQL progress updates
        try:
            # Get most recent task to count its progress
            recent_tasks = self.pg.get_tasks(agent_id=AGENT_ID, limit=1)
            if recent_tasks:
                progress = self.pg.get_task_progress(recent_tasks[0]["id"], limit=1000)
                baseline["postgresql_progress"] = len(progress)
            else:
                baseline["postgresql_progress"] = 0
            print(f"  PostgreSQL progress updates: {baseline['postgresql_progress']}")
        except Exception as e:
            print(f"  Warning: Failed to count PostgreSQL progress: {e}")
            baseline["postgresql_progress"] = 0
        
        # MinIO screenshot metadata
        try:
            screenshots = self.pg.get_binary_files(agent_id=AGENT_ID, bucket="screenshots", limit=1000)
            baseline["minio_screenshots"] = len(screenshots)
            print(f"  MinIO screenshot metadata: {baseline['minio_screenshots']}")
        except Exception as e:
            print(f"  Warning: Failed to count MinIO screenshots: {e}")
            baseline["minio_screenshots"] = 0
        
        return baseline
    
    async def execute_task(self):
        """Execute CUA agent task with storage integration."""
        print(f"\n[4/6] Executing CUA agent task...")
        print(f"  Task: {TASK_TEXT}")
        
        try:
            history = []
            result = await execute_task_with_storage(
                task_text=TASK_TEXT,
                agent=self.agent,
                history=history,
                mongo_adapter=self.mongo,
                pg_adapter=self.pg,
                minio_adapter=self.minio,
                agent_id=AGENT_ID
            )
            
            print(f"✓ Task execution completed")
            print(f"  Task ID: {result.get('task_id')}")
            print(f"  Logs written: {result.get('logs_written', 0)}")
            print(f"  Screenshots uploaded: {result.get('screenshots_uploaded', 0)}")
            print(f"  Progress updates: {result.get('progress_updates', 0)}")
            
            # Wait a bit for async operations to complete
            time.sleep(2)
            
            return result
        except Exception as e:
            print(f"✗ Task execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def verify_storage(self, baseline, execution_result):
        """Verify data appeared in storage systems."""
        print("\n[5/6] Verifying data in storage systems...")
        
        task_id = execution_result.get("task_id")
        verification_results = {}
        
        # Verify MongoDB logs
        print("  Checking MongoDB logs...")
        try:
            logs = self.mongo.read_logs(limit=100)
            new_logs = [log for log in logs if log.get("message") and 
                       (TASK_TEXT.lower() in log.get("message", "").lower() or
                        str(task_id) == str(log.get("task_id", "")))]
            
            if len(new_logs) > 0:
                print(f"    ✓ Found {len(new_logs)} new log entries related to task")
                verification_results["mongodb"] = True
            else:
                print(f"    ✗ No new log entries found (total logs: {len(logs)})")
                verification_results["mongodb"] = False
        except Exception as e:
            print(f"    ✗ MongoDB verification failed: {e}")
            verification_results["mongodb"] = False
        
        # Verify PostgreSQL task
        print("  Checking PostgreSQL task record...")
        try:
            if task_id:
                task = self.pg.get_task(task_id)
                if task:
                    print(f"    ✓ Task record found: {task['title']} - {task['status']}")
                    verification_results["postgresql_task"] = True
                    
                    # Verify progress updates
                    progress = self.pg.get_task_progress(task_id)
                    if len(progress) > 0:
                        print(f"    ✓ Found {len(progress)} progress updates")
                        verification_results["postgresql_progress"] = True
                    else:
                        print(f"    ⚠ No progress updates found")
                        verification_results["postgresql_progress"] = False
                else:
                    print(f"    ✗ Task record not found")
                    verification_results["postgresql_task"] = False
            else:
                print(f"    ⚠ No task_id returned from execution")
                verification_results["postgresql_task"] = False
        except Exception as e:
            print(f"    ✗ PostgreSQL verification failed: {e}")
            verification_results["postgresql_task"] = False
        
        # Verify MinIO screenshots (if any were uploaded)
        print("  Checking MinIO screenshot metadata...")
        try:
            screenshots = self.pg.get_binary_files(agent_id=AGENT_ID, bucket="screenshots", limit=100)
            task_screenshots = [s for s in screenshots if s.get("task_id") == task_id]
            
            if len(task_screenshots) > 0:
                print(f"    ✓ Found {len(task_screenshots)} screenshot(s) for this task")
                verification_results["minio"] = True
            else:
                print(f"    ⚠ No screenshots found (may not have generated screenshots)")
                verification_results["minio"] = "optional"  # Screenshots are optional
        except Exception as e:
            print(f"    ✗ MinIO verification failed: {e}")
            verification_results["minio"] = False
        
        return verification_results
    
    async def run_test(self):
        """Run complete test."""
        baseline = self.get_baseline_counts()
        
        execution_result = await self.execute_task()
        
        verification_results = self.verify_storage(baseline, execution_result)
        
        # Print summary
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        
        for component, result in verification_results.items():
            if result is True:
                status = "✓ PASS"
            elif result == "optional":
                status = "⊘ OPTIONAL"
            else:
                status = "✗ FAIL"
            print(f"{status}: {component}")
        
        # Cleanup
        try:
            self.mongo.close()
        except:
            pass
        
        # Return success if core components passed
        core_passed = (
            verification_results.get("mongodb") is True and
            verification_results.get("postgresql_task") is True
        )
        
        return core_passed


async def main():
    """Main test function."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        test = CUAStorageTest()
        success = await test.run_test()
        
        if success:
            print("\n✓ CUA agent storage integration test passed!")
            print("  All data successfully stored in MongoDB and PostgreSQL")
            sys.exit(0)
        else:
            print("\n✗ Some verifications failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
