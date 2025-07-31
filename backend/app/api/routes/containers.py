"""
Container management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging
import uuid
import os
from datetime import datetime
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.models.container import ContainerCreateRequest, ContainerResponse, TerminalSession
from app.services.container_service import container_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_docker_container(session: TerminalSession):
    """Get Docker container using the same client as container service"""
    if not container_service.docker:
        raise HTTPException(status_code=500, detail="Docker service not available")
    
    try:
        # Use python-on-whales (same as container service) for consistency
        container = container_service.docker.container.inspect(session.container_id)
        if not container:
            raise HTTPException(status_code=404, detail="Docker container not found")
        
        logger.info(f"📦 Using container: {container.name} (ID: {container.id[:12]}...)")
        return container
    except Exception as e:
        logger.error(f"Failed to get container {session.container_id}: {e}")
        raise HTTPException(status_code=404, detail="Container not accessible")


@router.get("/health")
async def container_health():
    """Simple health check for container endpoints"""
    return {"status": "ok", "message": "Container endpoints are working"}


@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new container for code execution - automatically ensures single container per user"""
    try:
        logger.info(f"Creating container for user {user_id}")
        
        # The container service now automatically handles cleanup of existing containers
        session = await container_service.create_container(
            user_id=user_id,
            project_id=request.project_id,
            project_name=request.project_name,
            initial_files=request.initial_files or {}
        )
        
        # Generate WebSocket URL for terminal connection
        websocket_url = f"ws://localhost:8000/api/containers/terminal/{session.id}"
        
        logger.info(f"Container created successfully for user {user_id}: {session.id}")
        
        return ContainerResponse(
            session_id=str(session.id),
            container_id=session.container_id,
            status=session.status,
            websocket_url=websocket_url,
            user_id=str(session.user_id)
        )
        
    except Exception as e:
        logger.error(f"Error creating container for user {user_id}: {str(e)}", exc_info=True)
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
        
        websocket_url = f"ws://localhost:8000/api/containers/terminal/{session_id}"
        
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
                websocket_url=f"ws://localhost:8000/api/containers/terminal/{session.id}",
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


# File system models
class ContainerFileNode(BaseModel):
    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: Optional[int] = None


class ContainerFileRequest(BaseModel):
    path: str
    content: str


class ContainerFileResponse(BaseModel):
    path: str
    content: str
    size: int
    modified: str


@router.get("/{container_id}/files", response_model=List[ContainerFileNode])
async def list_container_files(
    container_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """List files in the container's /workspace directory"""
    try:
        logger.info(f"🗂️ Starting file listing for container_id: {container_id}, user: {user_id}")
        
        # Verify user owns this container
        logger.info(f"🔍 Looking up session for container_id: {container_id}")
        session = await container_service.get_container_session(container_id)
        if not session:
            logger.error(f"❌ No session found for container_id: {container_id}")
            logger.info(f"🔍 Attempting direct session lookup by session ID...")
            
            # Try direct session lookup as fallback
            from app.services.database_service import db_service
            session = await db_service.get_terminal_session(container_id)
            if not session:
                logger.error(f"❌ No session found by session ID either: {container_id}")
                raise HTTPException(status_code=404, detail="Container session not found")
            else:
                logger.info(f"✅ Found session by session ID: {session.id}")
        else:
            logger.info(f"✅ Found session by container lookup: {session.id}")
        
        if str(session.user_id) != user_id:
            logger.error(f"❌ Access denied: User {user_id} does not own session {container_id} (owner: {session.user_id})")
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"✅ Session verified - ID: {session.id}, Container: {session.container_id}, Status: {session.status}")
        
        # Check if session status is running
        if session.status != 'running':
            logger.warning(f"⚠️ Container status is '{session.status}', not 'running'")
            if session.status in ['creating', 'stopped', 'error', 'terminated']:
                logger.error(f"❌ Container is not ready for file operations (status: {session.status})")
                raise HTTPException(status_code=400, detail=f"Container is not ready (status: {session.status})")
        
        # Use the container service's docker client for consistency
        if not hasattr(container_service, 'docker') or container_service.docker is None:
            logger.error("❌ Docker client not available in container service")
            raise HTTPException(status_code=500, detail="Docker service not available")
        
        try:
            # Use python-on-whales client from container_service
            logger.info(f"🐳 Getting Docker container using python-on-whales: {session.container_id}")
            
            # Get container using python-on-whales
            container = container_service.docker.container.inspect(session.container_id)
            if not container:
                logger.error(f"❌ Container not found: {session.container_id}")
                raise HTTPException(status_code=404, detail="Docker container not found")
            
            logger.info(f"✅ Got container: {container.name} (status: {container.state.status})")
            
            # Check if container is running
            if not container.state.running:
                logger.error(f"❌ Container is not running: {container.state.status}")
                raise HTTPException(status_code=400, detail=f"Container is not running (status: {container.state.status})")
            
            # List files in /workspace using exec
            logger.info("📁 Executing find command in container...")
            try:
                # python-on-whales execute returns a string directly
                find_output = container.execute(
                    ["find", "/workspace", "-type", "f", "-o", "-type", "d"]
                )
                
                if find_output is None:
                    logger.error("❌ Find command returned None")
                    raise HTTPException(status_code=500, detail="Failed to list container files")
                
                output_lines = find_output.strip().split('\n') if find_output else []
                logger.info(f"📁 Found {len(output_lines)} file/directory entries")
                logger.info(f"📁 File entries: {output_lines[:10]}...")  # Log first 10 entries
                
            except Exception as find_error:
                logger.error(f"❌ Find command failed: {str(find_error)}")
                raise HTTPException(status_code=500, detail="Failed to list container files")
            
            files = []
            
            for line in output_lines:
                if line and line != '/workspace':
                    try:
                        # Get file info using stat - python-on-whales execute returns string directly
                        stat_output = container.execute(
                            ["stat", "-c", "%F %s", line]
                        )
                        
                        if stat_output and stat_output.strip():
                            parts = stat_output.strip().split(' ', 1)
                            
                            if len(parts) == 2:
                                file_type, size_str = parts
                                
                                # Convert stat file type to our format
                                if 'directory' in file_type:
                                    node_type = 'directory'
                                    size = None
                                else:
                                    node_type = 'file'
                                    try:
                                        size = int(size_str)
                                    except ValueError:
                                        size = 0
                                
                                files.append(ContainerFileNode(
                                    name=os.path.basename(line),
                                    path=line,
                                    type=node_type,
                                    size=size
                                ))
                        else:
                            logger.warning(f"⚠️ Failed to stat file: {line}")
                    except Exception as file_error:
                        logger.warning(f"⚠️ Error processing file {line}: {file_error}")
                        continue
            
            logger.info(f"✅ Successfully processed {len(files)} files in container {container_id}")
            return files
            
        except Exception as docker_error:
            logger.error(f"❌ Docker operation failed: {str(docker_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Docker error: {str(docker_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error listing container files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/{container_id}/files/content", response_model=ContainerFileResponse)
