"""
WebSocket service for real-time terminal communication
"""
import asyncio
import json
import logging
import re
from typing import Dict, Optional, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.services.terminal_service import terminal_service
from app.services.container_service import container_service
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""
    type: str
    data: dict = {}
    timestamp: Optional[datetime] = None


class TerminalInput(BaseModel):
    """Terminal input message"""
    data: str


class WebSocketManager:
    """Manages WebSocket connections for terminal sessions"""
    
    def __init__(self):
        # session_id -> websocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # session_id -> set of connected websockets (for multiple clients)
        self.session_connections: Dict[str, Set[WebSocket]] = {}
        # session_id -> cleanup task for delayed terminal session cleanup
        self.cleanup_tasks: Dict[str, asyncio.Task] = {}
        # session_id -> command buffer for accumulating input
        self.command_buffers: Dict[str, str] = {}
        # session_id -> current working directory
        self.current_directories: Dict[str, str] = {}
        
        # Filesystem command patterns for detection
        self.filesystem_command_patterns = {
            'create_file': re.compile(r'^(touch|echo\s+.*\s*>\s*|cat\s+.*\s*>\s*|tee\s+.*|nano\s+|vim\s+|emacs\s+|code\s+)', re.IGNORECASE),
            'create_dir': re.compile(r'^mkdir\s+', re.IGNORECASE),
            'delete': re.compile(r'^(rm\s+|rmdir\s+)', re.IGNORECASE),
            'move_copy': re.compile(r'^(mv\s+|cp\s+|rsync\s+)', re.IGNORECASE),
            'change_dir': re.compile(r'^cd\s+', re.IGNORECASE),
            'list_files': re.compile(r'^(ls\s*|dir\s*|find\s+|tree\s*)', re.IGNORECASE),
            'extract': re.compile(r'^(tar\s+|unzip\s+|gunzip\s+|unrar\s+)', re.IGNORECASE),
            'git_operations': re.compile(r'^git\s+(clone|checkout|pull|reset|clean)', re.IGNORECASE),
            'python_file_ops': re.compile(r'\.py\s*$', re.IGNORECASE)
        }
        
    def _is_filesystem_command(self, command: str) -> tuple[bool, str]:
        """Check if a command affects the filesystem and return the command type"""
        command = command.strip()
        if not command:
            return False, ""
            
        for cmd_type, pattern in self.filesystem_command_patterns.items():
            if pattern.search(command):
                return True, cmd_type
        return False, ""
        
    async def _update_current_directory(self, session_id: str, command: str):
        """Update the current directory tracking for cd commands"""
        try:
            command = command.strip()
            if command.startswith('cd '):
                # Extract the target directory
                target_dir = command[3:].strip()
                
                # Initialize current directory if not set
                if session_id not in self.current_directories:
                    self.current_directories[session_id] = '/workspace'
                
                current_dir = self.current_directories[session_id]
                
                if target_dir == '' or target_dir == '~':
                    # cd with no args or ~ goes to home (workspace)
                    new_dir = '/workspace'
                elif target_dir == '..':
                    # Go up one directory
                    if current_dir != '/workspace':
                        new_dir = '/'.join(current_dir.rstrip('/').split('/')[:-1]) or '/workspace'
                    else:
                        new_dir = '/workspace'
                elif target_dir.startswith('/'):
                    # Absolute path
                    new_dir = target_dir if target_dir.startswith('/workspace') else '/workspace' + target_dir
                else:
                    # Relative path
                    new_dir = f"{current_dir.rstrip('/')}/{target_dir}"
                
                # Normalize the path
                new_dir = new_dir.replace('//', '/').rstrip('/') or '/'
                if not new_dir.startswith('/workspace'):
                    new_dir = '/workspace'
                
                self.current_directories[session_id] = new_dir
                logger.info(f"Updated current directory for {session_id}: {new_dir}")
                
                # Send directory change notification
                await self._broadcast_to_session(session_id, {
                    "type": "directory_change",
                    "data": {
                        "current_directory": new_dir,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                
        except Exception as e:
            logger.error(f"Error updating current directory: {e}")
        
    async def _notify_filesystem_change(self, session_id: str, command_type: str, command: str):
        """Notify connected clients about filesystem changes"""
        try:
            # Send filesystem change notification to all connected clients for this session
            message = {
                "type": "filesystem_change",
                "data": {
                    "command_type": command_type,
                    "command": command,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            await self._broadcast_to_session(session_id, message)
            logger.info(f"Sent filesystem change notification for session {session_id}: {command_type}")
        except Exception as e:
            logger.error(f"Failed to send filesystem change notification: {e}")
            
    async def _delayed_filesystem_notification(self, session_id: str, command_type: str, command: str):
        """Send filesystem change notification with a small delay to allow command execution"""
        try:
            # Wait a bit for the command to execute
            await asyncio.sleep(0.5)
            await self._notify_filesystem_change(session_id, command_type, command)
        except Exception as e:
            logger.error(f"Error in delayed filesystem notification: {e}")
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket connection"""
        try:
            # Accept the WebSocket connection first
            await websocket.accept()
            logger.info(f"🔌 WebSocket accepted for session {session_id}")
            
            # Cancel any pending cleanup task for this session
            if session_id in self.cleanup_tasks:
                self.cleanup_tasks[session_id].cancel()
                del self.cleanup_tasks[session_id]
                logger.info(f"🔄 Cancelled cleanup task for reconnecting session {session_id}")
            
            # Store connection
            ws_id = id(websocket)
            self.active_connections[ws_id] = websocket
            
            # Add to session connections
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(websocket)
            
            logger.info(f"WebSocket connected for session {session_id}")
            
            # Send welcome message with error handling
            try:
                await self._send_to_websocket(websocket, {
                    "type": "connected",
                    "data": {
                        "session_id": session_id,
                        "message": "Terminal connected successfully"
                    }
                })
                logger.info(f"✅ Welcome message sent successfully for session {session_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send welcome message for session {session_id}: {e}")
                raise
                
        except Exception as e:
            logger.error(f"❌ Error in WebSocket connect: {e}", exc_info=True)
            raise
        
    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket disconnection"""
        # Remove from active connections
        ws_id = id(websocket)
        if ws_id in self.active_connections:
            del self.active_connections[ws_id]
        
        # Remove from session connections
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(websocket)
            
            # If no more connections for this session, schedule delayed cleanup
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
                
                # Schedule delayed cleanup (30 seconds) to allow for reconnections
                cleanup_task = asyncio.create_task(self._delayed_cleanup(session_id))
                self.cleanup_tasks[session_id] = cleanup_task
                logger.info(f"Scheduled delayed cleanup for session {session_id} (30s grace period)")
        
        logger.info(f"WebSocket disconnected for session {session_id}")
        
    async def _delayed_cleanup(self, session_id: str):
        """Delayed cleanup of terminal session to allow for reconnections"""
        try:
            # Wait for 30 seconds to allow reconnection
            await asyncio.sleep(30)
            
            # Check if session was reconnected during the delay
            if session_id not in self.session_connections:
                await terminal_service.close_terminal_session(session_id)
                # Clean up command buffer
                if session_id in self.command_buffers:
                    del self.command_buffers[session_id]
                logger.info(f"Terminal session {session_id} closed after grace period")
            else:
                logger.info(f"Terminal session {session_id} was reconnected, cleanup cancelled")
                
        except asyncio.CancelledError:
            logger.info(f"Cleanup task cancelled for session {session_id} (reconnected)")
        finally:
            # Clean up the task reference
            if session_id in self.cleanup_tasks:
                del self.cleanup_tasks[session_id]
        
    async def handle_message(self, websocket: WebSocket, session_id: str, message: str):
        """Handle incoming WebSocket message"""
        try:
            # Parse message
            data = json.loads(message)
            msg_type = data.get("type")
            msg_data = data.get("data", {})
            
            logger.info(f"Received WebSocket message: type={msg_type}, session={session_id}")
            
            # Handle different message types
            if msg_type == "input" or msg_type == "terminal_input":
                # Handle both formats: {"type": "input", "data": {"data": "..."}} and {"type": "terminal_input", "data": "..."}
                if isinstance(msg_data, str):
                    # Direct string format from frontend
                    await self._handle_terminal_input(session_id, msg_data)
                elif isinstance(msg_data, dict) and "data" in msg_data:
                    # Nested format
                    await self._handle_terminal_input(session_id, msg_data["data"])
                else:
                    # Fallback - treat the data as the input
                    await self._handle_terminal_input(session_id, str(msg_data))
                    
            elif msg_type == "ping":
                await self._send_to_websocket(websocket, {"type": "pong"})
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Invalid WebSocket message: {e}")
            await self._send_error(websocket, "Invalid message format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(websocket, "Internal server error")
            
    async def start_terminal_output_stream(self, session_id: str):
        """Start streaming terminal output to connected WebSockets"""
        logger.info(f"🔄 Starting output stream for session {session_id}")
        
        output_stream = await terminal_service.get_output_stream(session_id)
        if not output_stream:
            logger.error(f"❌ No output stream available for session {session_id}")
            return
            
        logger.info(f"✅ Output stream obtained for session {session_id}")
        
        try:
            async for output in output_stream:
                logger.info(f"📤 Streaming output for {session_id}: {repr(output.data[:100])}")  # Log first 100 chars
                # Send output to all connected WebSockets for this session
                # Use 'terminal_output' type to match frontend expectations
                await self._broadcast_to_session(session_id, {
                    "type": "terminal_output",
                    "data": output.data  # Send data directly, not nested
                })
                
        except Exception as e:
            logger.error(f"❌ Error in terminal output stream for {session_id}: {e}")
            await self._broadcast_to_session(session_id, {
                "type": "error",
                "data": {"message": "Terminal output stream error"}
            })
            
    async def _handle_terminal_input(self, session_id: str, input_data: str):
        """Handle terminal input from WebSocket with command buffering for network detection"""
        try:
            logger.info(f"Sending input to terminal {session_id}: {repr(input_data)}")
            
            # ALWAYS send input to terminal first for immediate response and echoing
            success = await terminal_service.send_input(session_id, input_data)
            
            # Initialize buffer for this session if not exists
            if session_id not in self.command_buffers:
                self.command_buffers[session_id] = ""
            
            # Handle command buffering for network detection
            if input_data in ['\r', '\n', '\r\n']:
                # We have a complete command
                command = self.command_buffers[session_id].strip()
                
                if command:  # Only process non-empty commands
                    logger.info(f"Complete command detected for {session_id}: {repr(command)}")
                    
                    # Update current directory for cd commands
                    if command.startswith('cd '):
                        asyncio.create_task(self._update_current_directory(session_id, command))
                    
                    # Check if this is a filesystem command and notify clients
                    is_fs_command, command_type = self._is_filesystem_command(command)
                    if is_fs_command:
                        # Delay the notification slightly to allow command to execute first
                        asyncio.create_task(self._delayed_filesystem_notification(session_id, command_type, command))
                    
                    # Network commands now work by default with PyPI network access
                    logger.info(f"Command executed: {command}")
                
                # Clear the buffer after processing the command
                self.command_buffers[session_id] = ""
                
            else:
                # Accumulate input into buffer (but input was already sent above)
                self.command_buffers[session_id] += input_data
            
            if not success:
                logger.error(f"Failed to send input to terminal {session_id}")
                await self._broadcast_to_session(session_id, {
                    "type": "error",
                    "data": {"message": "Failed to send input to terminal"}
                })
                
        except Exception as e:
            logger.error(f"Error handling terminal input: {e}")
            await self._broadcast_to_session(session_id, {
                "type": "error", 
                "data": {"message": "Terminal input error"}
            })
            
    # Network handling methods removed - containers now have PyPI access by default
    async def _broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast a message to all WebSockets connected to a session"""
        if session_id not in self.session_connections:
            return
            
        # Get all connected WebSockets for this session
        connections = list(self.session_connections[session_id])
        
        # Send to all connections
        for websocket in connections:
            try:
                await self._send_to_websocket(websocket, message)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")
                # Remove broken connection
                self.session_connections[session_id].discard(websocket)
                
    async def _send_to_websocket(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
            
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """Send an error message to a WebSocket"""
        await self._send_to_websocket(websocket, {
            "type": "error",
            "data": {"message": error_message}
        })
        
    async def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for a terminal session"""
        connections_count = len(self.session_connections.get(session_id, set()))
        
        # Get container info
        container_info = await container_service.get_container_info(session_id)
        
        # Get terminal session info
        terminal_session = await terminal_service.get_terminal_session(session_id)
        
        return {
            "session_id": session_id,
            "connected_clients": connections_count,
            "terminal_active": terminal_session is not None and terminal_session.is_active,
            "container_info": container_info.dict() if container_info else None,
            "command_history_count": len(terminal_session.command_history) if terminal_session else 0
        }


class WebSocketService:
    """Main WebSocket service for terminal management"""
    
    def __init__(self):
        self.manager = WebSocketManager()
        
    async def handle_terminal_connection(self, websocket: WebSocket, session_id: str):
        """Handle a new terminal WebSocket connection"""
        try:
            logger.info(f"🔌 WebSocket connection attempt for session: {session_id}")
            
            # First, try to find the session by ID (if it's a valid UUID)
            container_session = None
            actual_session_id = session_id
            
            try:
                # Try direct lookup first (if session_id is a UUID)
                container_session = await db_service.get_terminal_session(session_id)
                if container_session:
                    logger.info(f"✅ Found session by direct ID lookup: {session_id}")
            except Exception as e:
                logger.info(f"Direct session lookup failed (expected if using container name): {e}")
            
            # If not found by direct lookup, try to find by container name
            if not container_session:
                logger.info(f"🔍 Searching for session by container name: {session_id}")
                
                from app.services.container_service import container_service
                
                # Look through active containers to find matching container name
                found_session_id = None
                for db_session_id, container in container_service.active_containers.items():
                    if hasattr(container, 'name') and container.name == session_id:
                        found_session_id = db_session_id
                        logger.info(f"🎯 Found session by container name: {session_id} -> {db_session_id}")
                        break
                
                if found_session_id:
                    actual_session_id = found_session_id
                    container_session = await db_service.get_terminal_session(actual_session_id)
                else:
                    # If still not found, try to find by container_id field in database
                    logger.info(f"🔍 Searching database for container_id matching: {session_id}")
                    sessions = await db_service.get_all_terminal_sessions()
                    for session in sessions:
                        if session.container_id and session.container_id == session_id:
                            actual_session_id = session.id
                            container_session = session
                            logger.info(f"🎯 Found session by container_id: {session_id} -> {session.id}")
                            break
            
            if not container_session:
                logger.error(f"❌ Could not find session {session_id} by any method")
                await websocket.close(code=1008, reason="Invalid session ID")
                return
                
            logger.info(f"✅ Session validated: {actual_session_id}")
            
            # Create terminal session if it doesn't exist
            terminal_session = await terminal_service.get_terminal_session(actual_session_id)
            if not terminal_session:
                logger.info(f"🔧 Creating terminal session for {actual_session_id}")
                success = await terminal_service.create_terminal_session(actual_session_id)
                if not success:
                    logger.error(f"❌ Failed to create terminal session for {actual_session_id}")
                    await websocket.close(code=1011, reason="Failed to create terminal session")
                    return
                    
            # Connect WebSocket using the correct session ID
            await self.manager.connect(websocket, actual_session_id)
            logger.info(f"🎉 WebSocket connected successfully for session {actual_session_id}")
            
            # Start output streaming in background
            output_task = asyncio.create_task(
                self.manager.start_terminal_output_stream(actual_session_id)
            )
            
            try:
                # Handle incoming messages
                while True:
                    message = await websocket.receive_text()
                    await self.manager.handle_message(websocket, actual_session_id, message)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {actual_session_id}")
            finally:
                # Clean up
                output_task.cancel()
                await self.manager.disconnect(websocket, actual_session_id)
                
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}", exc_info=True)
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass
                
    async def get_session_stats(self, session_id: str) -> dict:
        """Get session statistics"""
        return await self.manager.get_session_stats(session_id)


# Global WebSocket service instance
websocket_service = WebSocketService() 