"""
Container management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from app.core.auth import get_current_user_id
from app.models.container import ContainerCreateRequest, ContainerResponse, TerminalSession
from app.services.container_service import container_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    replace_existing: bool = Query(False, description="Replace existing active container if one exists"),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new container for code execution"""
    try:
        logger.info(f"Creating container for user {user_id}")
        
        # If replace_existing is True, cleanup any existing containers first
        if replace_existing:
            logger.info("Cleaning up existing containers before creating new one")
            await cleanup_user_containers(user_id)
        
        session = await container_service.create_container(
            user_id=user_id,
            project_id=request.project_id,
            project_name=request.project_name,
            initial_files=request.initial_files or {}
        )
        
        # Generate WebSocket URL for terminal connection
        websocket_url = f"ws://localhost:8000/api/ws/terminal/{session.id}"
        
        logger.info(f"Container created successfully for user {user_id}: {session.id}")
        
        return ContainerResponse(
            session_id=str(session.id),  # Convert UUID to string
            container_id=str(session.container_id),  # Convert UUID to string
            status=session.status,  # Already a string from database
            websocket_url=websocket_url,
            user_id=str(session.user_id)  # Convert session.user_id UUID to string
        )
        
    except ValueError as e:
        logger.warning(f"Container creation validation error for user {user_id}: {str(e)}")
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
    except ImportError as e:
        logger.error(f"Missing dependency for container creation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Container service is not properly configured. Please check Docker installation and configuration."
        )
    except ConnectionError as e:
        logger.error(f"Docker connection error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Docker daemon. Please ensure Docker is running and accessible."
        )
    except Exception as e:
        logger.error(f"Unexpected error creating container for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create container: {str(e)}"
        )


@router.get("/{session_id}/info", response_model=ContainerResponse)
async def get_container_info(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get information about a specific container"""
    try:
        logger.info(f"Getting container info for session {session_id}, user {user_id}")
        
        session = await container_service.get_container_info(session_id)
        if not session:
            logger.warning(f"Container not found: {session_id}")
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Verify user owns this container
        if session.user_id != user_id:
            logger.warning(f"Access denied: user {user_id} tried to access container owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        websocket_url = f"ws://localhost:8000/api/ws/terminal/{session_id}"
        
        return ContainerResponse(
            session_id=str(session.id),  # Convert UUID to string
            container_id=str(session.container_id),  # Convert UUID to string
            status=session.status,  # Already a string from database
            websocket_url=websocket_url,
            user_id=str(session.user_id)  # Convert session.user_id UUID to string
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
        
        sessions = await container_service.list_user_containers(user_id)
        
        logger.info(f"Found {len(sessions)} containers for user {user_id}")
        
        return [
            ContainerResponse(
                session_id=str(session.id),  # Convert UUID to string
                container_id=str(session.container_id),  # Convert UUID to string
                status=session.status,  # Already a string from database
                websocket_url=f"ws://localhost:8000/api/ws/terminal/{session.id}",
                user_id=str(session.user_id)  # Convert session.user_id UUID to string
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
        session = await container_service.get_container_info(session_id)
        if not session:
            logger.warning(f"Container not found for termination: {session_id}")
            raise HTTPException(status_code=404, detail="Container not found")
        
        if session.user_id != user_id:
            logger.warning(f"Access denied: user {user_id} tried to terminate container owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = await container_service.terminate_container(session_id)
        
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
                success = await container_service.terminate_container(session.id)
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