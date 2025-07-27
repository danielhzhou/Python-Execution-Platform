"""
Container management API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.container import (
    ContainerCreateRequest, 
    ContainerResponse, 
    ContainerInfo,
    ContainerStatus
)
from app.services.container_service import container_service
from app.services.websocket_service import websocket_service
from app.services.database_service import db_service
from app.core.auth import get_current_user_id, AuthUser, get_current_user

router = APIRouter()


@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new container for the authenticated user"""
    try:
        # Create container
        session = await container_service.create_container(
            user_id=user_id,
            project_id=request.project_id,
            project_name=request.project_name,
            initial_files=request.initial_files
        )
        
        # Generate WebSocket URL
        websocket_url = f"/api/v1/ws/terminal/{session.id}"
        
        return ContainerResponse(
            session_id=session.id,
            container_id=session.container_id,
            status=session.status,
            websocket_url=websocket_url
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create container: {str(e)}")


@router.get("/{session_id}/info", response_model=Optional[ContainerInfo])
async def get_container_info(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get container information for authenticated user"""
    # Verify user owns this session
    session = await db_service.get_terminal_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Container session not found")
    
    container_info = await container_service.get_container_info(session_id)
    if not container_info:
        raise HTTPException(status_code=404, detail="Container not found")
        
    return container_info


@router.post("/{session_id}/terminate")
async def terminate_container(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Terminate a container for authenticated user"""
    # Verify user owns this session
    session = await db_service.get_terminal_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Container session not found")
    
    success = await container_service.terminate_container(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to terminate container")
        
    return {"message": "Container terminated successfully"}


@router.post("/{session_id}/network/enable")
async def enable_network_access(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Enable network access for package installation"""
    # Verify user owns this session
    session = await db_service.get_terminal_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Container session not found")
    
    success = await container_service.enable_network_access(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable network access")
        
    return {"message": "Network access enabled"}


@router.post("/{session_id}/network/disable")
async def disable_network_access(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Disable network access"""
    # Verify user owns this session
    session = await db_service.get_terminal_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Container session not found")
    
    success = await container_service.disable_network_access(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disable network access")
        
    return {"message": "Network access disabled"}


@router.get("/{session_id}/stats")
async def get_session_stats(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get session statistics"""
    # Verify user owns this session
    session = await db_service.get_terminal_session(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Container session not found")
    
    stats = await websocket_service.get_session_stats(session_id)
    return stats


@router.get("/")
async def list_user_containers(
    user_id: str = Depends(get_current_user_id)
):
    """List all containers for the authenticated user"""
    # Get sessions from database
    sessions = await db_service.get_user_terminal_sessions(user_id)
    user_sessions = []
    
    for session in sessions:
        container_info = await container_service.get_container_info(session.id)
        user_sessions.append({
            "session_id": session.id,
            "container_id": session.container_id,
            "status": session.status,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "project_id": session.project_id,
            "container_info": container_info.dict() if container_info else None
        })
    
    return {"containers": user_sessions} 