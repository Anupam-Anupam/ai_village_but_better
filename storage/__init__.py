"""
Storage Adapters for Multi-Agent Architecture
=============================================

Centralized storage layer for logs, progress, and binary data.
"""

from .mongo_adapter import MongoAdapter
from .postgres_adapter import PostgresAdapter
from .minio_adapter import MinIOAdapter

__all__ = ["MongoAdapter", "PostgresAdapter", "MinIOAdapter"]

