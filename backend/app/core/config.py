"""
Application configuration settings
"""
from typing import List
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Security
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CONTAINER_LIFETIME_MINUTES: int = 30
    MAX_CONTAINERS_PER_USER: int = 1
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("CORS_ORIGINS must be a string or list")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings() 