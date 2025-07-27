"""
Supabase client initialization and configuration
"""
import logging
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.core.config import settings

# Configure SQLAlchemy logging BEFORE creating the engine
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Supabase client for API operations
supabase_client: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_SERVICE_KEY
)

# Database engine for SQLModel operations
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL query logging to reduce noise
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=300,     # Recycle connections every 5 minutes
    # Configure logging levels for SQLAlchemy
    logging_name="sqlalchemy.engine",
    echo_pool=False,  # Disable connection pool logging
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