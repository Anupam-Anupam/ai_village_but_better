"""
Quick connection test for databases
"""
import os

print("Testing database connections...")
print()

# PostgreSQL
print("1. Testing PostgreSQL connection...")
try:
    from storage.postgres_adapter import PostgresAdapter
    
    # Try with default
    pg = PostgresAdapter()
    print(f"✓ Connected to PostgreSQL: {pg.connection_string}")
    
    # Test query
    from sqlalchemy import text
    db = pg.SessionLocal()
    try:
        result = db.execute(text("SELECT 1"))
        print("✓ PostgreSQL query successful")
    finally:
        db.close()
except Exception as e:
    print(f"✗ PostgreSQL connection failed: {e}")
    print(f"  Connection string: {os.getenv('POSTGRES_URL', 'postgresql://hub:hubpassword@localhost:5432/hub')}")

print()

# MongoDB
print("2. Testing MongoDB connection...")
try:
    from storage.mongo_adapter import MongoAdapter
    mongo = MongoAdapter(agent_id="agent1")
    print(f"✓ Connected to MongoDB: {mongo.connection_string}")
    mongo.close()
except Exception as e:
    print(f"✗ MongoDB connection failed: {e}")
    print(f"  Connection string: {os.getenv('MONGODB_URL', 'mongodb://admin:password@localhost:27017/agent1db?authSource=admin')}")

print()

# MinIO
print("3. Testing MinIO connection...")
try:
    from storage.minio_adapter import MinIOAdapter
    from storage.postgres_adapter import PostgresAdapter
    
    pg = PostgresAdapter()
    minio = MinIOAdapter(agent_id="agent1", postgres_adapter=pg)
    buckets = minio.client.list_buckets()
    print(f"✓ Connected to MinIO: {minio.endpoint}")
    print(f"  Found {len(buckets)} buckets")
except Exception as e:
    print(f"✗ MinIO connection failed: {e}")
    print(f"  Endpoint: {os.getenv('MINIO_ENDPOINT', 'localhost:9000')}")

print()
print("Current environment variables:")
print(f"  POSTGRES_URL: {os.getenv('POSTGRES_URL', 'NOT SET')}")
print(f"  MONGODB_URL: {os.getenv('MONGODB_URL', 'NOT SET')}")
print(f"  MINIO_ENDPOINT: {os.getenv('MINIO_ENDPOINT', 'NOT SET')}")
print(f"  AGENT_ID: {os.getenv('AGENT_ID', 'NOT SET')}")

