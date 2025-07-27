"""
Authentication and authorization utilities
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.supabase import get_supabase_client
from app.services.database_service import db_service
from app.models.container import User

logger = logging.getLogger(__name__)
security = HTTPBearer()

# In-memory cache for user data to avoid constant database hits
# In production, use Redis or similar distributed cache
_user_cache: Dict[str, Dict] = {}
USER_CACHE_TTL = 300  # 5 minutes cache TTL
USER_SYNC_INTERVAL = 3600  # Sync with DB every hour


def _is_cache_valid(cache_entry: Dict) -> bool:
    """Check if a cache entry is still valid"""
    return datetime.utcnow() < cache_entry['expires_at']


def _should_sync_user(cache_entry: Dict) -> bool:
    """Check if user should be synced with database"""
    return datetime.utcnow() > cache_entry['last_sync'] + timedelta(seconds=USER_SYNC_INTERVAL)


async def _ensure_user_in_db(supabase_user, force_sync: bool = False) -> User:
    """Ensure user exists in database with intelligent caching"""
    user_id = supabase_user.id
    now = datetime.utcnow()
    
    # Check cache first
    if user_id in _user_cache and not force_sync:
        cache_entry = _user_cache[user_id]
        
        if _is_cache_valid(cache_entry):
            # Return cached user if valid and no sync needed
            if not _should_sync_user(cache_entry):
                logger.debug(f"Using cached user data for {supabase_user.email}")
                return cache_entry['user']
    
    # Sync with database (either cache miss, expired, or periodic sync)
    try:
        logger.debug(f"Syncing user {supabase_user.email} with database")
        
        user_record = await db_service.create_or_update_user(
            user_id=supabase_user.id,
            email=supabase_user.email,
            full_name=supabase_user.user_metadata.get("full_name"),
            avatar_url=supabase_user.user_metadata.get("avatar_url")
        )
        
        # Update cache
        _user_cache[user_id] = {
            'user': user_record,
            'expires_at': now + timedelta(seconds=USER_CACHE_TTL),
            'last_sync': now
        }
        
        logger.info(f"User {supabase_user.email} synced with database")
        return user_record
        
    except Exception as db_error:
        logger.error(f"Database error while syncing user {supabase_user.email}: {db_error}")
        
        # Return cached user if available, otherwise create temporary user
        if user_id in _user_cache:
            logger.warning(f"Using cached user data due to DB error for {supabase_user.email}")
            return _user_cache[user_id]['user']
        
        # Fallback: create temporary user object
        temp_user = User(
            id=supabase_user.id,
            email=supabase_user.email,
            full_name=supabase_user.user_metadata.get("full_name"),
            avatar_url=supabase_user.user_metadata.get("avatar_url")
        )
        
        logger.warning(f"Created temporary user object for {supabase_user.email}")
        return temp_user


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> str:
    """Get the current user ID (lightweight version for endpoints that only need ID)"""
    try:
        token = credentials.credentials
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        return user_response.user.id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> User:
    """
    Get the current authenticated user with intelligent caching
    """
    try:
        # Get the JWT token from the Authorization header
        token = credentials.credentials
        
        # Verify the token with Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        supabase_user = user_response.user
        
        # Use optimized user management with caching
        user_record = await _ensure_user_in_db(supabase_user)
        return user_record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


async def create_user_account(email: str, password: str, full_name: Optional[str] = None) -> dict:
    """
    Create a new user account
    """
    supabase = get_supabase_client()
    
    try:
        # Create user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })
        
        if auth_response.user:
            # User will be automatically created in our database when they first authenticate
            return {
                "user_id": auth_response.user.id,
                "email": auth_response.user.email,
                "message": "Registration successful! You can now log in."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )
            
    except Exception as e:
        logger.error(f"User creation error: {e}")
        error_message = str(e)
        
        # Provide more specific error messages for common issues
        if "Email address" in error_message and "invalid" in error_message:
            detail = "Invalid email address format. Please use a valid email."
        elif "User already registered" in error_message:
            detail = "An account with this email already exists. Please try logging in instead."
        elif "Password should be at least" in error_message:
            detail = "Password must be at least 6 characters long."
        else:
            detail = f"Registration failed: {error_message}"
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


async def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate user and return session info
    """
    supabase = get_supabase_client()
    
    try:
        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user and auth_response.session:
            return {
                "user": auth_response.user,
                "session": auth_response.session,
                "access_token": auth_response.session.access_token
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        error_message = str(e)
        
        # Provide more specific error messages
        if "Invalid login credentials" in error_message:
            detail = "Invalid email or password. Please check your credentials."
        elif "Too many requests" in error_message:
            detail = "Too many login attempts. Please wait a moment and try again."
        else:
            detail = "Login failed. Please check your credentials and try again."
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        ) 


def clear_user_cache(user_id: Optional[str] = None):
    """Clear user cache (for testing or manual cache invalidation)"""
    if user_id:
        _user_cache.pop(user_id, None)
        logger.info(f"Cleared cache for user {user_id}")
    else:
        _user_cache.clear()
        logger.info("Cleared all user cache")


def get_cache_stats() -> Dict:
    """Get cache statistics for monitoring"""
    now = datetime.utcnow()
    valid_entries = 0
    expired_entries = 0
    
    for entry in _user_cache.values():
        if _is_cache_valid(entry):
            valid_entries += 1
        else:
            expired_entries += 1
    
    return {
        'total_entries': len(_user_cache),
        'valid_entries': valid_entries,
        'expired_entries': expired_entries,
        'cache_hit_ratio': valid_entries / max(len(_user_cache), 1),
        'ttl_seconds': USER_CACHE_TTL,
        'sync_interval_seconds': USER_SYNC_INTERVAL
    }  