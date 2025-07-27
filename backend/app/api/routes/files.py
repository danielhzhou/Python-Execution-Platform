"""
File management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.auth import get_current_user_id
from app.services.storage_service import storage_service

router = APIRouter()


class FileRequest(BaseModel):
    """File save request"""
    containerId: str
    path: str
    content: str


class FileInfo(BaseModel):
    """File information response"""
    id: str
    name: str
    path: str
    content: str
    language: str
    size: int
    lastModified: str


@router.post("/", response_model=FileInfo)
async def save_file(
    request: FileRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Save file content"""
    try:
        # Save file to storage
        file_path = f"{user_id}/{request.containerId}/{request.path}"
        success = await storage_service.save_file(file_path, request.content)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        # Determine language from file extension
        language = "python" if request.path.endswith(".py") else "text"
        
        return FileInfo(
            id=f"{request.containerId}:{request.path}",
            name=request.path.split("/")[-1],
            path=request.path,
            content=request.content,
            language=language,
            size=len(request.content.encode('utf-8')),
            lastModified=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.get("/", response_model=FileInfo)
async def get_file(
    containerId: str = Query(...),
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Get file content"""
    try:
        file_path = f"{user_id}/{containerId}/{path}"
        content = await storage_service.get_file(file_path)
        
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        language = "python" if path.endswith(".py") else "text"
        
        return FileInfo(
            id=f"{containerId}:{path}",
            name=path.split("/")[-1],
            path=path,
            content=content,
            language=language,
            size=len(content.encode('utf-8')),
            lastModified=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.get("/list", response_model=List[FileInfo])
async def list_files(
    containerId: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """List files in container"""
    try:
        file_prefix = f"{user_id}/{containerId}/"
        files = await storage_service.list_files(file_prefix)
        
        file_infos = []
        for file_path in files:
            try:
                content = await storage_service.get_file(file_path)
                if content is not None:
                    relative_path = file_path.replace(file_prefix, "")
                    language = "python" if relative_path.endswith(".py") else "text"
                    
                    file_infos.append(FileInfo(
                        id=f"{containerId}:{relative_path}",
                        name=relative_path.split("/")[-1],
                        path=relative_path,
                        content=content,
                        language=language,
                        size=len(content.encode('utf-8')),
                        lastModified=datetime.utcnow().isoformat()
                    ))
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return file_infos
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/")
async def delete_file(
    containerId: str = Query(...),
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a file"""
    try:
        file_path = f"{user_id}/{containerId}/{path}"
        success = await storage_service.delete_file(file_path)
        
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}") 