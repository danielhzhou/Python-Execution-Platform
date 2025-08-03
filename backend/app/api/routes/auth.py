"""
Authentication API routes
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.auth import authenticate_user, create_user_account, get_current_user
from app.models.container import User

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    user: dict
    refresh_token: Optional[str] = None
    message: Optional[str] = None


@router.post("/register", response_model=dict)
async def register_user(request: RegisterRequest):
    """Register a new user account"""
    try:
        result = await create_user_account(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login_user(request: LoginRequest):
    """Authenticate user and return access token"""
    try:
        auth_result = await authenticate_user(
            email=request.email,
            password=request.password
        )
        
        # Get the full user record from database to include role
        from app.core.auth import _ensure_user_in_db
        user_record = await _ensure_user_in_db(auth_result["user"])
        
        return AuthResponse(
            access_token=auth_result["access_token"],
            refresh_token=auth_result["session"].refresh_token if auth_result.get("session") else None,
            user={
                "id": user_record.id,
                "email": user_record.email,
                "full_name": user_record.full_name,
                "role": user_record.role,
                "created_at": user_record.created_at.isoformat() if user_record.created_at else None,
                "updated_at": user_record.updated_at.isoformat() if user_record.updated_at else None
            },
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token"""
    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()
        
        # Refresh the session with Supabase
        auth_response = supabase.auth.refresh_session(request.refresh_token)
        
        if auth_response.session and auth_response.user:
            # Get the full user record from database
            from app.core.auth import _ensure_user_in_db
            user_record = await _ensure_user_in_db(auth_response.user)
            
            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user={
                    "id": user_record.id,
                    "email": user_record.email,
                    "full_name": user_record.full_name,
                    "role": user_record.role,
                    "created_at": user_record.created_at.isoformat() if user_record.created_at else None,
                    "updated_at": user_record.updated_at.isoformat() if user_record.updated_at else None
                },
                message="Token refreshed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """Logout user and invalidate Supabase session"""
    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()
        
        # Invalidate the session on Supabase side
        try:
            supabase.auth.sign_out()
        except Exception as e:
            # Log but don't fail if Supabase logout fails
            logger.warning(f"Supabase logout warning for user {current_user.email}: {e}")
        
        # Clear user from cache
        from app.core.auth import clear_user_cache
        clear_user_cache(current_user.id)
        
        return {"message": "Logout successful"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if logout fails, return success to prevent client-side issues
        return {"message": "Logout successful"}


# Email confirmation is handled automatically by Supabase Auth 