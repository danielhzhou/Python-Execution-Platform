"""
API router configuration
"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include sub-routers (will be created later)
# from app.api.routes import auth, containers, files, websocket
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
# api_router.include_router(files.router, prefix="/files", tags=["files"])
# api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"]) 