"""
WebSocket service for real-time terminal communication
"""
import asyncio
import json
import logging
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
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket connection"""
        try:
            # Accept the WebSocket connection first
            await websocket.accept()
            logger.info(f"🔌 WebSocket accepted for session {session_id}")
            
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
            
            # If no more connections for this session, clean up terminal
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
                await terminal_service.close_terminal_session(session_id)
                logger.info(f"Terminal session {session_id} closed due to no active connections")
        
        logger.info(f"WebSocket disconnected for session {session_id}")
        
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
        """Handle terminal input from WebSocket"""
        try:
            logger.info(f"Sending input to terminal {session_id}: {repr(input_data)}")
            
            # Send input directly to terminal service
            success = await terminal_service.send_input(session_id, input_data)
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
            
            # If not found by direct lookup, try container service unified lookup
            if not container_session:
                logger.info(f"🔍 Using container service to find session: {session_id}")
                
                from app.services.container_service import container_service
                
                container = await container_service.get_container_by_session(session_id)
                if container:
                    for db_session_id, tracked_container in container_service.active_containers.items():
                        if tracked_container.id == container.id:
                            actual_session_id = db_session_id
                            container_session = await db_service.get_terminal_session(actual_session_id)
                            logger.info(f"🎯 Found session via container lookup: {session_id} -> {actual_session_id}")
                            break
                
                if not container_session:
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