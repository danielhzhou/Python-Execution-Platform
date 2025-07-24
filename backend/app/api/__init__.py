"""
API router configuration
"""
from fastapi import APIRouter

from app.api.routes import containers, websocket

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"]) 