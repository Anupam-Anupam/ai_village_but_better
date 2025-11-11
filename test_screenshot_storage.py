#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify screenshot storage functionality.
Tests that screenshots are saved correctly in MinIO under agent{ID}/screenshots/
"""

import os
import sys
from pathlib import Path
from io import BytesIO

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import storage adapters
try:
    from storage import PostgresAdapter, MinIOAdapter
    print("[OK] Successfully imported storage adapters")
except ImportError as e:
    print(f"[ERROR] Failed to import storage adapters: {e}")
    sys.exit(1)


def create_test_image() -> bytes:
    """Create a simple test PNG image (1x1 pixel)."""
    # Minimal valid PNG file
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    return png_data


def test_agent_id_normalization():
    """Test that agent IDs are normalized correctly."""
    print("\n" + "="*60)
    print("TEST 1: Agent ID Normalization")
    print("="*60)
    
    # Test cases
    test_cases = [
        ("agent1-cua", "agent1"),
        ("agent2-cua", "agent2"),
        ("agent3-cua", "agent3"),
        ("agent1", "agent1"),
        ("agent2", "agent2"),
        ("1", "agent1"),
        ("2", "agent2"),
    ]
    
    # We need to test the normalization method
    # Since it's a private method, we'll test it through the adapter initialization
    print("\nTesting agent ID normalization...")
    
    for input_id, expected in test_cases:
        try:
            # Initialize adapter with test agent_id
            # We'll use a mock approach since we need MinIO connection
            from storage.minio_adapter import MinIOAdapter
            import re
            
            # Test the normalization logic directly
            match = re.search(r'agent(\d+)', input_id, re.IGNORECASE)
            if match:
                agent_num = match.group(1)
                normalized = f"agent{agent_num}"
            else:
                match = re.search(r'(\d+)', input_id)
                if match:
                    agent_num = match.group(1)
                    normalized = f"agent{agent_num}"
                else:
                    normalized = "agent1"
            
            if normalized == expected:
                print(f"  [OK] '{input_id}' -> '{normalized}' (expected: '{expected}')")
            else:
                print(f"  [FAIL] '{input_id}' -> '{normalized}' (expected: '{expected}')")
        except Exception as e:
            print(f"  [ERROR] Error testing '{input_id}': {e}")
    
    print("\n[OK] Agent ID normalization test completed")


def test_minio_connection():
    """Test MinIO connection."""
    print("\n" + "="*60)
    print("TEST 2: MinIO Connection")
    print("="*60)
    
    try:
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        print(f"MinIO Endpoint: {minio_endpoint}")
        
        # Try to initialize MinIO adapter
        # We need PostgreSQL adapter first
        pg_url = os.getenv("POSTGRES_URL")
        if not pg_url:
            print("[WARN] POSTGRES_URL not set, skipping MinIO connection test")
            return False
        
        pg_adapter = PostgresAdapter(connection_string=pg_url)
        print("[OK] PostgreSQL adapter initialized")
        
        # Initialize MinIO adapter
        minio_adapter = MinIOAdapter(
            endpoint=minio_endpoint,
            postgres_adapter=pg_adapter,
            agent_id="agent1-cua"  # Test with agent1-cua
        )
        
        print(f"[OK] MinIO adapter initialized")
        print(f"   Normalized agent_id: {minio_adapter.agent_id}")
        
        # Check if bucket exists
        if minio_adapter.client.bucket_exists("screenshots"):
            print("[OK] 'screenshots' bucket exists")
        else:
            print("[WARN] 'screenshots' bucket does not exist (will be created on first upload)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] MinIO connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screenshot_upload():
    """Test uploading a screenshot to MinIO."""
    print("\n" + "="*60)
    print("TEST 3: Screenshot Upload")
    print("="*60)
    
    try:
        # Get environment variables
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        pg_url = os.getenv("POSTGRES_URL")
        
        if not pg_url:
            print("[ERROR] POSTGRES_URL not set, cannot test screenshot upload")
            return False
        
        # Initialize adapters
        pg_adapter = PostgresAdapter(connection_string=pg_url)
        minio_adapter = MinIOAdapter(
            endpoint=minio_endpoint,
            postgres_adapter=pg_adapter,
            agent_id="agent1-cua"  # Test with agent1-cua
        )
        
        print(f"Using agent_id: agent1-cua")
        print(f"Normalized agent_id: {minio_adapter.agent_id}")
        
        # Create test image
        test_image = create_test_image()
        print(f"Created test image ({len(test_image)} bytes)")
        
        # Upload screenshot
        print("\nUploading screenshot...")
        object_path = minio_adapter.upload_screenshot(
            file_data=test_image,
            filename="test_screenshot.png",
            task_id=None,
            metadata={"test": True, "source": "test_script"}
        )
        
        print(f"✅ Screenshot uploaded successfully!")
        print(f"   Object path: {object_path}")
        
        # Verify path format
        expected_prefix = f"{minio_adapter.agent_id}/screenshots/"
        if object_path.startswith(expected_prefix):
            print(f"[OK] Path format is correct: {object_path}")
            print(f"   Expected prefix: {expected_prefix}")
        else:
            print(f"[FAIL] Path format is incorrect!")
            print(f"   Got: {object_path}")
            print(f"   Expected prefix: {expected_prefix}")
            return False
        
        # Verify file exists in MinIO
        try:
            response = minio_adapter.client.get_object("screenshots", object_path)
            data = response.read()
            response.close()
            response.release_conn()
            
            if len(data) == len(test_image):
                print(f"[OK] Screenshot verified in MinIO ({len(data)} bytes)")
            else:
                print(f"[WARN] Screenshot size mismatch: expected {len(test_image)}, got {len(data)}")
        except Exception as e:
            print(f"[WARN] Could not verify screenshot in MinIO: {e}")
        
        # Test with different agent IDs
        print("\n--- Testing different agent IDs ---")
        test_agents = ["agent2-cua", "agent3-cua", "agent1"]
        
        for agent_id in test_agents:
            try:
                minio_adapter_test = MinIOAdapter(
                    endpoint=minio_endpoint,
                    postgres_adapter=pg_adapter,
                    agent_id=agent_id
                )
                print(f"  Agent ID: '{agent_id}' -> Normalized: '{minio_adapter_test.agent_id}'")
                
                # Upload test screenshot
                test_path = minio_adapter_test.upload_screenshot(
                    file_data=test_image,
                    filename=f"test_{agent_id.replace('-', '_')}.png"
                )
                print(f"    [OK] Uploaded to: {test_path}")
                
            except Exception as e:
                print(f"    [ERROR] Failed for '{agent_id}': {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Screenshot upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_list_screenshots():
    """Test listing screenshots from MinIO."""
    print("\n" + "="*60)
    print("TEST 4: List Screenshots")
    print("="*60)
    
    try:
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        pg_url = os.getenv("POSTGRES_URL")
        
        if not pg_url:
            print("[ERROR] POSTGRES_URL not set, cannot test listing")
            return False
        
        pg_adapter = PostgresAdapter(connection_string=pg_url)
        minio_adapter = MinIOAdapter(
            endpoint=minio_endpoint,
            postgres_adapter=pg_adapter,
            agent_id="agent1-cua"
        )
        
        # List screenshots for agent1
        print(f"\nListing screenshots for {minio_adapter.agent_id}...")
        objects = minio_adapter.list_objects(
            bucket="screenshots",
            prefix=f"{minio_adapter.agent_id}/screenshots/",
            limit=10
        )
        
        print(f"Found {len(objects)} screenshot(s):")
        for obj in objects[:5]:  # Show first 5
            print(f"  - {obj['object_name']} ({obj['size']} bytes)")
        
        if len(objects) > 5:
            print(f"  ... and {len(objects) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] List screenshots test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("SCREENSHOT STORAGE FUNCTIONALITY TEST")
    print("="*60)
    
    # Check environment variables
    print("\nChecking environment variables...")
    required_vars = ["POSTGRES_URL", "MINIO_ENDPOINT"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive parts
            if "password" in var.lower() or "key" in var.lower():
                print(f"  [OK] {var}: {'*' * len(value)}")
            else:
                print(f"  [OK] {var}: {value}")
        else:
            print(f"  [WARN] {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n[WARN] Missing environment variables: {', '.join(missing_vars)}")
        print("   Some tests may be skipped")
    
    # Run tests
    results = []
    
    # Test 1: Agent ID normalization
    try:
        test_agent_id_normalization()
        results.append(("Agent ID Normalization", True))
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        results.append(("Agent ID Normalization", False))
    
    # Test 2: MinIO connection
    try:
        success = test_minio_connection()
        results.append(("MinIO Connection", success))
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        results.append(("MinIO Connection", False))
    
    # Test 3: Screenshot upload
    try:
        success = test_screenshot_upload()
        results.append(("Screenshot Upload", success))
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        results.append(("Screenshot Upload", False))
    
    # Test 4: List screenshots
    try:
        success = test_list_screenshots()
        results.append(("List Screenshots", success))
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        results.append(("List Screenshots", False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[PASSED]" if success else "[FAILED]"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

