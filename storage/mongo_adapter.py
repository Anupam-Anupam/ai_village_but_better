"""
MongoDB Adapter
===============

Read/write adapter for agent logs stored in MongoDB.
Supports per-agent isolation with clustered read access for evaluator.
"""

import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from datetime import datetime
from .schemas import MongoSchema


class MongoAdapter:
    """
    MongoDB adapter for agent logs and memories.
    
    Agents: Full read/write to their own database
    Evaluator: Read access across all agent databases (clustered)
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        agent_id: Optional[str] = None,
        cluster_mode: bool = False
    ):
        """
        Initialize MongoDB adapter.
        
        Args:
            connection_string: MongoDB connection string. If None, uses MONGODB_URL env var.
            agent_id: Agent identifier (used for database name if not in connection string)
            cluster_mode: If True, enables read access to multiple agent databases
        """
        self.agent_id = agent_id or os.getenv("AGENT_ID", "agent1")
        self.cluster_mode = cluster_mode
        
        # Get connection string from env or parameter
        if connection_string:
            self.connection_string = connection_string
        else:
            base_url = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017")
            if cluster_mode:
                # Cluster mode: extract base URL without database name
                # Parse URL: mongodb://[user:pass@]host:port[/db][?options]
                if '/' in base_url:
                    # Remove database name but keep authentication and options
                    parts = base_url.rsplit('/', 1)
                    # Check if second part is a database name or query params
                    if '?' not in parts[1] and parts[1]:
                        # It's a database name, use base URL without it
                        self.connection_string = parts[0]
                    else:
                        # Already no database name or has query params
                        self.connection_string = base_url
                else:
                    self.connection_string = base_url
            else:
                # Single agent mode: use agent-specific database
                db_name = f"{self.agent_id}db"
                if '/' in base_url and not base_url.endswith('/'):
                    # Replace database name
                    parts = base_url.rsplit('/', 1)
                    query_params = ''
                    if '?' in parts[1]:
                        db_part, query_params = parts[1].split('?', 1)
                        query_params = '?' + query_params
                    else:
                        db_part = parts[1].split('?')[0]
                    
                    self.connection_string = f"{parts[0]}/{db_name}{query_params}"
                else:
                    query_params = '?' + base_url.split('?')[1] if '?' in base_url else ''
                    self.connection_string = f"{base_url.rstrip('/')}/{db_name}{query_params}"
        
        # Connect to MongoDB
        self.client = MongoClient(self.connection_string)
        
        # Extract database name for single agent mode
        if not cluster_mode:
            db_part = self.connection_string.split('/')[-1].split('?')[0]
            self.db_name = db_part if db_part else f"{self.agent_id}db"
            self.db = self.client[self.db_name]
            self._init_collections()
        else:
            # Cluster mode: will connect to multiple databases dynamically
            self.databases = {}
    
    def _init_collections(self):
        """Initialize collections and indexes for single agent database."""
        self.logs = self.db.agent_logs
        self.memories = self.db.agent_memories
        self.config = self.db.agent_config
        
        # Create indexes
        self.logs.create_index("agent_id")
        self.logs.create_index("created_at")
        self.logs.create_index("level")
        self.logs.create_index("task_id")
        
        self.memories.create_index("agent_id")
        self.memories.create_index("created_at")
        self.memories.create_index("memory_type")
        
        self.config.create_index("key", unique=True)
    
    def write_log(
        self,
        level: str,
        message: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write log entry to MongoDB.
        
        Args:
            level: Log level (info, error, warning, debug)
            message: Log message
            task_id: Optional task identifier
            metadata: Optional additional metadata
            
        Returns:
            Log entry ID
        """
        if self.cluster_mode:
            raise ValueError("Cannot write in cluster mode. Use agent-specific adapter.")
        
        log_entry = MongoSchema.log_entry(
            level=level,
            message=message,
            agent_id=self.agent_id,
            task_id=task_id,
            metadata=metadata
        )
        result = self.logs.insert_one(log_entry)
        return str(result.inserted_id)
    
    def read_logs(
        self,
        agent_id: Optional[str] = None,
        level: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read logs from MongoDB.
        
        Args:
            agent_id: Agent identifier (only used in cluster mode)
            level: Filter by log level
            task_id: Filter by task ID
            limit: Maximum number of results
            start_time: Filter logs after this time
            end_time: Filter logs before this time
            
        Returns:
            List of log entries
        """
        query = {}
        
        if agent_id and self.cluster_mode:
            # Cluster mode: connect to specific agent database
            db_name = f"{agent_id}db"
            if db_name not in self.databases:
                # Parse connection string to get base URL
                base_url = self.connection_string.rstrip('/')
                db_url = f"{base_url}/{db_name}"
                # Preserve authentication if present
                if '@' in base_url:
                    # Already has auth
                    pass
                client = MongoClient(db_url)
                self.databases[db_name] = {
                    "client": client,
                    "db": client[db_name],
                    "logs": client[db_name].agent_logs
                }
            logs_collection = self.databases[db_name]["logs"]
        else:
            if not self.cluster_mode and agent_id and agent_id != self.agent_id:
                raise ValueError(f"Cannot read logs from different agent in single mode. Use cluster_mode=True.")
            logs_collection = self.logs
        
        if agent_id and self.cluster_mode:
            query["agent_id"] = agent_id
        elif not self.cluster_mode:
            query["agent_id"] = self.agent_id
        
        if level:
            query["level"] = level
        
        if task_id:
            query["task_id"] = task_id
        
        if start_time:
            query["created_at"] = {"$gte": start_time}
        
        if end_time:
            if "created_at" in query:
                query["created_at"]["$lte"] = end_time
            else:
                query["created_at"] = {"$lte": end_time}
        
        cursor = logs_collection.find(query).sort("created_at", -1).limit(limit)
        return list(cursor)
    
    def write_memory(
        self,
        content: str,
        memory_type: str = "general",
        task_id: Optional[str] = None
    ) -> str:
        """
        Write memory entry to MongoDB.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            task_id: Optional task identifier
            
        Returns:
            Memory entry ID
        """
        if self.cluster_mode:
            raise ValueError("Cannot write in cluster mode. Use agent-specific adapter.")
        
        memory_entry = MongoSchema.memory_entry(
            content=content,
            agent_id=self.agent_id,
            memory_type=memory_type,
            task_id=task_id
        )
        result = self.memories.insert_one(memory_entry)
        return str(result.inserted_id)
    
    def read_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Read memories from MongoDB.
        
        Args:
            agent_id: Agent identifier (only used in cluster mode)
            memory_type: Filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of memory entries
        """
        query = {}
        
        if agent_id and self.cluster_mode:
            db_name = f"{agent_id}db"
            if db_name not in self.databases:
                base_url = self.connection_string.rstrip('/')
                db_url = f"{base_url}/{db_name}"
                client = MongoClient(db_url)
                self.databases[db_name] = {
                    "client": client,
                    "db": client[db_name],
                    "memories": client[db_name].agent_memories
                }
            memories_collection = self.databases[db_name]["memories"]
        else:
            if not self.cluster_mode and agent_id and agent_id != self.agent_id:
                raise ValueError(f"Cannot read memories from different agent in single mode.")
            memories_collection = self.memories
        
        if agent_id and self.cluster_mode:
            query["agent_id"] = agent_id
        elif not self.cluster_mode:
            query["agent_id"] = self.agent_id
        
        if memory_type:
            query["memory_type"] = memory_type
        
        cursor = memories_collection.find(query).sort("created_at", -1).limit(limit)
        return list(cursor)
    
    def read_all_agent_logs(
        self,
        agent_ids: List[str],
        level: Optional[str] = None,
        limit_per_agent: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Read logs from multiple agents (evaluator use case).
        
        Args:
            agent_ids: List of agent identifiers
            level: Filter by log level
            limit_per_agent: Maximum results per agent
            
        Returns:
            Dictionary mapping agent_id to list of logs
        """
        if not self.cluster_mode:
            raise ValueError("Cluster mode required for reading all agent logs.")
        
        results = {}
        for agent_id in agent_ids:
            results[agent_id] = self.read_logs(
                agent_id=agent_id,
                level=level,
                limit=limit_per_agent
            )
        
        return results
    
    def close(self):
        """Close MongoDB connections."""
        if self.cluster_mode:
            for db_info in self.databases.values():
                db_info["client"].close()
        self.client.close()

