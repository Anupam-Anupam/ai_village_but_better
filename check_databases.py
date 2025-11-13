#!/usr/bin/env python3
"""
Database checker for AI Village system
Checks both server and agent databases, and PostgreSQL task storage
"""

import pymongo
import requests
import json
import os
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 not available. Install with: pip install psycopg2-binary")

def check_server_database():
    """Check the server's MongoDB database"""
    print("🔍 CHECKING SERVER DATABASE")
    print("=" * 50)
    
    try:
        # Connect to server database
        MONGODB_URL = 'mongodb://admin:password@localhost:27017/serverdb?authSource=admin'
        client = pymongo.MongoClient(MONGODB_URL)
        db = client.serverdb
        
        print(f"✅ Connected to server database: {db.name}")
        print(f"📁 Collections: {db.list_collection_names()}")
        
        # Check messages
        messages = list(db.messages.find().sort('timestamp', -1).limit(10))
        print(f"\n📨 Recent Messages ({len(messages)}):")
        for i, msg in enumerate(messages, 1):
            timestamp = msg.get('timestamp', 'No timestamp')
            message = msg.get('message', 'No message')
            source = msg.get('source', 'Unknown')
            print(f"  {i}. [{source}] {timestamp}: {message[:60]}{'...' if len(message) > 60 else ''}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to server database: {e}")
        return False

def check_agent_databases():
    """Check each agent's database via their API endpoints"""
    print("\n🤖 CHECKING AGENT DATABASES")
    print("=" * 50)
    
    agents = [
        {"name": "GPT-4 (Agent 1)", "url": "http://localhost:8001"},
        {"name": "Claude (Agent 2)", "url": "http://localhost:8002"}, 
        {"name": "Llama (Agent 3)", "url": "http://localhost:8003"}
    ]
    
    for agent in agents:
        print(f"\n🔍 Checking {agent['name']}...")
        try:
            # Try to get agent status by checking if it responds
            response = requests.get(f"{agent['url']}/", timeout=5)
            if response.status_code == 404:  # 404 means server is running but no root endpoint
                print(f"✅ {agent['name']} is running (server responding)")
                
                # Try to get database info
                try:
                    db_response = requests.get(f"{agent['url']}/database/info", timeout=5)
                    if db_response.status_code == 200:
                        db_info = db_response.json()
                        print(f"📊 Database: {db_info.get('database_name', 'Unknown')}")
                        print(f"📁 Collections: {db_info.get('collections', [])}")
                        
                        # Show recent tasks
                        tasks = db_info.get('recent_tasks', [])
                        if tasks:
                            print(f"📋 Recent Tasks ({len(tasks)}):")
                            for task in tasks[:3]:  # Show first 3
                                print(f"  - {task.get('input_text', 'No input')[:50]}...")
                    else:
                        print(f"⚠️  Could not get database info: {db_response.status_code}")
                except Exception as e:
                    print(f"⚠️  Database info not available: {e}")
            else:
                print(f"❌ {agent['name']} not responding: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {agent['name']} connection failed: {e}")

def check_mongodb_directly():
    """Check MongoDB directly for all databases"""
    print("\n🗄️  CHECKING MONGODB DIRECTLY")
    print("=" * 50)
    
    try:
        # Connect to MongoDB admin
        client = pymongo.MongoClient('mongodb://admin:password@localhost:27017/?authSource=admin')
        
        # List all databases
        db_list = client.list_database_names()
        print(f"📚 Available databases: {db_list}")
        
        # Check each database
        for db_name in ['serverdb', 'agent1db', 'agent2db', 'agent3db']:
            if db_name in db_list:
                db = client[db_name]
                collections = db.list_collection_names()
                print(f"\n📁 {db_name}:")
                print(f"  Collections: {collections}")
                
                # Show document counts
                for collection in collections:
                    count = db[collection].count_documents({})
                    print(f"    - {collection}: {count} documents")
            else:
                print(f"❌ Database {db_name} not found")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return False

def check_postgresql_tasks():
    """Check PostgreSQL database for tasks"""
    print("\n🐘 CHECKING POSTGRESQL TASK DATABASE")
    print("=" * 50)
    
    if not PSYCOPG2_AVAILABLE:
        print("❌ psycopg2 not available. Cannot check PostgreSQL.")
        print("   Install with: pip install psycopg2-binary")
        return False
    
    try:
        # Try to get connection string from environment or use default
        postgres_url = os.getenv(
            "POSTGRES_URL",
            "postgresql://hub:hubpassword@localhost:5433/hub"
        )
        
        # Parse connection string for psycopg2
        # Format: postgresql://user:password@host:port/dbname
        if postgres_url.startswith("postgresql://"):
            postgres_url = postgres_url.replace("postgresql://", "postgres://", 1)
        
        print(f"🔗 Connecting to PostgreSQL...")
        print(f"   Connection string: {postgres_url.split('@')[0]}@***")
        
        conn = psycopg2.connect(postgres_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if tasks table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tasks'
            );
        """)
        table_exists = cursor.fetchone()['exists']
        
        if not table_exists:
            print("❌ Tasks table does not exist!")
            print("   The table should be created automatically by the storage adapter.")
            conn.close()
            return False
        
        print("✅ Tasks table exists")
        
        # Get total task count
        cursor.execute("SELECT COUNT(*) as count FROM tasks")
        total_tasks = cursor.fetchone()['count']
        print(f"📊 Total tasks in database: {total_tasks}")
        
        # Get tasks by status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM tasks 
            GROUP BY status 
            ORDER BY count DESC
        """)
        status_counts = cursor.fetchall()
        print(f"\n📈 Tasks by status:")
        for row in status_counts:
            print(f"   - {row['status']}: {row['count']}")
        
        # Get recent tasks
        cursor.execute("""
            SELECT id, agent_id, title, status, created_at, updated_at, metadata
            FROM tasks 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_tasks = cursor.fetchall()
        
        if recent_tasks:
            print(f"\n📋 Recent Tasks (last {len(recent_tasks)}):")
            for i, task in enumerate(recent_tasks, 1):
                created = task['created_at'].strftime('%Y-%m-%d %H:%M:%S') if task['created_at'] else 'N/A'
                title = task['title'][:60] + '...' if len(task['title']) > 60 else task['title']
                print(f"   {i}. [ID: {task['id']}] [{task['status']}] {title}")
                print(f"      Agent: {task['agent_id']} | Created: {created}")
                if task['metadata']:
                    metadata_str = json.dumps(task['metadata'])[:80]
                    print(f"      Metadata: {metadata_str}...")
        else:
            print("\n⚠️  No tasks found in database!")
            print("   This could mean:")
            print("   - No tasks have been created yet")
            print("   - Tasks are being created in a different database")
            print("   - There's an issue with task creation")
        
        # Check task_progress table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'task_progress'
            );
        """)
        progress_table_exists = cursor.fetchone()['exists']
        
        if progress_table_exists:
            cursor.execute("SELECT COUNT(*) as count FROM task_progress")
            progress_count = cursor.fetchone()['count']
            print(f"\n📊 Total progress updates: {progress_count}")
            
            if progress_count > 0:
                cursor.execute("""
                    SELECT task_id, agent_id, progress_percent, message, timestamp
                    FROM task_progress 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                """)
                recent_progress = cursor.fetchall()
                print(f"\n📈 Recent Progress Updates (last {len(recent_progress)}):")
                for i, prog in enumerate(recent_progress, 1):
                    timestamp = prog['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if prog['timestamp'] else 'N/A'
                    message = prog['message'][:50] + '...' if prog['message'] and len(prog['message']) > 50 else (prog['message'] or 'N/A')
                    print(f"   {i}. Task {prog['task_id']} [{prog['agent_id']}]: {prog['progress_percent']}% - {message}")
                    print(f"      Time: {timestamp}")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        print("   Make sure PostgreSQL is running and accessible.")
        print("   Check: docker-compose ps postgres")
        return False
    except Exception as e:
        print(f"❌ Error checking PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to check all databases"""
    print("🚀 AI VILLAGE DATABASE CHECKER")
    print("=" * 50)
    
    # Check server database
    server_ok = check_server_database()
    
    # Check agent databases
    check_agent_databases()
    
    # Check MongoDB directly
    mongo_ok = check_mongodb_directly()
    
    # Check PostgreSQL tasks
    postgres_ok = check_postgresql_tasks()
    
    print("\n" + "=" * 50)
    results = []
    if server_ok:
        results.append("✅ Server MongoDB")
    if mongo_ok:
        results.append("✅ MongoDB Direct")
    if postgres_ok:
        results.append("✅ PostgreSQL Tasks")
    
    if results:
        print("✅ Database check completed!")
        print("\n".join(results))
    else:
        print("⚠️  Some database connections failed. Check if Docker containers are running.")
    
    print("\n💡 To start the system: docker-compose up -d")
    print("💡 To send a test message: python send_message.py 'Hello agents!'")
    print("💡 To create a task: curl -X POST http://localhost:8000/task -H 'Content-Type: application/json' -d '{\"text\": \"Your task here\"}'")

if __name__ == "__main__":
    main()
