"""
Main FastAPI application for Python Execution Platform
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.supabase import create_db_tables
from app.api import api_router
from app.services.container_service import container_service
from app.services.storage_service import storage_service
from app.services.database_service import db_service

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
    
    # Initialize database tables
    try:
        create_db_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't fail startup - tables might already exist
    
    # Start container service
    await container_service.start()
    
    # Initialize storage service
    storage_initialized = await storage_service.ensure_bucket_exists()
    if storage_initialized:
        logger.info("Storage service initialized successfully")
    else:
        logger.warning("Failed to initialize storage service")
    
    # Create test user for auth-disabled testing
    # Skip user creation since we don't have auth.users table in test environment
    try:
        # Check if we're in test/dev mode by trying to create the user
        # In production, this would be handled by Supabase auth
        logger.info("Skipping test user creation - auth disabled for testing")
    except Exception as e:
        logger.warning(f"Test user creation skipped: {e}")
    
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