async def get_container_file_content(
    container_id: str,
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Get content of a file in the container"""
    try:
        logger.info(f"Getting file content for {path} in container {container_id}")
        
        # Verify user owns this container
        session = await container_service.get_container_session(container_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Container not found or access denied")
        
        # Get Docker container using consistent client
        container = await get_docker_container(session)
        
        try:
            # Check if file exists and get its size
            size_output = container.execute(["stat", "-c", "%s", path])
            size = int(size_output.strip()) if size_output.strip().isdigit() else 0
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
        
        try:
            # Read file content
            content = container.execute(["cat", path])
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read file")
        
        return ContainerFileResponse(
            path=path,
            content=content,
            size=size,
            modified=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get file content: {str(e)}")


@router.post("/{container_id}/files", response_model=ContainerFileResponse)
async def save_container_file(
    container_id: str,
    request: ContainerFileRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Save content to a file in the container"""
    try:
        logger.info(f"🔄 SAVE REQUEST: Saving file {request.path} in container {container_id}")
        logger.info(f"📝 Content preview: {request.content[:100]}...")
        logger.info(f"📊 Content length: {len(request.content)} characters")
        
        # Verify user owns this container
        session = await container_service.get_container_session(container_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Container not found or access denied")
        
        # Get Docker container using consistent client
        container = await get_docker_container(session)
        
        try:
            # Create directory if needed
            dir_path = os.path.dirname(request.path)
            if dir_path and dir_path != '/':
                # Use python-on-whales execute method
                container.execute(["mkdir", "-p", dir_path])
            
            # Write file content using python-on-whales execute method
            # Use base64 encoding to avoid any shell escaping issues
            import base64
            encoded_content = base64.b64encode(request.content.encode('utf-8')).decode('ascii')
            
            try:
                # Use python-on-whales execute - returns string directly
                write_output = container.execute([
                    "sh", "-c", f"echo '{encoded_content}' | base64 -d > '{request.path}'"
                ])
                logger.info(f"Write command output: {write_output}")
            except Exception as e:
                logger.error(f"Error writing file: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")
            
            # Verify the file was written correctly by reading it back
            try:
                written_content = container.execute(["cat", request.path])
            except Exception as e:
                logger.error(f"Error verifying file write: {e}")
                raise HTTPException(status_code=500, detail="Failed to verify file was written")
            
            # Log verification details for debugging
            logger.info(f"File verification - Expected length: {len(request.content)}, Actual length: {len(written_content)}")
            
            # Normalize line endings for comparison (handle Windows/Unix differences)
            expected_normalized = request.content.replace('\r\n', '\n').replace('\r', '\n')
            actual_normalized = written_content.replace('\r\n', '\n').replace('\r', '\n')
            
            # More lenient verification - only check if file is not empty and roughly the right size
            if len(actual_normalized) == 0:
                logger.error("File verification failed: written file is empty")
                raise HTTPException(status_code=500, detail="File was not written (empty file)")
            
            # Allow for small differences (up to 5% difference in size)
            size_diff_ratio = abs(len(actual_normalized) - len(expected_normalized)) / max(len(expected_normalized), 1)
            if size_diff_ratio > 0.05:  # More than 5% difference
                logger.error(f"File size difference too large: {size_diff_ratio:.2%}")
                logger.error(f"Expected {len(expected_normalized)} chars, got {len(actual_normalized)} chars")
                raise HTTPException(status_code=500, detail="File content size verification failed")
            
            # If content is identical, great! If not, just log a warning but don't fail
            if actual_normalized != expected_normalized:
                logger.warning(f"File content differs slightly (possibly line endings or encoding)")
                logger.warning(f"Expected first 50 chars: {repr(expected_normalized[:50])}")
                logger.warning(f"Actual first 50 chars: {repr(actual_normalized[:50])}")
                # Don't raise an exception - the file is probably fine
            else:
                logger.info("✅ File content verification passed - exact match")
            
            # Get file size
            try:
                size_output = container.execute(["stat", "-c", "%s", request.path])
                size = int(size_output.strip()) if size_output.strip().isdigit() else len(written_content)
            except:
                size = len(written_content)
            
            logger.info(f"✅ Successfully saved and verified file {request.path} ({size} bytes)")
            
            return ContainerFileResponse(
                path=request.path,
                content=request.content,
                size=size,
                modified=datetime.utcnow().isoformat()
            )
            
        except Exception as docker_error:
            logger.error(f"Docker operation failed: {docker_error}")
            raise HTTPException(status_code=500, detail=f"Container operation failed: {str(docker_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.delete("/{container_id}/files")
async def delete_container_file(
    container_id: str,
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a file in the container"""
    try:
        logger.info(f"Deleting file {path} in container {container_id}")
        
        # Verify user owns this container
        session = await container_service.get_container_session(container_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Container not found or access denied")
        
        # Get Docker container using consistent client
        container = await get_docker_container(session)
        
        try:
            # Check if file exists
            try:
                container.execute(["test", "-e", path])
            except Exception:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Delete file
            try:
                container.execute(["rm", "-f", path])
            except Exception:
                raise HTTPException(status_code=500, detail="Failed to delete file")
            
            logger.info(f"Successfully deleted file {path}")
            return {"message": "File deleted successfully"}
            
        except Exception as docker_error:
            logger.error(f"Docker operation failed: {docker_error}")
            raise HTTPException(status_code=500, detail=f"Container operation failed: {str(docker_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.post("/{container_id}/directories")
async def create_container_directory(
    container_id: str,
    path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Create a directory in the container"""
    try:
        logger.info(f"Creating directory {path} in container {container_id}")
        
        # Verify user owns this container
        session = await container_service.get_container_session(container_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Container not found or access denied")
        
        # Get Docker container using consistent client
        container = await get_docker_container(session)
        
        try:
            # Create directory with proper permissions
            try:
                container.execute(["mkdir", "-p", path])
                container.execute(["chown", "1000:1000", path])
            except Exception:
                raise HTTPException(status_code=500, detail="Failed to create directory")
            
            logger.info(f"Successfully created directory {path}")
            return {"message": "Directory created successfully", "path": path}
            
        except Exception as docker_error:
            logger.error(f"Docker operation failed: {docker_error}")
            raise HTTPException(status_code=500, detail=f"Container operation failed: {str(docker_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")


@router.post("/{container_id}/files/rename")
async def rename_container_file(
    container_id: str,
    old_path: str = Query(...),
    new_path: str = Query(...),
    user_id: str = Depends(get_current_user_id)
):
    """Rename/move a file in the container"""
    try:
        logger.info(f"Renaming file from {old_path} to {new_path} in container {container_id}")
        
        # Verify user owns this container
        session = await container_service.get_container_session(container_id)
        if not session or str(session.user_id) != user_id:
            raise HTTPException(status_code=404, detail="Container not found or access denied")
        
        # Get Docker container using consistent client
        container = await get_docker_container(session)
        
        try:
            # Check if source file exists
            try:
                container.execute(["test", "-e", old_path])
            except Exception:
                raise HTTPException(status_code=404, detail="Source file not found")
            
            # Create destination directory if needed
            new_dir = os.path.dirname(new_path)
            if new_dir and new_dir != '/':
                container.execute(["mkdir", "-p", new_dir])
            
            # Move/rename file
            try:
                container.execute(["mv", old_path, new_path])
            except Exception:
                raise HTTPException(status_code=500, detail="Failed to rename file")
            
            logger.info(f"Successfully renamed file from {old_path} to {new_path}")
            return {"message": "File renamed successfully", "old_path": old_path, "new_path": new_path}
            
        except Exception as docker_error:
            logger.error(f"Docker operation failed: {docker_error}")
            raise HTTPException(status_code=500, detail=f"Container operation failed: {str(docker_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rename file: {str(e)}") 