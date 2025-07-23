"""
Main FastAPI application for Python Execution Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import api_router

# Create FastAPI application
app = FastAPI(
    title="Python Execution Platform API",
    description="Secure browser-based Python code execution with Docker sandboxing",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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
            "version": "1.0.0"
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