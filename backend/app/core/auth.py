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
from app.services.database_service import db_service

logger = logging.getLogger(__name__)

# Security scheme for JWT token
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
) -> str:
    """
    Get the current authenticated user ID
    """
    user = await get_current_user(credentials, supabase)
    return user.id


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
        
        # Check if user exists in our local database, create if not
        try:
            user_record = await db_service.create_or_update_user(
                user_id=supabase_user.id,
                email=supabase_user.email,
                full_name=supabase_user.user_metadata.get("full_name"),
                avatar_url=supabase_user.user_metadata.get("avatar_url")
            )
            logger.info(f"User ensured in local database: {supabase_user.email}")
            
            return user_record
            
        except Exception as db_error:
            logger.error(f"Database error while creating/fetching user: {db_error}")
            # If database fails, still return a User object for the session
            return User(
                id=supabase_user.id,
                email=supabase_user.email,
                full_name=supabase_user.user_metadata.get("full_name"),
                avatar_url=supabase_user.user_metadata.get("avatar_url")
            )
        
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
                },
                # Add proper redirect URL for email confirmation
                "email_redirect_to": "http://localhost:5173"
            }
        })
        
        if auth_response.user:
            # User will be automatically created in our database when they first authenticate
            return {
                "user_id": auth_response.user.id,
                "email": auth_response.user.email,
                "message": "Registration successful! Please check your email for verification link.",
                "email_confirmation_required": True
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
            # Check if email is confirmed (for better user experience)
            if not auth_response.user.email_confirmed_at:
                # Still allow login but inform about email confirmation
                logger.warning(f"User {email} logged in without email confirmation")
            
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
        elif "Email not confirmed" in error_message:
            detail = "Please verify your email address before logging in. Check your inbox for a verification link."
        elif "Too many requests" in error_message:
            detail = "Too many login attempts. Please wait a moment and try again."
        else:
            detail = "Login failed. Please check your credentials and try again."
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        ) 