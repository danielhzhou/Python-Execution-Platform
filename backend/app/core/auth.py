"""
Supabase Authentication middleware and utilities
"""
import logging
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


class AuthUser(BaseModel):
    """Authenticated user information from JWT"""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"
    app_metadata: dict = {}
    user_metadata: dict = {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """
    Extract and verify user information from Supabase JWT token
    """
    try:
        token = credentials.credentials
        
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Create or update user record in database
        email = payload.get("email")
        if email:
            # Import here to avoid circular imports
            from app.services.database_service import db_service
            
            # Extract user metadata
            user_metadata = payload.get("user_metadata", {})
            full_name = user_metadata.get("full_name") or user_metadata.get("name")
            avatar_url = user_metadata.get("avatar_url") or user_metadata.get("picture")
            
            try:
                await db_service.create_or_update_user(
                    user_id=user_id,
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url
                )
            except Exception as db_error:
                logger.warning(f"Failed to sync user to database: {db_error}")
                # Don't fail authentication if database sync fails
        
        return AuthUser(
            id=user_id,
            email=email,
            role=payload.get("role", "authenticated"),
            app_metadata=payload.get("app_metadata", {}),
            user_metadata=payload.get("user_metadata", {})
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_user_id(user: AuthUser = Depends(get_current_user)) -> str:
    """
    Get the current user's ID (simplified dependency for routes that only need user ID)
    """
    return user.id


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return the payload
    Used for cases where you need to verify tokens outside of FastAPI dependencies
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except jwt.InvalidTokenError:
        return None 