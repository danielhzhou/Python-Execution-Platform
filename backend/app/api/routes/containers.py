"""
Container management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging
import uuid
import os
from datetime import datetime

from app.core.auth import get_current_user_id
from app.models.container import ContainerCreateRequest, ContainerResponse, TerminalSession
from app.services.terminal_service import terminal_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create-local", response_model=ContainerResponse)
async def create_local_session(
    request: ContainerCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new local terminal session for development"""
    try:
        logger.info(f"Creating local terminal session for user {user_id}")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Use current working directory or create a workspace
        workspace_dir = os.path.join(os.getcwd(), "workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Create terminal session
        success = await terminal_service.create_terminal_session(session_id, workspace_dir)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create terminal session")
        
        # Generate WebSocket URL for terminal connection
        websocket_url = f"ws://localhost:8000/api/containers/terminal/{session_id}"
        
        logger.info(f"Local terminal session created successfully: {session_id}")
        
        return ContainerResponse(
            session_id=session_id,
            container_id=session_id,  # For local dev, session_id == container_id
            status="running",
            websocket_url=websocket_url,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create local terminal session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create terminal session: {str(e)}")


@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    replace_existing: bool = Query(False, description="Replace existing active container if one exists"),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new container for code execution (redirects to local for development)"""
    # For development, redirect to local session creation
    return await create_local_session(request, user_id)


@router.get("/{session_id}/info", response_model=ContainerResponse)
async def get_container_info(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get information about a specific container"""
    try:
        logger.info(f"Getting container info for session {session_id}, user {user_id}")
        
        session = await terminal_service.get_terminal_session_info(session_id)
        if not session:
            logger.warning(f"Container not found: {session_id}")
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Verify user owns this container
        if session["user_id"] != user_id:
            logger.warning(f"Access denied: user {user_id} tried to access container owned by {session['user_id']}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        websocket_url = f"ws://localhost:8000/api/containers/terminal/{session_id}"
        
        return ContainerResponse(
            session_id=str(session["id"]),  # Convert UUID to string
            container_id=str(session["id"]),  # For local dev, session_id == container_id
            status=session["status"],  # Already a string
            websocket_url=websocket_url,
            user_id=str(session["user_id"])  # Convert session.user_id UUID to string
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting container info for {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get container info: {str(e)}")


@router.get("/", response_model=List[ContainerResponse])
async def list_containers(user_id: str = Depends(get_current_user_id)):
    """List all containers for the current user"""
    try:
        logger.info(f"Listing containers for user {user_id}")
        
        sessions = await terminal_service.list_user_terminal_sessions(user_id)
        
        logger.info(f"Found {len(sessions)} containers for user {user_id}")
        
        return [
            ContainerResponse(
                session_id=str(session["id"]),  # Convert UUID to string
                container_id=str(session["id"]),  # For local dev, session_id == container_id
                status=session["status"],  # Already a string
                websocket_url=f"ws://localhost:8000/api/containers/terminal/{session['id']}",
                user_id=str(session["user_id"])  # Convert session.user_id UUID to string
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error listing containers for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to list containers: {str(e)}"
        )


@router.post("/{session_id}/terminate")
async def terminate_container(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Terminate a specific container"""
    try:
        logger.info(f"Terminating container {session_id} for user {user_id}")
        
        # Verify user owns this container
        session = await terminal_service.get_terminal_session_info(session_id)
        if not session:
            logger.warning(f"Container not found for termination: {session_id}")
            raise HTTPException(status_code=404, detail="Container not found")
        
        if session["user_id"] != user_id:
            logger.warning(f"Access denied: user {user_id} tried to terminate container owned by {session['user_id']}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = await terminal_service.terminate_terminal_session(session_id)
        
        if success:
            logger.info(f"Container {session_id} terminated successfully")
            return {"message": "Container terminated successfully"}
        else:
            logger.error(f"Failed to terminate container {session_id}")
            raise HTTPException(status_code=400, detail="Failed to terminate container")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating container {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to terminate container: {str(e)}")


@router.post("/cleanup")
async def cleanup_user_containers(user_id: str = Depends(get_current_user_id)):
    """Cleanup/terminate all active containers for the current user"""
    try:
        logger.info(f"Cleaning up containers for user {user_id}")
        
        from app.services.database_service import db_service
        
        # Get all active containers for the user
        active_sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        
        logger.info(f"Found {len(active_sessions)} active containers for cleanup")
        
        terminated_count = 0
        errors = []
        
        for session in active_sessions:
            try:
                logger.info(f"Terminating container {session.id}")
                success = await terminal_service.terminate_terminal_session(session.id)
                if success:
                    terminated_count += 1
                else:
                    errors.append(f"Failed to terminate container {session.id}")
            except Exception as e:
                error_msg = f"Error terminating container {session.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        response = {
            "message": f"Cleanup completed. Terminated {terminated_count} containers.",
            "terminated_count": terminated_count
        }
        
        if errors:
            response["errors"] = errors
            response["message"] += f" {len(errors)} errors occurred."
            logger.warning(f"Cleanup completed with {len(errors)} errors")
        else:
            logger.info(f"Cleanup completed successfully, terminated {terminated_count} containers")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during cleanup for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/status")
async def get_user_container_status(user_id: str = Depends(get_current_user_id)):
    """Get current container status for the user"""
    try:
        logger.info(f"Getting container status for user {user_id}")
        
        from app.services.database_service import db_service
        
        # Get all sessions for the user
        all_sessions = await db_service.get_user_terminal_sessions(user_id)
        active_sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        
        status = {
            "user_id": user_id,
            "total_containers": len(all_sessions),
            "active_containers": len(active_sessions),
            "can_create_new": len(active_sessions) == 0,
            "active_container_ids": [session.id for session in active_sessions] if active_sessions else [],
            "max_containers_per_user": 1  # From settings
        }
        
        logger.info(f"Container status for user {user_id}: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting container status for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get container status: {str(e)}") 