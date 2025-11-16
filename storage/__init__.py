"""
Storage Adapters for Multi-Agent Architecture
=============================================

Centralized storage layer for logs, progress, and binary data.
"""

from .mongo_adapter import MongoAdapter
from .postgres_adapter import PostgresAdapter
__all__ = ["MongoAdapter", "PostgresAdapter"]

