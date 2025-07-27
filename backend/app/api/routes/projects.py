"""
Project management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional

from app.models.container import (
    ProjectCreateRequest, ProjectResponse, Project
)
from app.services.database_service import db_service
from app.services.storage_service import storage_service
# from app.core.auth import get_current_user_id
from app.core.mock_auth import get_mock_user_id

router = APIRouter()

@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Create a new project for the authenticated user"""
    try:
        project = await db_service.create_project(
            name=request.name,
            owner_id=user_id,
            description=request.description,
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
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
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
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Get a specific project"""
    try:
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if user owns the project or it's public
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
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Update a project"""
    try:
        # Check if project exists and user owns it
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update project
        updated_project = await db_service.update_project(
            project_id,
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )
        
        if not updated_project:
            raise HTTPException(status_code=500, detail="Failed to update project")
        
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
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Delete a project"""
    try:
        # Check if project exists and user owns it
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete project
        success = await db_service.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete project")
        
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """List all files in a project"""
    try:
        # Check if project exists and user has access
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id and not project.is_public:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get project files
        files = await db_service.get_project_files(project_id)
        
        return {
            "project_id": project_id,
            "files": [
                {
                    "id": file.id,
                    "file_path": file.file_path,
                    "file_name": file.file_name,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "created_at": file.created_at,
                    "updated_at": file.updated_at
                }
                for file in files
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list project files: {str(e)}")


@router.get("/{project_id}/files/{file_id}")
async def get_project_file(
    project_id: str,
    file_id: str,
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Get a specific project file with content"""
    try:
        # Check if project exists and user has access
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id and not project.is_public:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get project file
        file = await db_service.get_project_file(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "id": file.id,
            "project_id": file.project_id,
            "file_path": file.file_path,
            "file_name": file.file_name,
            "content": file.content,
            "storage_path": file.storage_path,
            "file_size": file.file_size,
            "mime_type": file.mime_type,
            "created_at": file.created_at,
            "updated_at": file.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project file: {str(e)}")


@router.post("/{project_id}/files/upload")
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    file_path: str = Form(...),
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Upload a file to a project"""
    try:
        # Check if project exists and user owns it
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Read file content
        file_content = await file.read()
        
        # Upload to storage
        storage_path = await storage_service.upload_project_file(
            project_id=project_id,
            file_path=file_path,
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream"
        )
        
        if not storage_path:
            raise HTTPException(status_code=500, detail="Failed to upload file")
        
        return {
            "message": "File uploaded successfully",
            "file_path": file_path,
            "storage_path": storage_path,
            "file_size": len(file_content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.put("/{project_id}/files/{file_id}")
async def update_project_file(
    project_id: str,
    file_id: str,
    content: str = Form(...),
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Update a project file's content"""
    try:
        # Check if project exists and user owns it
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get and verify file
        file = await db_service.get_project_file(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update file content
        if file.storage_path:
            # File is in storage, update storage
            storage_path = await storage_service.upload_text_file(
                project_id=project_id,
                file_path=file.file_path,
                content=content
            )
            if not storage_path:
                raise HTTPException(status_code=500, detail="Failed to update file in storage")
        else:
            # File content is in database, update database
            await db_service.update_project_file(
                file_id,
                content=content,
                file_size=len(content.encode('utf-8'))
            )
        
        return {"message": "File updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


@router.delete("/{project_id}/files/{file_id}")
async def delete_project_file(
    project_id: str,
    file_id: str,
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Delete a project file"""
    try:
        # Check if project exists and user owns it
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get and verify file
        file = await db_service.get_project_file(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete from storage if exists
        if file.storage_path:
            await storage_service.delete_project_file(project_id, file.file_path)
        
        # Delete from database
        success = await db_service.delete_project_file(file_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/{project_id}/files/{file_id}/download")
async def download_project_file(
    project_id: str,
    file_id: str,
    # user_id: str = Depends(get_current_user_id)
    user_id: str = Depends(get_mock_user_id)
):
    """Get a download URL for a project file"""
    try:
        # Check if project exists and user has access
        project = await db_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project.owner_id != user_id and not project.is_public:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get file
        file = await db_service.get_project_file(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(status_code=404, detail="File not found")
        
        if file.storage_path:
            # File is in storage, get signed URL
            signed_url = await storage_service.get_file_url(project_id, file.file_path)
            if not signed_url:
                raise HTTPException(status_code=500, detail="Failed to generate download URL")
            
            return {"download_url": signed_url, "expires_in": 3600}
        else:
            # File content is in database, return directly
            return {
                "content": file.content,
                "file_name": file.file_name,
                "mime_type": file.mime_type
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}") 