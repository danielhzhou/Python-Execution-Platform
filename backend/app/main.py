"""
Main FastAPI application for Python Execution Platform
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import api_router
from app.services.container_service import container_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Python Execution Platform")
    await container_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Python Execution Platform")
    await container_service.stop()


# Create FastAPI application
app = FastAPI(
    title="Python Execution Platform API",
    description="Secure browser-based Python code execution with Docker sandboxing",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "python-execution-platform",
            "version": "1.0.0",
            "active_containers": len(container_service.active_containers),
            "active_sessions": len(container_service.container_sessions)
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Python Execution Platform API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 