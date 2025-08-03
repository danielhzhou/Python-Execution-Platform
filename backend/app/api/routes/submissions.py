"""
Submission API endpoints
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel

from app.core.auth import get_current_user, get_current_user_id
from app.models.container import User, UserRole, SubmissionStatus
from app.services.submission_service import submission_service
from app.services.database_service import db_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["submissions"])


# Request/Response Models
class CreateSubmissionRequest(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None


class SubmissionFileData(BaseModel):
    path: str
    content: str
    name: str


class SubmitFilesRequest(BaseModel):
    submission_id: str
    files: List[SubmissionFileData]


class ReviewSubmissionRequest(BaseModel):
    submission_id: str
    status: str  # "approved" or "rejected"
    comment: str


class SubmissionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    submitter_id: str
    project_id: str
    submitted_at: Optional[str]
    reviewed_at: Optional[str]
    reviewer_id: Optional[str]
    created_at: str
    updated_at: str


class SubmissionFileResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    content: str
    file_size: Optional[int]
    mime_type: Optional[str]


class SubmissionReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    status: str
    comment: str
    file_path: Optional[str]
    line_number: Optional[int]
    created_at: str


class SubmissionDetailResponse(BaseModel):
    submission: SubmissionResponse
    files: List[SubmissionFileResponse]
    reviews: List[SubmissionReviewResponse]


# Helper function to check if user is reviewer
async def require_reviewer(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.REVIEWER.value and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only reviewers can access this endpoint"
        )
    return current_user


# Helper function to check if user is submitter
async def require_submitter(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUBMITTER.value and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only submitters can access this endpoint"
        )
    return current_user


# Submitter endpoints
@router.post("/create", response_model=SubmissionResponse)
async def create_submission(
    request: CreateSubmissionRequest,
    current_user: User = Depends(require_submitter)
):
    """Create a new submission"""
    try:
        # Check if project exists, create a default one if not
        project = await db_service.get_project(request.project_id)
        if not project:
            # Create a default project for this submission
            project = await db_service.create_project(
                name=f"Container Project {request.project_id[:8]}",
                description="Auto-created project for submission",
                owner_id=current_user.id
            )
            # Use the new project ID
            project_id = project.id
        else:
            project_id = request.project_id
        
        submission = await submission_service.create_submission(
            submitter_id=current_user.id,
            project_id=project_id,
            title=request.title,
            description=request.description
        )
        
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create submission"
            )
        
        return SubmissionResponse(
            id=str(submission.id),  # Convert UUID to string
            title=submission.title,
            description=submission.description,
            status=submission.status,
            submitter_id=str(submission.submitter_id),  # Convert UUID to string
            project_id=str(submission.project_id),  # Convert UUID to string
            submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else None,
            reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            reviewer_id=str(submission.reviewer_id) if submission.reviewer_id else None,  # Convert UUID to string
            created_at=submission.created_at.isoformat(),
            updated_at=submission.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create submission"
        )


@router.post("/upload-files")
async def upload_submission_files(
    request: SubmitFilesRequest,
    current_user: User = Depends(require_submitter)
):
    """Upload files for a submission"""
    try:
        # Verify the submission belongs to the current user
        submission = await db_service.get_submission(request.submission_id)
        if not submission or submission.submitter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        # Convert files to the format expected by the service
        files = [
            {
                "path": file_data.path,
                "content": file_data.content,
                "name": file_data.name
            }
            for file_data in request.files
        ]
        
        success = await submission_service.upload_submission_files(
            submission_id=request.submission_id,
            files=files
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload files"
            )
        
        return {"message": "Files uploaded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading submission files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload files"
        )


@router.post("/submit/{submission_id}")
async def submit_for_review(
    submission_id: str,
    current_user: User = Depends(require_submitter)
):
    """Submit a submission for review"""
    try:
        # Verify the submission belongs to the current user
        submission = await db_service.get_submission(submission_id)
        if not submission or submission.submitter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        if submission.status != SubmissionStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft submissions can be submitted for review"
            )
        
        success = await submission_service.submit_for_review(submission_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit for review"
            )
        
        return {"message": "Submission submitted for review"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting for review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit for review"
        )


@router.get("/my-submissions", response_model=List[SubmissionResponse])
async def get_my_submissions(
    current_user: User = Depends(require_submitter)
):
    """Get all submissions by the current user"""
    try:
        submissions = await submission_service.get_user_submissions(current_user.id)
        
        return [
            SubmissionResponse(
                id=str(submission.id),  # Convert UUID to string
                title=submission.title,
                description=submission.description,
                status=submission.status,
                submitter_id=str(submission.submitter_id),  # Convert UUID to string
                project_id=str(submission.project_id),  # Convert UUID to string
                submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else None,
                reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
                reviewer_id=str(submission.reviewer_id) if submission.reviewer_id else None,  # Convert UUID to string
                created_at=submission.created_at.isoformat(),
                updated_at=submission.updated_at.isoformat()
            )
            for submission in submissions
        ]
        
    except Exception as e:
        logger.error(f"Error getting user submissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get submissions"
        )


# Reviewer endpoints
@router.get("/for-review", response_model=List[SubmissionResponse])
async def get_submissions_for_review(
    current_user: User = Depends(require_reviewer)
):
    """Get all submissions available for review"""
    try:
        submissions = await submission_service.get_submissions_for_review(current_user.id)
        
        return [
            SubmissionResponse(
                id=str(submission.id),  # Convert UUID to string
                title=submission.title,
                description=submission.description,
                status=submission.status,
                submitter_id=str(submission.submitter_id),  # Convert UUID to string
                project_id=str(submission.project_id),  # Convert UUID to string
                submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else None,
                reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
                reviewer_id=str(submission.reviewer_id) if submission.reviewer_id else None,  # Convert UUID to string
                created_at=submission.created_at.isoformat(),
                updated_at=submission.updated_at.isoformat()
            )
            for submission in submissions
        ]
        
    except Exception as e:
        logger.error(f"Error getting submissions for review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get submissions for review"
        )


@router.get("/{submission_id}/details", response_model=SubmissionDetailResponse)
async def get_submission_details(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed submission information with files and reviews"""
    try:
        submission_data = await submission_service.get_submission_with_files(submission_id)
        if not submission_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        submission = submission_data["submission"]
        
        # Check permissions - submitters can only see their own, reviewers can see all
        if (current_user.role == UserRole.SUBMITTER.value and 
            submission.submitter_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return SubmissionDetailResponse(
            submission=SubmissionResponse(
                id=str(submission.id),  # Convert UUID to string
                title=submission.title,
                description=submission.description,
                status=submission.status,
                submitter_id=str(submission.submitter_id),  # Convert UUID to string
                project_id=str(submission.project_id),  # Convert UUID to string
                submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else None,
                reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
                reviewer_id=str(submission.reviewer_id) if submission.reviewer_id else None,  # Convert UUID to string
                created_at=submission.created_at.isoformat(),
                updated_at=submission.updated_at.isoformat()
            ),
            files=[
                SubmissionFileResponse(
                    id=str(file.id),  # Convert UUID to string
                    file_path=file.file_path,
                    file_name=file.file_name,
                    content=file.content,
                    file_size=file.file_size,
                    mime_type=file.mime_type
                )
                for file in submission_data["files"]
            ],
            reviews=[
                SubmissionReviewResponse(
                    id=str(review.id),  # Convert UUID to string
                    reviewer_id=str(review.reviewer_id),  # Convert UUID to string
                    status=review.status,
                    comment=review.comment,
                    file_path=review.file_path,
                    line_number=review.line_number,
                    created_at=review.created_at.isoformat()
                )
                for review in submission_data["reviews"]
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting submission details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get submission details"
        )


@router.post("/review")
async def review_submission(
    request: ReviewSubmissionRequest,
    current_user: User = Depends(require_reviewer)
):
    """Review a submission (approve/reject)"""
    try:
        if request.status not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'approved' or 'rejected'"
            )
        
        success = await submission_service.review_submission(
            submission_id=request.submission_id,
            reviewer_id=current_user.id,
            status=request.status,
            comment=request.comment
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to review submission"
            )
        
        return {"message": f"Submission {request.status} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review submission"
        )


@router.get("/approved", response_model=List[dict])
async def get_approved_submissions(
    current_user: User = Depends(require_reviewer)
):
    """Get list of approved submissions with submitter info"""
    try:
        approved_submissions = await submission_service.get_approved_submissions()
        return approved_submissions
        
    except Exception as e:
        logger.error(f"Error getting approved submissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approved submissions"
        )


@router.get("/{submission_id}/download")
async def download_submission_files(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download submission files as a zip"""
    try:
        # Check permissions
        submission = await db_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        
        if (current_user.role == UserRole.SUBMITTER.value and 
            submission.submitter_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        file_data = await submission_service.download_submission_files(submission_id)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission files not found"
            )
        
        from fastapi.responses import Response
        return Response(
            content=file_data,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=submission_{submission_id}.zip"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading submission files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download submission files"
        )


# Admin endpoints
@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: User = Depends(get_current_user)
):
    """Update a user's role (admin only)"""
    try:
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can update user roles"
            )
        
        if role not in [UserRole.SUBMITTER.value, UserRole.REVIEWER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
        
        user = await db_service.update_user_role(user_id, role)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": f"User role updated to {role}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )