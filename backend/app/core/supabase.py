"""
Supabase client initialization and configuration
"""
import logging
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supabase client for API operations
supabase_client: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_SERVICE_KEY
)

# Database engine for SQLModel operations
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=300      # Recycle connections every 5 minutes
)


def create_db_tables():
    """Create all database tables"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_db_session() -> Session:
    """Get a database session"""
    return Session(engine)


def get_supabase_client() -> Client:
    """Get the Supabase client instance"""
    return supabase_client 