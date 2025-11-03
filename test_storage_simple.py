"""
Simple Storage Test
===================

Quick test script to verify storage adapters work correctly.
Tests each adapter independently without requiring running services.

Usage:
    python test_storage_simple.py
"""

import os
import sys
from datetime import datetime

# Add storage directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'storage'))

from storage import MongoAdapter, PostgresAdapter, MinIOAdapter


def test_mongo_adapter():
    """Test MongoDB adapter."""
    print("\n[1/3] Testing MongoDB Adapter...")
    
    try:
        mongo = MongoAdapter(agent_id="agent1")
        
        # Write log
        log_id = mongo.write_log(
            level="info",
            message="Test log message",
            task_id="test_123"
        )
        print(f"✓ Wrote log: {log_id}")
        
        # Read logs
        logs = mongo.read_logs(limit=5)
        print(f"✓ Read {len(logs)} logs")
        
        # Write memory
        memory_id = mongo.write_memory(
            content="Test memory",
            memory_type="test"
        )
        print(f"✓ Wrote memory: {memory_id}")
        
        # Read memories
        memories = mongo.read_memories(limit=5)
        print(f"✓ Read {len(memories)} memories")
        
        mongo.close()
        print("✓ MongoDB adapter test passed\n")
        return True
        
    except Exception as e:
        print(f"✗ MongoDB adapter test failed: {e}\n")
        return False


def test_postgres_adapter():
    """Test PostgreSQL adapter."""
    print("[2/3] Testing PostgreSQL Adapter...")
    
    try:
        pg = PostgresAdapter()
        
        # Create task
        task_id = pg.create_task(
            agent_id="agent1",
            title="Test Task",
            description="Test description",
            status="pending"
        )
        print(f"✓ Created task: {task_id}")
        
        # Add progress
        progress_id = pg.add_progress_update(
            task_id=task_id,
            agent_id="agent1",
            progress_percent=50.0,
            message="Halfway done"
        )
        print(f"✓ Added progress: {progress_id}")
        
        # Update status
        updated = pg.update_task_status(task_id, "completed")
        print(f"✓ Updated status: {updated}")
        
        # Get task
        task = pg.get_task(task_id)
        if task:
            print(f"✓ Retrieved task: {task['title']}")
        
        # Get progress
        progress = pg.get_task_progress(task_id)
        print(f"✓ Retrieved {len(progress)} progress updates")
        
        print("✓ PostgreSQL adapter test passed\n")
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL adapter test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_minio_adapter():
    """Test MinIO adapter."""
    print("[3/3] Testing MinIO Adapter...")
    
    try:
        pg = PostgresAdapter()
        minio = MinIOAdapter(agent_id="agent1", postgres_adapter=pg)
        
        # Create test PNG data (1x1 pixel)
        test_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Upload screenshot
        object_path = minio.upload_screenshot(
            file_data=test_png,
            filename="test.png",
            task_id=None
        )
        print(f"✓ Uploaded screenshot: {object_path}")
        
        # Download screenshot
        downloaded = minio.download_screenshot(object_path)
        if downloaded == test_png:
            print("✓ Downloaded screenshot matches")
        else:
            print("✗ Downloaded screenshot doesn't match")
            return False
        
        # Check metadata
        files = pg.get_binary_files(bucket="screenshots", agent_id="agent1")
        if files:
            print(f"✓ Found {len(files)} screenshot metadata entries")
        
        print("✓ MinIO adapter test passed\n")
        return True
        
    except Exception as e:
        print(f"✗ MinIO adapter test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all simple tests."""
    print("=" * 70)
    print("Simple Storage Adapter Tests")
    print("=" * 70)
    
    results = {
        "MongoDB": test_mongo_adapter(),
        "PostgreSQL": test_postgres_adapter(),
        "MinIO": test_minio_adapter()
    }
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if all(results.values()):
        print("\n✓ All adapter tests passed!")
        return 0
    else:
        print("\n✗ Some adapter tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

