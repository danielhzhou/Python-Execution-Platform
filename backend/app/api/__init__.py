"""
API router configuration
"""
from fastapi import APIRouter

from app.api.routes import containers, websocket, projects, auth

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"]) 