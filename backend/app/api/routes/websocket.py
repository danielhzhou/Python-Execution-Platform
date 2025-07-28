"""
WebSocket API routes for terminal connections
"""
from fastapi import APIRouter, WebSocket
import logging
from app.services.websocket_service import websocket_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/test")
async def test_websocket(websocket: WebSocket):
    """Simple WebSocket test endpoint"""
    await websocket.accept()
    logger.info("Test WebSocket connected")
    try:
        await websocket.send_text("Hello from WebSocket test!")
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}")


@router.websocket("/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal connections - no authentication for now"""
    logger.info(f"🔌 Terminal WebSocket connection attempt for session: {session_id}")
    
    # Handle the terminal connection directly without authentication
    await websocket_service.handle_terminal_connection(websocket, session_id) 