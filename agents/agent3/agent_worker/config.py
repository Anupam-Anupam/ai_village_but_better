# Configuration module: reads environment variables and exposes Config dataclass
"""Configuration module for agent worker."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Agent worker configuration from environment variables."""
    
    # PostgreSQL
    postgres_dsn: str
    
    # MongoDB
    mongo_uri: str
    
    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool
    
    # Agent
    agent_id: str
    
    # Worker settings
    poll_interval_seconds: int
    run_task_timeout_seconds: int
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # PostgreSQL - support both POSTGRES_URL (existing convention) and POSTGRES_DSN
        postgres_dsn = os.getenv("POSTGRES_URL") or os.getenv("POSTGRES_DSN")
        if not postgres_dsn:
            raise ValueError("POSTGRES_URL or POSTGRES_DSN environment variable is required")
        
        # MongoDB - support both MONGODB_URL (existing convention) and MONGO_URI
        mongo_uri = os.getenv("MONGODB_URL") or os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URL or MONGO_URI environment variable is required")
        
        # MinIO
        minio_endpoint = os.getenv("MINIO_ENDPOINT")
        if not minio_endpoint:
            raise ValueError("MINIO_ENDPOINT environment variable is required")
        
        minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        if not minio_access_key:
            raise ValueError("MINIO_ACCESS_KEY environment variable is required")
        
        minio_secret_key = os.getenv("MINIO_SECRET_KEY")
        if not minio_secret_key:
            raise ValueError("MINIO_SECRET_KEY environment variable is required")
        
        # MinIO secure mode (default: False)
        minio_secure_str = os.getenv("MINIO_SECURE", "false").lower()
        minio_secure = minio_secure_str in ("true", "1", "yes")
        
        # Agent ID
        agent_id = os.getenv("AGENT_ID")
        if not agent_id:
            raise ValueError("AGENT_ID environment variable is required")
        
        # Worker settings with defaults
        poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
        run_task_timeout_seconds = int(os.getenv("RUN_TASK_TIMEOUT_SECONDS", "300"))
        
        return cls(
            postgres_dsn=postgres_dsn,
            mongo_uri=mongo_uri,
            minio_endpoint=minio_endpoint,
            minio_access_key=minio_access_key,
            minio_secret_key=minio_secret_key,
            minio_secure=minio_secure,
            agent_id=agent_id,
            poll_interval_seconds=poll_interval_seconds,
            run_task_timeout_seconds=run_task_timeout_seconds
        )

