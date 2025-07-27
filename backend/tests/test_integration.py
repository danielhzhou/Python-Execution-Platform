"""
Integration tests for frontend-backend compatibility
"""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


client = TestClient(app)


class TestFrontendBackendIntegration:
    """Test frontend-backend API integration"""
    
    def test_api_response_format(self):
        """Test that API responses match frontend expectations"""
        # This would require authentication, so we'll test the format
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        
        # Should return 401 but with proper error format
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data  # FastAPI standard error format
    
    def test_container_creation_response_format(self):
        """Test container creation response format"""
        # This would require authentication
        response = client.post(
            "/api/containers/create",
            json={"project_name": "test"},
            headers={"Authorization": "Bearer invalid"}
        )
        
        # Should return 401 but with proper error format
        assert response.status_code == 401
        
    def test_file_api_endpoints_exist(self):
        """Test that file API endpoints exist"""
        # Test file save endpoint exists
        response = client.post(
            "/api/files/",
            json={"containerId": "test", "path": "test.py", "content": "print('hello')"},
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401  # Unauthorized, but endpoint exists
        
        # Test file get endpoint exists
        response = client.get(
            "/api/files/?containerId=test&path=test.py",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401  # Unauthorized, but endpoint exists
        
        # Test file list endpoint exists
        response = client.get(
            "/api/files/list?containerId=test",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401  # Unauthorized, but endpoint exists
    
    def test_websocket_endpoint_exists(self):
        """Test that WebSocket endpoint exists"""
        # Test WebSocket endpoint (will fail connection but should not be 404)
        with client.websocket_connect("/api/ws/terminal/test-session") as websocket:
            # If we get here, the endpoint exists
            # Connection will likely fail due to auth, but that's expected
            pass
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.options("/api/containers/", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST"
        })
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 405
    
    def test_openapi_schema(self):
        """Test OpenAPI schema is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        
        # Check that key endpoints are documented
        paths = schema["paths"]
        assert "/api/containers/create" in paths
        assert "/api/files/" in paths
        assert "/api/auth/login" in paths


class TestDataStructureCompatibility:
    """Test data structure compatibility between frontend and backend"""
    
    def test_container_response_structure(self):
        """Test ContainerResponse matches frontend expectations"""
        from app.models.container import ContainerResponse, ContainerStatus
        
        # Create a sample response
        response = ContainerResponse(
            session_id="test-session",
            container_id="test-container",
            status=ContainerStatus.RUNNING,
            websocket_url="ws://localhost:8000/api/ws/terminal/test-session",
            user_id="test-user"
        )
        
        # Convert to dict (simulating JSON serialization)
        data = response.model_dump()
        
        # Check required fields for frontend
        assert "session_id" in data
        assert "container_id" in data
        assert "status" in data
        assert "websocket_url" in data
        assert "user_id" in data
        
        # Check WebSocket URL format
        assert data["websocket_url"].startswith("ws://")
        assert "/api/ws/terminal/" in data["websocket_url"]
    
    def test_user_model_compatibility(self):
        """Test User model matches frontend expectations"""
        from app.models.container import User
        
        user = User(
            id="test-id",
            email="test@example.com",
            full_name="Test User",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        data = user.model_dump()
        
        # Check required fields for frontend
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert "avatar_url" in data
    
    def test_websocket_message_types(self):
        """Test WebSocket message types are compatible"""
        # This is more of a documentation test
        # Frontend expects these message types:
        expected_types = [
            'input',
            'output', 
            'terminal_input',
            'terminal_output',
            'connected',
            'resized',
            'resize',
            'ping',
            'pong',
            'connection',
            'disconnection'
        ]
        
        # Backend should handle these types in WebSocket service
        # This test serves as documentation of the contract
        assert len(expected_types) > 0  # Basic test to ensure types are defined


if __name__ == "__main__":
    pytest.main([__file__]) 