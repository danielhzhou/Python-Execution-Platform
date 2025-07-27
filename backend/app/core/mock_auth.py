"""
Mock authentication functions for testing without Supabase auth
"""

def get_mock_user_id() -> str:
    """Return a mock user ID for testing"""
    return "123e4567-e89b-12d3-a456-426614174000"  # Valid UUID format

def get_mock_user() -> dict:
    """Return a mock user object for testing"""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "authenticated"
    } 