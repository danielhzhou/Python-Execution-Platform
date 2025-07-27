"""
FastAPI main application module
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import api_router
from app.services.container_service import container_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Python Execution Platform")
    
    # Initialize container service
    await container_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Python Execution Platform")
    await container_service.stop()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Python Execution Platform",
        description="Browser-based IDE for Python code execution with integrated terminal",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Configure CORS - Updated for proper WebSocket support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else "http://localhost:5173"
        ] if getattr(settings, 'ENVIRONMENT', 'development') == "development" else [
            getattr(settings, 'FRONTEND_URL', "http://localhost:5173")
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Mx-ReqToken",
            "Keep-Alive",
            "X-Requested-With",
            "If-Modified-Since",
            "X-CSRF-Token",
            # WebSocket specific headers
            "Sec-WebSocket-Key",
            "Sec-WebSocket-Version",
            "Sec-WebSocket-Protocol",
            "Sec-WebSocket-Extensions",
            "Connection",
            "Upgrade"
        ],
        expose_headers=["*"]
    )
    
    # Add trusted host middleware for security in production
    if getattr(settings, 'ENVIRONMENT', 'development') == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[getattr(settings, 'ALLOWED_HOSTS', ['localhost'])]
        )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Python Execution Platform API",
            "version": "1.0.0",
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return JSONResponse(
            content={
                "status": "healthy",
                "environment": getattr(settings, 'ENVIRONMENT', 'development'),
                "version": "1.0.0",
                "active_containers": len(getattr(container_service, 'active_containers', {})),
                "active_sessions": len(getattr(container_service, 'container_sessions', {}))
            }
        )
    
    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=getattr(settings, 'DEBUG', True)
    ) 