"""
Container management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from app.core.auth import get_current_user_id
from app.models.container import ContainerCreateRequest, ContainerResponse, TerminalSession
from app.services.container_service import container_service

router = APIRouter()


@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    replace_existing: bool = Query(False, description="Replace existing active container if one exists"),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new container for code execution"""
    try:
        # If replace_existing is True, cleanup any existing containers first
        if replace_existing:
            await cleanup_user_containers(user_id)
        
        session = await container_service.create_container(
            user_id=user_id,
            project_id=request.project_id,
            project_name=request.project_name,
            initial_files=request.initial_files or {}
        )
        
        # Generate WebSocket URL for terminal connection
        websocket_url = f"ws://localhost:8000/api/containers/{session.id}/terminal"
        
        return ContainerResponse(
            session_id=session.id,
            container_id=session.container_id,
            status=session.status,
            websocket_url=websocket_url
        )
        
    except ValueError as e:
        if "already has an active container" in str(e):
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "User already has an active container",
                    "message": "You already have an active container. Please terminate it first or use replace_existing=true",
                    "suggestion": "Try calling /api/containers/cleanup first, or add ?replace_existing=true to this request"
                }
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create container: {str(e)}")


@router.get("/{session_id}/info", response_model=ContainerResponse)
async def get_container_info(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get information about a specific container"""
    try:
        session = await container_service.get_container_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Verify user owns this container
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        websocket_url = f"ws://localhost:8000/api/containers/{session_id}/terminal"
        
        return ContainerResponse(
            session_id=session.id,
            container_id=session.container_id,
            status=session.status,
            websocket_url=websocket_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ContainerResponse])
async def list_containers(user_id: str = Depends(get_current_user_id)):
    """List all containers for the current user"""
    try:
        sessions = await container_service.list_user_containers(user_id)
        
        return [
            ContainerResponse(
                session_id=session.id,
                container_id=session.container_id,
                status=session.status,
                websocket_url=f"ws://localhost:8000/api/containers/{session.id}/terminal"
            )
            for session in sessions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/terminate")
async def terminate_container(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Terminate a specific container"""
    try:
        # Verify user owns this container
        session = await container_service.get_container_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Container not found")
        
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = await container_service.terminate_container(session_id)
        
        if success:
            return {"message": "Container terminated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to terminate container")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_user_containers(user_id: str = Depends(get_current_user_id)):
    """Cleanup/terminate all active containers for the current user"""
    try:
        from app.services.database_service import db_service
        
        # Get all active containers for the user
        active_sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        
        terminated_count = 0
        errors = []
        
        for session in active_sessions:
            try:
                success = await container_service.terminate_container(session.id)
                if success:
                    terminated_count += 1
                else:
                    errors.append(f"Failed to terminate container {session.id}")
            except Exception as e:
                errors.append(f"Error terminating container {session.id}: {str(e)}")
        
        response = {
            "message": f"Cleanup completed. Terminated {terminated_count} containers.",
            "terminated_count": terminated_count
        }
        
        if errors:
            response["errors"] = errors
            response["message"] += f" {len(errors)} errors occurred."
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/status")
async def get_user_container_status(user_id: str = Depends(get_current_user_id)):
    """Get current container status for the user"""
    try:
        from app.services.database_service import db_service
        
        # Get all sessions for the user
        all_sessions = await db_service.get_user_terminal_sessions(user_id)
        active_sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        
        return {
            "user_id": user_id,
            "total_containers": len(all_sessions),
            "active_containers": len(active_sessions),
            "can_create_new": len(active_sessions) == 0,
            "active_container_ids": [session.id for session in active_sessions] if active_sessions else [],
            "max_containers_per_user": 1  # From settings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 