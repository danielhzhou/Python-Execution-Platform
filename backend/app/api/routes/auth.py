"""
Authentication API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.auth import authenticate_user, create_user_account, get_current_user
from app.models.container import User

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


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    user: dict
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
        
        return AuthResponse(
            access_token=auth_result["access_token"],
            user={
                "id": auth_result["user"].id,
                "email": auth_result["user"].email,
                "user_metadata": auth_result["user"].user_metadata
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


@router.post("/logout")
async def logout_user():
    """Logout user (client should clear the token)"""
    return {"message": "Logout successful. Please clear your access token."}


@router.get("/confirm")
async def confirm_email(
    token_hash: str = Query(..., description="Email confirmation token"),
    type: str = Query(..., description="Confirmation type")
):
    """Handle email confirmation from Supabase"""
    try:
        from app.core.supabase import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Verify the email confirmation token
        result = supabase.auth.verify_otp({
            "token_hash": token_hash,
            "type": type
        })
        
        if result.user:
            return {
                "message": "Email confirmed successfully! You can now log in.",
                "user_id": result.user.id,
                "email": result.user.email
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired confirmation token"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Email confirmation failed: {str(e)}"
        )


@router.post("/resend-confirmation")
async def resend_confirmation_email(request: dict):
    """Resend email confirmation"""
    try:
        from app.core.supabase import get_supabase_client
        
        email = request.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        supabase = get_supabase_client()
        
        result = supabase.auth.resend({
            "type": "signup",
            "email": email,
            "options": {
                "email_redirect_to": "http://localhost:5173"
            }
        })
        
        return {"message": "Confirmation email sent! Please check your inbox."}
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to resend confirmation email: {str(e)}"
        ) 