"""
Standardized API response formats
"""
from typing import Any, Optional, Dict, Union
from uuid import UUID
from pydantic import BaseModel
from fastapi import HTTPException
from fastapi.responses import JSONResponse


def convert_uuid_to_str(value: Any) -> Any:
    """Convert UUID objects to strings recursively"""
    if isinstance(value, UUID):
        return str(value)
    elif isinstance(value, dict):
        return {k: convert_uuid_to_str(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_uuid_to_str(item) for item in value]
    elif hasattr(value, '__dict__'):
        # Handle SQLModel objects
        obj_dict = {}
        for key, val in value.__dict__.items():
            if not key.startswith('_'):  # Skip private attributes
                obj_dict[key] = convert_uuid_to_str(val)
        return obj_dict
    return value


class ApiResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ApiError(BaseModel):
    """Standard API error format"""
    error: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


def success_response(data: Any = None, message: Optional[str] = None) -> ApiResponse:
    """Create a successful API response"""
    return ApiResponse(
        success=True,
        data=data,
        message=message
    )


def error_response(error: str, message: Optional[str] = None, code: Optional[str] = None) -> ApiResponse:
    """Create an error API response"""
    return ApiResponse(
        success=False,
        error=error,
        message=message or error
    )


def handle_api_error(error: Exception, default_message: str = "An error occurred") -> HTTPException:
    """Convert exceptions to standardized HTTP exceptions"""
    if isinstance(error, HTTPException):
        return error
    
    error_message = str(error) if str(error) else default_message
    
    # Map common exceptions to HTTP status codes
    if isinstance(error, ValueError):
        status_code = 400
    elif isinstance(error, PermissionError):
        status_code = 403
    elif isinstance(error, FileNotFoundError):
        status_code = 404
    else:
        status_code = 500
    
    return HTTPException(
        status_code=status_code,
        detail=error_message
    )


def json_error_response(status_code: int, error: str, message: Optional[str] = None) -> JSONResponse:
    """Create a JSON error response"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error,
            "message": message or error
        }
    ) 