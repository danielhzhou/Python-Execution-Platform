"""
Authentication functions using Supabase Auth
"""
import logging
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from app.core.supabase import get_supabase_client
from app.models.container import User

logger = logging.getLogger(__name__)

# Security scheme for JWT token
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> str:
    """
    Extract and validate user ID from JWT token
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
        
        return user_response.user.id
        
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
    Get the current authenticated user
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
        
        # Check if user exists in our database, create if not
        user_data = supabase.table("users").select("*").eq("id", supabase_user.id).execute()
        
        if not user_data.data:
            # Create user in our database
            new_user = {
                "id": supabase_user.id,
                "email": supabase_user.email,
                "full_name": supabase_user.user_metadata.get("full_name"),
                "avatar_url": supabase_user.user_metadata.get("avatar_url")
            }
            supabase.table("users").insert(new_user).execute()
            user_record = new_user
        else:
            user_record = user_data.data[0]
        
        return User(**user_record)
        
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
                "message": "User created successfully. Please check your email for verification."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )
            
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user account: {str(e)}"
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        ) 