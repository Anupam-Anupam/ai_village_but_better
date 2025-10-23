#!/usr/bin/env python3
"""
Initialize agent database with tables and default data
"""
import sys
import os

# Add the shared directory to path
sys.path.append(os.path.dirname(__file__))

from db import SessionLocal, engine
from models import Base, AgentConfig, AgentLog

def init_agent_database():
    print("🤖 Initializing Agent Database...")
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Initialize with default configuration
    db = SessionLocal()
    try:
        # Check if config already exists
        existing_config = db.query(AgentConfig).count()
        if existing_config == 0:
            print("Adding default agent configuration...")
            
            # Default agent configurations
            default_configs = [
                {
                    "key": "memory_window_size",
                    "value": 10,
                    "description": "Maximum number of memories to keep"
                },
                {
                    "key": "task_timeout",
                    "value": 300,
                    "description": "Task timeout in seconds"
                },
                {
                    "key": "learning_enabled",
                    "value": True,
                    "description": "Enable learning from completed tasks"
                },
                {
                    "key": "log_level",
                    "value": "info",
                    "description": "Logging level (debug, info, warning, error)"
                }
            ]
            
            for config_data in default_configs:
                config = AgentConfig(**config_data)
                db.add(config)
            
            db.commit()
            print("✅ Default configuration added!")
        else:
            print("✅ Configuration already exists, skipping...")
            
        # Add initial log entry
        initial_log = AgentLog(
            level="info",
            message="Agent database initialized successfully",
            task_id=None
        )
        db.add(initial_log)
        db.commit()
        print("✅ Initial log entry added!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("✅ Agent database initialization complete!")

if __name__ == "__main__":
    init_agent_database()
