"""
Supabase Storage service for file management
"""
import logging
import os
from typing import Optional, List, BinaryIO
from io import BytesIO

from app.core.supabase import get_supabase_client
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing files in Supabase Storage"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bucket_name = "project-files"
    
    async def upload_project_file(
        self, 
        project_id: str, 
        file_path: str, 
        file_content: bytes,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """Upload a file to Supabase Storage and create database record"""
        try:
            # Generate storage path
            storage_path = f"projects/{project_id}/{file_path}"
            
            # Upload to Supabase Storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": True  # Overwrite if exists
                }
            )
            
            if result.error:
                logger.error(f"Failed to upload file to storage: {result.error}")
                return None
            
            # Create or update database record
            file_name = os.path.basename(file_path)
            file_size = len(file_content)
            
            # Check if file already exists in database
            project_files = await db_service.get_project_files(project_id)
            existing_file = next((f for f in project_files if f.file_path == file_path), None)
            
            if existing_file:
                # Update existing file
                await db_service.update_project_file(
                    existing_file.id,
                    storage_path=storage_path,
                    file_size=file_size,
                    mime_type=content_type
                )
            else:
                # Create new file record
                await db_service.create_project_file(
                    project_id=project_id,
                    file_path=file_path,
                    file_name=file_name,
                    storage_path=storage_path,
                    file_size=file_size,
                    mime_type=content_type
                )
            
            return storage_path
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None
    
    async def download_project_file(self, project_id: str, file_path: str) -> Optional[bytes]:
        """Download a file from Supabase Storage"""
        try:
            storage_path = f"projects/{project_id}/{file_path}"
            
            result = self.supabase.storage.from_(self.bucket_name).download(storage_path)
            
            if result.error:
                logger.error(f"Failed to download file: {result.error}")
                return None
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    async def delete_project_file(self, project_id: str, file_path: str) -> bool:
        """Delete a file from Supabase Storage"""
        try:
            storage_path = f"projects/{project_id}/{file_path}"
            
            result = self.supabase.storage.from_(self.bucket_name).remove([storage_path])
            
            if result.error:
                logger.error(f"Failed to delete file: {result.error}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def get_file_url(self, project_id: str, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get a signed URL for a file"""
        try:
            storage_path = f"projects/{project_id}/{file_path}"
            
            result = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                storage_path, 
                expires_in
            )
            
            if result.error:
                logger.error(f"Failed to create signed URL: {result.error}")
                return None
            
            return result.data.get("signedURL")
            
        except Exception as e:
            logger.error(f"Error creating signed URL: {e}")
            return None
    
    async def list_project_files_in_storage(self, project_id: str) -> List[dict]:
        """List all files for a project in storage"""
        try:
            folder_path = f"projects/{project_id}/"
            
            result = self.supabase.storage.from_(self.bucket_name).list(folder_path)
            
            if result.error:
                logger.error(f"Failed to list files: {result.error}")
                return []
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    async def upload_text_file(
        self, 
        project_id: str, 
        file_path: str, 
        content: str
    ) -> Optional[str]:
        """Upload a text file (convenience method)"""
        return await self.upload_project_file(
            project_id=project_id,
            file_path=file_path,
            file_content=content.encode('utf-8'),
            content_type="text/plain"
        )
    
    async def download_text_file(self, project_id: str, file_path: str) -> Optional[str]:
        """Download a text file (convenience method)"""
        file_bytes = await self.download_project_file(project_id, file_path)
        if file_bytes:
            return file_bytes.decode('utf-8')
        return None
    
    async def ensure_bucket_exists(self) -> bool:
        """Ensure the storage bucket exists"""
        try:
            # List buckets to check if our bucket exists
            result = self.supabase.storage.list_buckets()
            
            # Handle both error response and direct list response
            if hasattr(result, 'error') and result.error:
                logger.error(f"Failed to list buckets: {result.error}")
                return False
            
            # Handle direct list response (some versions return list directly)
            if isinstance(result, list):
                buckets = result
            else:
                buckets = result.data or []
                
            bucket_names = [bucket.get("name") for bucket in buckets]
            
            if self.bucket_name not in bucket_names:
                # Create bucket
                create_result = self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={
                        "public": False,  # Private bucket
                        "allowed_mime_types": [
                            "text/plain",
                            "text/python",
                            "application/json",
                            "application/javascript",
                            "text/html",
                            "text/css",
                            "text/markdown",
                            "application/octet-stream"
                        ],
                        "file_size_limit": 10 * 1024 * 1024  # 10MB limit
                    }
                )
                
                if hasattr(create_result, 'error') and create_result.error:
                    logger.error(f"Failed to create bucket: {create_result.error}")
                    return False
                
                logger.info(f"Created storage bucket: {self.bucket_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            return False


# Global storage service instance
storage_service = StorageService() 