# Storage adapter: MinIO client for uploading screenshots
"""MinIO storage adapter for uploading screenshots."""

import os
from pathlib import Path
from typing import Optional
from uuid import uuid4
from minio import Minio
from minio.error import S3Error


class MinioClientWrapper:
    """MinIO client wrapper for uploading screenshots."""
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool,
        agent_id: str
    ):
        """
        Initialize MinIO client.
        
        Args:
            endpoint: MinIO endpoint (e.g., 'minio:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Use HTTPS (True) or HTTP (False)
            agent_id: Agent identifier
        """
        self.endpoint = endpoint
        self.agent_id = agent_id
        
        # Initialize MinIO client
        try:
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MinIO client: {e}")
        
        # Ensure bucket exists
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create screenshots bucket if it doesn't exist."""
        bucket_name = "screenshots"
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket {bucket_name}: {e}")
    
    def _normalize_agent_id(self, agent_id: str) -> str:
        """
        Normalize agent_id to format: agent{ID}
        
        Examples:
            'agent1' -> 'agent1'
            'agent1-cua' -> 'agent1'
            '1' -> 'agent1'
            'agent2' -> 'agent2'
        
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
    
    def upload_file(self, local_path: str) -> str:
        """
        Upload a file to MinIO screenshots bucket.
        
        Args:
            local_path: Local file path to upload
            
        Returns:
            Object path (e.g., 'agent1/screenshots/uuid.png')
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")
        
        # Get file extension
        ext = Path(local_path).suffix
        if not ext:
            ext = ".png"  # Default to .png for screenshots
        
        # Normalize agent_id to ensure consistent format
        normalized_agent_id = self._normalize_agent_id(self.agent_id)
        
        # Generate object name: {normalized_agent_id}/screenshots/{uuid}{ext}
        object_name = f"{normalized_agent_id}/screenshots/{uuid4()}{ext}"
        
        # Upload file
        try:
            self.client.fput_object(
                "screenshots",
                object_name,
                local_path
            )
            return object_name
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to MinIO: {e}")

