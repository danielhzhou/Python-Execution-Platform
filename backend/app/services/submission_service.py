"""
Submission service for handling code submissions and reviews
"""
import logging
import os
import zipfile
from datetime import datetime
from typing import List, Optional, Dict, Any
from io import BytesIO

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
        Upload files for a submission to Supabase storage
        files format: [{"path": str, "content": str, "name": str}]
        """
        try:
            # Create a zip file containing all submission files
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_data in files:
                    zip_file.writestr(file_data["path"], file_data["content"])
            
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            
            # Generate storage path
            storage_path = f"pending/{submission_id}/submission.zip"
            
            # Upload to Supabase Storage
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=zip_content,
                file_options={
                    "content-type": "application/zip",
                    "upsert": True
                }
            )
            
            if result.error:
                logger.error(f"Failed to upload submission files: {result.error}")
                return False
            
            # Update submission with storage path
            await db_service.update_submission(submission_id, storage_path=storage_path)
            
            # Create database records for each file
            for file_data in files:
                await db_service.create_submission_file(
                    submission_id=submission_id,
                    file_path=file_data["path"],
                    file_name=file_data["name"],
                    content=file_data["content"],
                    storage_path=storage_path,
                    file_size=len(file_data["content"].encode('utf-8')),
                    mime_type="text/plain"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading submission files: {e}")
            return False
    
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
            if result.error:
                logger.error(f"Failed to download submission for moving: {result.error}")
                return
            
            # Upload to new location
            upload_result = self.supabase.storage.from_(self.bucket_name).upload(
                path=new_path,
                file=result.data,
                file_options={
                    "content-type": "application/zip",
                    "upsert": True
                }
            )
            
            if upload_result.error:
                logger.error(f"Failed to upload to new location: {upload_result.error}")
                return
            
            # Delete from old location
            delete_result = self.supabase.storage.from_(self.bucket_name).remove([submission.storage_path])
            if delete_result.error:
                logger.warning(f"Failed to delete old file: {delete_result.error}")
            
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
            if result.error:
                logger.error(f"Failed to download submission: {result.error}")
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