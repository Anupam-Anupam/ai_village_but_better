"""
Shared Database Models for AI Agents
===================================

This module provides a unified database interface for all AI agents.
Each agent uses this shared code but connects to its own separate MongoDB database.

Database Structure:
- Each agent has its own MongoDB instance running in its container
- Each agent connects to its own database (agent1db, agent2db, agent3db)
- No data sharing between agents - complete isolation
- Shared code for consistency and maintainability

Collections per agent:
- agent_tasks: Task storage and tracking
- agent_memories: Agent's memory window with automatic cleanup
- agent_config: Agent settings and preferences
- agent_logs: Activity and error logging
"""

from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, Optional
import os

class AgentDatabase:
    """
    MongoDB database manager for individual AI agents.
    
    Each agent instance gets its own database connection based on the MONGODB_URL
    environment variable. This ensures complete data isolation between agents.
    
    Example:
        Agent 1: MONGODB_URL=mongodb://localhost:27017/agent1db
        Agent 2: MONGODB_URL=mongodb://localhost:27017/agent2db
        Agent 3: MONGODB_URL=mongodb://localhost:27017/agent3db
    """
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database connection for this specific agent.
        
        Args:
            connection_string: MongoDB connection string. If None, uses MONGODB_URL env var.
                              Each agent should have its own unique database name.
        """
        # Get connection string from parameter or environment variable
        self.connection_string = connection_string or os.getenv("MONGODB_URL", "mongodb://localhost:27017/agentdb")
        
        # Connect to MongoDB
        self.client = MongoClient(self.connection_string)
        
        # Extract database name from connection string
        # This ensures each agent connects to its own database
        # Remove query parameters (like ?authSource=admin) from database name
        db_part = self.connection_string.split('/')[-1]
        self.db_name = db_part.split('?')[0]
        self.db = self.client[self.db_name]
        
        # Define collections for this agent's database
        # Each agent has its own separate collections
        self.tasks = self.db.agent_tasks      # Task storage and tracking
        self.memories = self.db.agent_memories # Agent's memory window
        self.config = self.db.agent_config     # Agent settings
        self.logs = self.db.agent_logs         # Activity logging
        
        # Create database indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """
        Create database indexes for better performance.
        
        Indexes are created on frequently queried fields to improve
        database performance for each agent's operations.
        """
        # Task indexes
        self.tasks.create_index("status")      # For filtering by task status
        self.tasks.create_index("created_at")   # For sorting by creation time
        
        # Memory indexes  
        self.memories.create_index("memory_type") # For filtering by memory type
        self.memories.create_index("created_at")  # For sorting by creation time
        
        # Config indexes
        self.config.create_index("key", unique=True) # For unique config keys
        
        # Log indexes
        self.logs.create_index("level")        # For filtering by log level
        self.logs.create_index("created_at")   # For sorting by creation time
    
    def create_task(self, title: str, description: str, input_data: Dict[str, Any], status: str = "pending") -> str:
        """
        Create a new task in this agent's database.
        
        Args:
            title: Task title
            description: Task description
            input_data: Input data for the task (JSON)
            status: Task status (pending, in_progress, completed, failed)
            
        Returns:
            str: Task ID (MongoDB ObjectId as string)
        """
        task = {
            "title": title,
            "description": description,
            "input_data": input_data,
            "output_data": None,
            "status": status,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.tasks.insert_one(task)
        return str(result.inserted_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task"""
        updates["updated_at"] = datetime.utcnow()
        result = self.tasks.update_one({"_id": task_id}, {"$set": updates})
        return result.modified_count > 0
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        return self.tasks.find_one({"_id": task_id})
    
    def get_tasks(self, status: str = None, limit: int = 10) -> list:
        """Get tasks with optional status filter"""
        query = {}
        if status:
            query["status"] = status
        
        return list(self.tasks.find(query).sort("created_at", -1).limit(limit))
    
    def add_memory(self, content: str, memory_type: str = "general", task_id: str = None) -> str:
        """Add a memory"""
        memory = {
            "content": content,
            "memory_type": memory_type,
            "task_id": task_id,
            "created_at": datetime.utcnow()
        }
        result = self.memories.insert_one(memory)
        return str(result.inserted_id)
    
    def get_memories(self, memory_type: str = None, limit: int = 10) -> list:
        """Get memories with optional type filter"""
        query = {}
        if memory_type:
            query["memory_type"] = memory_type
        
        return list(self.memories.find(query).sort("created_at", -1).limit(limit))
    
    def cleanup_old_memories(self, max_memories: int = 10):
        """Clean up old memories to maintain memory window"""
        memories = list(self.memories.find().sort("created_at", -1))
        if len(memories) > max_memories:
            old_memories = memories[max_memories:]
            for memory in old_memories:
                self.memories.delete_one({"_id": memory["_id"]})
    
    def set_config(self, key: str, value: Any, description: str = None) -> bool:
        """Set configuration value"""
        config = {
            "key": key,
            "value": value,
            "description": description,
            "updated_at": datetime.utcnow()
        }
        result = self.config.update_one(
            {"key": key}, 
            {"$set": config}, 
            upsert=True
        )
        return True
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        config = self.config.find_one({"key": key})
        return config["value"] if config else default
    
    def log(self, level: str, message: str, task_id: str = None) -> str:
        """Add a log entry"""
        log_entry = {
            "level": level,
            "message": message,
            "task_id": task_id,
            "created_at": datetime.utcnow()
        }
        result = self.logs.insert_one(log_entry)
        return str(result.inserted_id)
    
    def get_logs(self, level: str = None, limit: int = 50) -> list:
        """Get logs with optional level filter"""
        query = {}
        if level:
            query["level"] = level
        
        return list(self.logs.find(query).sort("created_at", -1).limit(limit))
    
    def close(self):
        """Close database connection"""
        self.client.close()
