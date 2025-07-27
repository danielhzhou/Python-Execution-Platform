"""
Application configuration settings
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database (Supabase Postgres)
    DATABASE_URL: str
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str  # For JWT verification
    
    # Redis Configuration (optional)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Docker & Container Management
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    CONTAINER_IMAGE: str = "python-execution-sandbox:latest"
    CONTAINER_CPU_LIMIT: str = "1.0"  # 1 vCPU
    CONTAINER_MEMORY_LIMIT: str = "512m"  # 512MB
    CONTAINER_TIMEOUT_SECONDS: int = 1800  # 30 minutes
    CONTAINER_CLEANUP_INTERVAL: int = 300  # 5 minutes
    
    # Network Security
    PYPI_NETWORK_NAME: str = "pypi-net"
    ALLOWED_DOMAINS: List[str] = ["pypi.org", "files.pythonhosted.org"]
    NETWORK_TIMEOUT_SECONDS: int = 30
    
    # Terminal Configuration
    TERMINAL_ROWS: int = 24
    TERMINAL_COLS: int = 80
    PTY_BUFFER_SIZE: int = 8192
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Security
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CONTAINER_LIFETIME_MINUTES: int = 30
    MAX_CONTAINERS_PER_USER: int = 1
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a string or list")
    
    @field_validator("ALLOWED_DOMAINS", mode="before")
    @classmethod
    def assemble_allowed_domains(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("ALLOWED_DOMAINS must be a string or list")
    
    model_config = {
        "env_file": [".env", "../.env"],  # Look in current dir and parent dir
        "case_sensitive": True
    }


# Global settings instance
settings = Settings() 