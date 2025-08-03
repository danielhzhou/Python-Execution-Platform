"""
Submission service for handling code submissions and reviews
"""
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.supabase import get_supabase_client
from app.services.database_service import db_service
from app.models.container import Submission, SubmissionFile, SubmissionStatus, UserRole

logger = logging.getLogger(__name__)


class SubmissionService:
    """Service for managing code submissions"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bucket_name = "submissions"
    
    async def create_submission(
        self, 
        submitter_id: str, 
        project_id: str, 
        title: str, 
        description: Optional[str] = None
    ) -> Optional[Submission]:
        """Create a new submission"""
        try:
            submission = await db_service.create_submission(
                submitter_id=submitter_id,
                project_id=project_id,
                title=title,
                description=description
            )
            return submission
        except Exception as e:
            logger.error(f"Error creating submission: {e}")
            return None
    
    async def upload_submission_files(
        self, 
        submission_id: str, 
        files: List[Dict[str, Any]]
    ) -> bool:
        """
        Upload files for a submission to Supabase storage as individual files
        files format: [{"path": str, "content": str, "name": str}]
        """
        try:
            uploaded_files = []
            
            # Upload each file individually
            for file_data in files:
                # Generate storage path for individual file
                # Use file path but sanitize it for storage
                sanitized_path = file_data["path"].replace("/", "_").replace("\\", "_")
                storage_path = f"pending/{submission_id}/{sanitized_path}"
                
                # Convert content to bytes
                file_content = file_data["content"].encode('utf-8')
                
                # Determine MIME type based on file extension
                mime_type = self._get_mime_type(file_data["name"])
                
                # Upload to Supabase Storage
                result = self.supabase.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=file_content,
                    file_options={
                        "content-type": mime_type,
                        "upsert": "true"
                    }
                )
                
                # Check if upload was successful
                if not result:
                    logger.error(f"Failed to upload file {file_data['name']}: No response")
                    continue
                
                # Create database record for this file
                await db_service.create_submission_file(
                    submission_id=submission_id,
                    file_path=file_data["path"],
                    file_name=file_data["name"],
                    content=file_data["content"],
                    storage_path=storage_path,
                    file_size=len(file_content),
                    mime_type=mime_type
                )
                
                uploaded_files.append(storage_path)
            
            if not uploaded_files:
                logger.error("No files were successfully uploaded")
                return False
            
            # Update submission with folder path (not specific file)
            folder_path = f"pending/{submission_id}/"
            await db_service.update_submission(submission_id, storage_path=folder_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading submission files: {e}")
            return False
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'py': 'text/x-python',
            'js': 'text/javascript',
            'ts': 'text/typescript',
            'html': 'text/html',
            'css': 'text/css',
            'json': 'application/json',
            'md': 'text/markdown',
            'txt': 'text/plain',
            'yml': 'text/yaml',
            'yaml': 'text/yaml',
            'xml': 'text/xml',
            'sql': 'text/sql',
            'sh': 'text/x-shellscript',
            'dockerfile': 'text/plain',
            'gitignore': 'text/plain',
            'env': 'text/plain',
        }
        return mime_types.get(extension, 'text/plain')
    
    async def submit_for_review(self, submission_id: str) -> bool:
        """Submit a submission for review"""
        try:
            # Update submission status and timestamp
            await db_service.update_submission(
                submission_id=submission_id,
                status=SubmissionStatus.SUBMITTED.value,
                submitted_at=datetime.utcnow()
            )
            return True
        except Exception as e:
            logger.error(f"Error submitting for review: {e}")
            return False
    
    async def get_submissions_for_review(self, reviewer_id: str) -> List[Submission]:
        """Get all submissions available for review"""
        try:
            # Get all submitted submissions
            submissions = await db_service.get_submissions_by_status(
                SubmissionStatus.SUBMITTED.value
            )
            return submissions
        except Exception as e:
            logger.error(f"Error getting submissions for review: {e}")
            return []
    
    async def get_user_submissions(self, user_id: str) -> List[Submission]:
        """Get all submissions by a user"""
        try:
            submissions = await db_service.get_submissions_by_submitter(user_id)
            return submissions
        except Exception as e:
            logger.error(f"Error getting user submissions: {e}")
            return []
    
    async def review_submission(
        self, 
        submission_id: str, 
        reviewer_id: str, 
        status: str, 
        comment: str
    ) -> bool:
        """Review a submission (approve/reject)"""
        try:
            # Create review record
            await db_service.create_submission_review(
                submission_id=submission_id,
                reviewer_id=reviewer_id,
                status=status,
                comment=comment
            )
            
            # Update submission status
            new_status = SubmissionStatus.APPROVED.value if status == "approved" else SubmissionStatus.REJECTED.value
            await db_service.update_submission(
                submission_id=submission_id,
                status=new_status,
                reviewer_id=reviewer_id,
                reviewed_at=datetime.utcnow()
            )
            
            # Move files to appropriate folder in storage
            submission = await db_service.get_submission(submission_id)
            if submission and submission.storage_path:
                await self._move_submission_files(submission, status)
            
            return True
            
        except Exception as e:
            logger.error(f"Error reviewing submission: {e}")
            return False
    
    async def _move_submission_files(self, submission: Submission, review_status: str):
        """Move submission files to approved/rejected folder"""
        try:
            if not submission.storage_path:
                return
            
            # Determine target folder
            folder = "approved" if review_status == "approved" else "rejected"
            new_path = f"{folder}/{submission.id}/submission.zip"
            
            # Download the file
            result = self.supabase.storage.from_(self.bucket_name).download(submission.storage_path)
            # Check if download was successful
            if not result:
                logger.error(f"Failed to download submission for moving: No response")
                return
            
            # Upload to new location
            upload_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=new_path,
                file=result.data,
                file_options={
                    "content-type": "application/zip",
                    "upsert": "true"
                }
            )
            
            # Check if upload was successful
            if not upload_result:
                logger.error(f"Failed to upload to new location: No response")
                return
            
            # Delete from old location
            delete_result = self.supabase.storage.from_(self.bucket_name).remove([submission.storage_path])
            # Check if delete was successful (non-critical)
            if not delete_result:
                logger.warning(f"Failed to delete old file: No response")
            
            # Update submission storage path
            await db_service.update_submission(submission.id, storage_path=new_path)
            
        except Exception as e:
            logger.error(f"Error moving submission files: {e}")
    
    async def download_submission_files(self, submission_id: str) -> Optional[bytes]:
        """Download submission files as a zip"""
        try:
            submission = await db_service.get_submission(submission_id)
            if not submission or not submission.storage_path:
                return None
            
            result = self.supabase.storage.from_(self.bucket_name).download(submission.storage_path)
            # Check if download was successful
            if not result:
                logger.error(f"Failed to download submission: No response")
                return None
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error downloading submission files: {e}")
            return None
    
    async def get_submission_with_files(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get submission with all its files"""
        try:
            submission = await db_service.get_submission(submission_id)
            if not submission:
                return None
            
            files = await db_service.get_submission_files(submission_id)
            reviews = await db_service.get_submission_reviews(submission_id)
            
            return {
                "submission": submission,
                "files": files,
                "reviews": reviews
            }
            
        except Exception as e:
            logger.error(f"Error getting submission with files: {e}")
            return None
    
    async def get_approved_submissions(self) -> List[Dict[str, Any]]:
        """Get list of approved submissions with submitter info"""
        try:
            submissions = await db_service.get_submissions_by_status(SubmissionStatus.APPROVED.value)
            result = []
            
            for submission in submissions:
                submitter = await db_service.get_user(submission.submitter_id)
                result.append({
                    "submission_id": submission.id,
                    "title": submission.title,
                    "submitter_email": submitter.email if submitter else "Unknown",
                    "submitter_id": submission.submitter_id,
                    "submitted_at": submission.submitted_at,
                    "reviewed_at": submission.reviewed_at
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting approved submissions: {e}")
            return []


# Global instance
submission_service = SubmissionService()