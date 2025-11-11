"""
MinIO Adapter
=============

Adapter for screenshots and binary files stored in MinIO (S3-compatible).
Agents: Full read/write to their own namespace
Evaluator: Read metadata only (not binary content)
Frontend: Read screenshots only
"""

import os
from typing import Optional, BinaryIO, Dict, Any
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from datetime import datetime
from .schemas import MinIOSchema
from .postgres_adapter import PostgresAdapter


class MinIOAdapter:
    """
    MinIO adapter for binary file storage.
    
    Agents: Upload and download screenshots/binary files
    Evaluator: Read metadata only (from PostgreSQL)
    Frontend: Download screenshots via presigned URLs
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
        agent_id: Optional[str] = None,
        postgres_adapter: Optional[PostgresAdapter] = None
    ):
        """
        Initialize MinIO adapter.
        
        Args:
            endpoint: MinIO endpoint (e.g., 'minio:9000' or 'localhost:9000')
            access_key: MinIO access key. If None, uses MINIO_ACCESS_KEY env var.
            secret_key: MinIO secret key. If None, uses MINIO_SECRET_KEY env var.
            secure: Use HTTPS (True) or HTTP (False). If None, auto-detects based on endpoint.
            agent_id: Agent identifier for namespace isolation (e.g., 'agent1-cua' -> 'agent1')
            postgres_adapter: PostgreSQL adapter for metadata storage
        """
        raw_agent_id = agent_id or os.getenv("AGENT_ID", "agent1")
        # Normalize agent_id to format: agent{ID} (e.g., 'agent1-cua' -> 'agent1', 'agent1' -> 'agent1')
        self.agent_id = self._normalize_agent_id(raw_agent_id)
        
        # Get MinIO credentials from environment
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        # Auto-detect secure mode if not specified
        if secure is None:
            # Check environment variable first
            secure_env = os.getenv("MINIO_SECURE", "").lower()
            if secure_env in ("true", "1", "yes"):
                self.secure = True
            elif secure_env in ("false", "0", "no"):
                self.secure = False
            else:
                # Auto-detect: use HTTP for localhost/local endpoints, HTTPS for others
                # Remove protocol prefix if present
                endpoint_clean = self.endpoint.replace("http://", "").replace("https://", "")
                is_local = (
                    endpoint_clean.startswith("localhost") or
                    endpoint_clean.startswith("127.0.0.1") or
                    endpoint_clean.startswith("minio:") or
                    endpoint_clean.startswith("0.0.0.0") or
                    ":9000" in endpoint_clean  # Default MinIO port
                )
                self.secure = not is_local  # HTTP for local, HTTPS for remote
        else:
            self.secure = secure
        
        # Initialize MinIO client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # PostgreSQL adapter for metadata
        self.pg_adapter = postgres_adapter
        
        # Initialize buckets
        self._init_buckets()
    
    def _normalize_agent_id(self, agent_id: str) -> str:
        """
        Normalize agent_id to format: agent{ID}
        
        Examples:
            'agent1-cua' -> 'agent1'
            'agent2-cua' -> 'agent2'
            'agent1' -> 'agent1'
            'agent1' -> 'agent1'
            '1' -> 'agent1'
            'cua_agent' -> 'agent1' (fallback)
        
        Args:
            agent_id: Raw agent identifier
            
        Returns:
            Normalized agent_id in format 'agent{ID}'
        """
        import re
        
        # Extract numeric part from agent_id
        # Match patterns like: agent1, agent1-cua, agent2-cua, etc.
        match = re.search(r'agent(\d+)', agent_id, re.IGNORECASE)
        if match:
            agent_num = match.group(1)
            return f"agent{agent_num}"
        
        # If no match, try to extract just a number
        match = re.search(r'(\d+)', agent_id)
        if match:
            agent_num = match.group(1)
            return f"agent{agent_num}"
        
        # Fallback: use default
        return "agent1"
    
    def _init_buckets(self):
        """Create buckets if they don't exist."""
        buckets = ["screenshots", "binaries"]
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
            except S3Error as e:
                print(f"Error creating bucket {bucket}: {e}")
    
    def upload_screenshot(
        self,
        file_data: bytes,
        filename: Optional[str] = None,
        task_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a screenshot to MinIO.
        
        Args:
            file_data: Screenshot image bytes
            filename: Optional custom filename. If None, auto-generates.
            task_id: Optional task identifier
            metadata: Optional additional metadata
            
        Returns:
            Object path (for use in URLs)
        """
        # Generate object path
        if filename:
            object_path = f"{self.agent_id}/screenshots/{filename}"
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            object_path = f"{self.agent_id}/screenshots/screenshot_{timestamp}.png"
        
        # Upload to MinIO
        file_size = len(file_data)
        file_stream = BytesIO(file_data)
        
        try:
            self.client.put_object(
                "screenshots",
                object_path,
                file_stream,
                file_size,
                content_type="image/png"
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload screenshot: {e}")
        
        # Register metadata in PostgreSQL
        if self.pg_adapter:
            try:
                self.pg_adapter.register_binary_file(
                    agent_id=self.agent_id,
                    object_path=object_path,
                    bucket="screenshots",
                    content_type="image/png",
                    task_id=task_id,
                    size_bytes=file_size,
                    metadata=metadata
                )
            except Exception as e:
                print(f"Warning: Failed to register screenshot metadata: {e}")
        
        return object_path
    
    def download_screenshot(self, object_path: str) -> bytes:
        """
        Download a screenshot from MinIO.
        
        Args:
            object_path: Object path returned from upload_screenshot
            
        Returns:
            Screenshot image bytes
        """
        try:
            response = self.client.get_object("screenshots", object_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise RuntimeError(f"Failed to download screenshot: {e}")
    
    def upload_binary_file(
        self,
        file_data: bytes,
        bucket: str,
        object_path: str,
        content_type: str = "application/octet-stream",
        task_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a binary file to MinIO.
        
        Args:
            file_data: File bytes
            bucket: Bucket name
            object_path: Object path (including agent namespace, e.g., 'agent1/files/data.bin')
            content_type: MIME type
            task_id: Optional task identifier
            metadata: Optional additional metadata
            
        Returns:
            Object path
        """
        # Ensure object path includes agent namespace
        if not object_path.startswith(f"{self.agent_id}/"):
            object_path = f"{self.agent_id}/{object_path}"
        
        # Upload to MinIO
        file_size = len(file_data)
        file_stream = BytesIO(file_data)
        
        try:
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
            
            self.client.put_object(
                bucket,
                object_path,
                file_stream,
                file_size,
                content_type=content_type
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload binary file: {e}")
        
        # Register metadata in PostgreSQL
        if self.pg_adapter:
            try:
                self.pg_adapter.register_binary_file(
                    agent_id=self.agent_id,
                    object_path=object_path,
                    bucket=bucket,
                    content_type=content_type,
                    task_id=task_id,
                    size_bytes=file_size,
                    metadata=metadata
                )
            except Exception as e:
                print(f"Warning: Failed to register binary file metadata: {e}")
        
        return object_path
    
    def download_binary_file(self, bucket: str, object_path: str) -> bytes:
        """
        Download a binary file from MinIO.
        
        Args:
            bucket: Bucket name
            object_path: Object path
            
        Returns:
            File bytes
        """
        try:
            response = self.client.get_object(bucket, object_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise RuntimeError(f"Failed to download binary file: {e}")
    
    def get_presigned_url(
        self,
        bucket: str,
        object_path: str,
        expires_seconds: int = 3600
    ) -> str:
        """
        Get a presigned URL for downloading a file (frontend use case).
        
        Args:
            bucket: Bucket name
            object_path: Object path
            expires_seconds: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        from datetime import timedelta
        
        try:
            url = self.client.presigned_get_object(
                bucket,
                object_path,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")
    
    def list_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        limit: int = 1000
    ) -> list:
        """
        List objects in a bucket (metadata only, for evaluator).
        
        Args:
            bucket: Bucket name
            prefix: Optional prefix filter (e.g., 'agent1/' for agent1's files)
            limit: Maximum number of results
            
        Returns:
            List of object metadata dictionaries
        """
        try:
            objects = []
            for obj in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                objects.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": getattr(obj, 'content_type', None)
                })
                if len(objects) >= limit:
                    break
            return objects
        except S3Error as e:
            raise RuntimeError(f"Failed to list objects: {e}")
    
    def delete_object(self, bucket: str, object_path: str) -> bool:
        """
        Delete an object from MinIO.
        
        Args:
            bucket: Bucket name
            object_path: Object path
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            self.client.remove_object(bucket, object_path)
            return True
        except S3Error as e:
            print(f"Failed to delete object: {e}")
            return False

