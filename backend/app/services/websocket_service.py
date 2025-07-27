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
    
    
class TerminalResize(BaseModel):
    """Terminal resize message"""
    rows: int
    cols: int


class WebSocketManager:
    """Manages WebSocket connections for terminal sessions"""
    
    def __init__(self):
        # websocket_id -> websocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # session_id -> set of connected websockets (for multiple clients)
        self.session_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a WebSocket connection for a terminal session"""
        await websocket.accept()
        
        # Store the connection
        self.active_connections[str(id(websocket))] = websocket
        
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(websocket)
        
        logger.info(f"WebSocket connected for session {session_id}")
        
        # Send welcome message
        await self._send_to_websocket(websocket, {
            "type": "connected",
            "data": {
                "session_id": session_id,
                "message": "Terminal connected successfully"
            }
        })
        
    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Handle WebSocket disconnection"""
        # Remove from active connections
        ws_id = str(id(websocket))
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
            msg = WebSocketMessage(**data)
            
            # Handle different message types
            if msg.type == "input":
                await self._handle_terminal_input(session_id, msg.data)
            elif msg.type == "resize":
                await self._handle_terminal_resize(session_id, msg.data)
            elif msg.type == "ping":
                await self._send_to_websocket(websocket, {"type": "pong"})
            else:
                logger.warning(f"Unknown message type: {msg.type}")
                
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Invalid WebSocket message: {e}")
            await self._send_error(websocket, "Invalid message format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(websocket, "Internal server error")
            
    async def start_terminal_output_stream(self, session_id: str):
        """Start streaming terminal output to connected WebSockets"""
        output_stream = await terminal_service.get_output_stream(session_id)
        if not output_stream:
            logger.error(f"No output stream available for session {session_id}")
            return
            
        try:
            async for output in output_stream:
                # Send output to all connected WebSockets for this session
                await self._broadcast_to_session(session_id, {
                    "type": "output",
                    "data": {
                        "content": output.data,
                        "stream": output.stream,
                        "timestamp": output.timestamp.isoformat()
                    }
                })
                
        except Exception as e:
            logger.error(f"Error in terminal output stream: {e}")
            await self._broadcast_to_session(session_id, {
                "type": "error",
                "data": {"message": "Terminal output stream error"}
            })
            
    async def _handle_terminal_input(self, session_id: str, data: dict):
        """Handle terminal input from WebSocket"""
        try:
            input_data = TerminalInput(**data)
            
            # Send input to terminal
            success = await terminal_service.send_input(session_id, input_data.data)
            if not success:
                await self._broadcast_to_session(session_id, {
                    "type": "error",
                    "data": {"message": "Failed to send input to terminal"}
                })
                
        except ValidationError as e:
            logger.error(f"Invalid terminal input: {e}")
            
    async def _handle_terminal_resize(self, session_id: str, data: dict):
        """Handle terminal resize from WebSocket"""
        try:
            resize_data = TerminalResize(**data)
            
            # Resize terminal
            success = await terminal_service.resize_terminal(
                session_id, 
                resize_data.rows, 
                resize_data.cols
            )
            
            if success:
                await self._broadcast_to_session(session_id, {
                    "type": "resized",
                    "data": {
                        "rows": resize_data.rows,
                        "cols": resize_data.cols
                    }
                })
            else:
                await self._broadcast_to_session(session_id, {
                    "type": "error",
                    "data": {"message": "Failed to resize terminal"}
                })
                
        except ValidationError as e:
            logger.error(f"Invalid resize data: {e}")
            
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
        """Handle a new terminal WebSocket connection for local development"""
        try:
            # For local development, we don't need to verify database session
            # Just create a terminal session directly
            
            # Create terminal session if it doesn't exist
            terminal_session = await terminal_service.get_terminal_session(session_id)
            if not terminal_session:
                # Create local terminal session with current working directory
                import os
                working_dir = os.getcwd()
                success = await terminal_service.create_terminal_session(session_id, working_dir)
                if not success:
                    await websocket.close(code=1011, reason="Failed to create terminal session")
                    return
                    
            # Connect WebSocket
            await self.manager.connect(websocket, session_id)
            
            # Send welcome message
            await websocket.send_text(json.dumps({
                "type": "connected",
                "data": {
                    "message": "Terminal connected successfully",
                    "session_id": session_id
                }
            }))
            
            # Start output streaming in background
            output_task = asyncio.create_task(
                self.manager.start_terminal_output_stream(session_id)
            )
            
            try:
                # Handle incoming messages
                while True:
                    message = await websocket.receive_text()
                    await self.manager.handle_message(websocket, session_id, message)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
            finally:
                # Clean up
                output_task.cancel()
                await self.manager.disconnect(websocket, session_id)
                
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass
                
    async def get_session_stats(self, session_id: str) -> dict:
        """Get session statistics"""
        return await self.manager.get_session_stats(session_id)


# Global WebSocket service instance
websocket_service = WebSocketService()  