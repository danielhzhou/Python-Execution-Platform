"""
Project management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.container import (
    ProjectCreateRequest, ProjectResponse, SubmissionCreateRequest, 
    SubmissionResponse, User, Project, Submission
)
from app.services.database_service import db_service
from app.services.storage_service import storage_service
from app.core.auth import get_current_user_id

router = APIRouter()

@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new project for the authenticated user"""
    try:
        project = await db_service.create_project(
            name=request.name,
            description=request.description,
            owner_id=user_id,
            is_public=request.is_public
        )
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_public=project.is_public,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/", response_model=List[ProjectResponse])
async def list_user_projects(
    user_id: str = Depends(get_current_user_id)
):
    """List all projects for the authenticated user"""
    try:
        projects = await db_service.get_user_projects(user_id)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                owner_id=project.owner_id,
                is_public=project.is_public,
                created_at=project.created_at,
                updated_at=project.updated_at
            )
            for project in projects
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user has access to this project
        if project.owner_id != user_id and not project.is_public:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            is_public=project.is_public,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Update a project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user owns this project
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        updated_project = await db_service.update_project(
            project_id=project_id,
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )
        
        return ProjectResponse(
            id=updated_project.id,
            name=updated_project.name,
            description=updated_project.description,
            owner_id=updated_project.owner_id,
            is_public=updated_project.is_public,
            created_at=updated_project.created_at,
            updated_at=updated_project.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user owns this project
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        await db_service.delete_project(project_id)
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.post("/{project_id}/files")
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    file_path: str = "",
    user_id: str = Depends(get_current_user_id)
):
    """Upload a file to a project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user owns this project
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Read file content
        content = await file.read()
        
        # Save file to project
        project_file = await db_service.create_project_file(
            project_id=project_id,
            file_path=file_path or file.filename,
            file_name=file.filename,
            content=content.decode('utf-8') if file.content_type.startswith('text/') else None,
            mime_type=file.content_type,
            file_size=len(content)
        )
        
        return {
            "id": project_file.id,
            "file_path": project_file.file_path,
            "file_name": project_file.file_name,
            "mime_type": project_file.mime_type,
            "file_size": project_file.file_size,
            "created_at": project_file.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """List files in a project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user has access to this project
        if project.owner_id != user_id and not project.is_public:
            raise HTTPException(status_code=403, detail="Access denied")
        
        files = await db_service.get_project_files(project_id)
        return [
            {
                "id": f.id,
                "file_path": f.file_path,
                "file_name": f.file_name,
                "mime_type": f.mime_type,
                "file_size": f.file_size,
                "created_at": f.created_at,
                "updated_at": f.updated_at
            }
            for f in files
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


# Submission endpoints
@router.post("/submissions", response_model=SubmissionResponse)
async def create_submission(
    request: SubmissionCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new code submission"""
    try:
        # Verify user owns the project
        project = await db_service.get_project(request.project_id)
        if not project or project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        submission = await db_service.create_submission(
            owner_id=user_id,
            project_id=request.project_id,
            title=request.title,
            description=request.description,
            file_paths=request.file_paths
        )
        
        return SubmissionResponse(
            id=submission.id,
            user_id=submission.owner_id,
            project_id=submission.project_id,
            title=submission.title,
            description=submission.description,
            status=submission.status,
            created_at=submission.created_at,
            submitted_at=submission.submitted_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create submission: {str(e)}")


@router.get("/submissions")
async def list_submissions(
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """List submissions (for reviewers) or user's own submissions"""
    try:
        # For now, return all submissions - in production you'd check reviewer permissions
        submissions = await db_service.get_submissions(status=status)
        
        return [
            {
                "id": s.id,
                "user_id": s.owner_id,
                "project_id": s.project_id,
                "title": s.title,
                "description": s.description,
                "status": s.status,
                "created_at": s.created_at,
                "submitted_at": s.submitted_at,
                "reviewed_at": s.reviewed_at
            }
            for s in submissions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list submissions: {str(e)}")


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific submission"""
    try:
        submission = await db_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check access - owner or reviewer can view
        # For now, allow any authenticated user to view
        
        # Get submission files
        files = await db_service.get_submission_files(submission_id)
        
        return {
            "id": submission.id,
            "user_id": submission.owner_id,
            "project_id": submission.project_id,
            "title": submission.title,
            "description": submission.description,
            "status": submission.status,
            "created_at": submission.created_at,
            "submitted_at": submission.submitted_at,
            "reviewed_at": submission.reviewed_at,
            "files": [
                {
                    "id": f.id,
                    "file_path": f.file_path,
                    "file_name": f.file_name,
                    "content": f.content,
                    "diff": f.diff
                }
                for f in files
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get submission: {str(e)}")


@router.post("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: str,
    review_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
):
    """Review a submission (approve/reject)"""
    try:
        submission = await db_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # In production, check if user is a reviewer
        
        approved = review_data.get("approved", False)
        feedback = review_data.get("feedback", "")
        
        # Update submission status
        new_status = "approved" if approved else "rejected"
        await db_service.update_submission_status(
            submission_id=submission_id,
            status=new_status,
            reviewer_id=user_id
        )
        
        # Add review comment
        if feedback:
            await db_service.create_submission_review(
                submission_id=submission_id,
                reviewer_id=user_id,
                comment=feedback
            )
        
        return {
            "message": f"Submission {new_status}",
            "status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review submission: {str(e)}")


@router.post("/submissions/{submission_id}/submit")
async def submit_for_review(
    submission_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Submit a draft for review"""
    try:
        submission = await db_service.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check if user owns this submission
        if submission.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update status to submitted
        await db_service.update_submission_status(
            submission_id=submission_id,
            status="submitted"
        )
        
        return {"message": "Submission sent for review"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit for review: {str(e)}") 