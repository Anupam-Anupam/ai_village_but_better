#!/usr/bin/env python3
"""
Database checker for AI Village system
Checks both server and agent databases
"""

import pymongo
import requests
import json
from datetime import datetime

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
    
    print("\n" + "=" * 50)
    if server_ok and mongo_ok:
        print("✅ Database check completed successfully!")
    else:
        print("⚠️  Some database connections failed. Check if Docker containers are running.")
    
    print("\n💡 To start the system: docker-compose up -d")
    print("💡 To send a test message: python send_message.py 'Hello agents!'")

if __name__ == "__main__":
    main()
