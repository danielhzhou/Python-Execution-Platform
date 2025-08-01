"""
API router configuration
"""
from fastapi import APIRouter

from app.api.routes import containers, websocket, projects, auth, files

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
# WebSocket routes on separate prefix to avoid auth dependencies
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"]) 