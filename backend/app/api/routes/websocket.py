"""
WebSocket API routes for terminal connections
"""
from fastapi import APIRouter, WebSocket, HTTPException
from app.services.websocket_service import websocket_service

router = APIRouter()


@router.websocket("/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal connections"""
    await websocket_service.handle_terminal_connection(websocket, session_id) 