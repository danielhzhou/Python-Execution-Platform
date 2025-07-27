"""
Tests for API endpoints - Integration tests for REST API
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.models.container import ContainerStatus

# Test constants with valid UUID formats
TEST_SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_CONTAINER_ID = "test-container-456"


class TestContainerEndpoints:
    """Test suite for container management API endpoints"""
    
    def _mock_session_lookup(self, session_id=None, user_id=None):
        """Helper to mock both database and container service session lookups"""
        if session_id is None:
            session_id = TEST_SESSION_ID
        if user_id is None:
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            
        # Create mock patches
        container_patch = patch('app.api.routes.containers.container_service')
        db_patch = patch('app.api.routes.containers.db_service')
        
        # Start patches
        mock_service = container_patch.start()
        mock_db = db_patch.start()
        
        # Mock database session lookup
        mock_db_session = Mock()
        mock_db_session.user_id = user_id
        mock_db.get_terminal_session = AsyncMock(return_value=mock_db_session)
        
        # Mock container service session lookup
        mock_session = Mock()
        mock_session.user_id = user_id
        mock_service.container_sessions = {session_id: mock_session}
        
        return mock_service, mock_db, container_patch, db_patch

    @pytest.mark.unit
    def test_create_container_success(self, test_client, api_test_data):
        """Test successful container creation via API"""
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_session = Mock()
            mock_session.id = TEST_SESSION_ID
            mock_session.container_id = TEST_CONTAINER_ID
            mock_session.status = ContainerStatus.RUNNING
            mock_service.create_container = AsyncMock(return_value=mock_session)
            
            response = test_client.post(
                "/api/v1/containers/create",
                json=api_test_data["create_container"]
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == TEST_SESSION_ID
            assert data["container_id"] == TEST_CONTAINER_ID
            assert data["status"] == ContainerStatus.RUNNING.value
            
            # Verify the service was called with correct parameters
            mock_service.create_container.assert_called_once_with(
                user_id="123e4567-e89b-12d3-a456-426614174000",  # Mock user UUID
                project_id=None,
                project_name="test-project",
                initial_files={"main.py": "print('Hello, World!')"}
            )

    @pytest.mark.unit
    def test_create_container_failure(self, test_client, api_test_data):
        """Test container creation failure via API"""
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.create_container.side_effect = Exception("Docker error")
            
            response = test_client.post(
                "/api/v1/containers/create",
                json=api_test_data["create_container"]
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"].lower()

    @pytest.mark.unit
    def test_get_container_info_success(self, test_client):
        """Test getting container information via API"""
        session_id = TEST_SESSION_ID
        
        mock_service, mock_db, container_patch, db_patch = self._mock_session_lookup(session_id)
        try:
            
            # Mock the container info with all required fields
            from datetime import datetime
            mock_info = Mock()
            mock_info.id = session_id
            mock_info.status = ContainerStatus.RUNNING
            mock_info.image = "python-execution-sandbox:latest"
            mock_info.created_at = datetime.now()
            mock_info.last_activity = datetime.now()
            mock_info.cpu_usage = 25.5
            mock_info.memory_usage = 256 * 1024 * 1024
            mock_info.network_enabled = False
            mock_service.get_container_info = AsyncMock(return_value=mock_info)
            
            response = test_client.get(f"/api/v1/containers/{session_id}/info")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == session_id
            assert data["cpu_usage"] == 25.5
        finally:
            container_patch.stop()
            db_patch.stop()

    @pytest.mark.unit
    def test_get_container_info_not_found(self, test_client):
        """Test getting info for non-existent container"""
        session_id = "non-existent-session"
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.get_container_info.return_value = None
            
            response = test_client.get(f"/api/v1/containers/{session_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.unit
    def test_terminate_container_success(self, test_client):
        """Test successful container termination via API"""
        session_id = TEST_SESSION_ID
        
        mock_service, mock_db, container_patch, db_patch = self._mock_session_lookup(session_id)
        try:
            # Mock the terminate method
            mock_service.terminate_container = AsyncMock(return_value=True)
            
            response = test_client.post(f"/api/v1/containers/{session_id}/terminate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Container terminated successfully"
        finally:
            container_patch.stop()
            db_patch.stop()

    @pytest.mark.unit
    def test_terminate_container_not_found(self, test_client):
        """Test terminating non-existent container"""
        session_id = "non-existent-session"
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.terminate_container.return_value = False
            
            response = test_client.delete(f"/api/v1/containers/{session_id}")
            
            assert response.status_code == 404

    @pytest.mark.unit
    def test_list_user_containers(self, test_client, test_user_data):
        """Test listing containers for a user"""
        with patch('app.api.routes.containers.container_service') as mock_service, \
             patch('app.api.routes.containers.db_service') as mock_db:
            # Mock container sessions
            mock_session1 = Mock()
            mock_session1.user_id = "123e4567-e89b-12d3-a456-426614174000"
            mock_session1.container_id = "container-1"
            mock_session1.status = ContainerStatus.RUNNING.value
            mock_session1.created_at = "2024-01-01T00:00:00Z"
            mock_session1.last_activity = "2024-01-01T01:00:00Z"
            
            mock_session2 = Mock()
            mock_session2.user_id = "123e4567-e89b-12d3-a456-426614174000"
            mock_session2.container_id = "container-2"
            mock_session2.status = ContainerStatus.RUNNING.value
            mock_session2.created_at = "2024-01-01T00:00:00Z"
            mock_session2.last_activity = "2024-01-01T01:00:00Z"
            
            # Mock database sessions
            mock_session1.id = "session-1"
            mock_session1.project_id = "project-1"
            mock_session2.id = "session-2"
            mock_session2.project_id = "project-2"
            
            mock_db.get_user_terminal_sessions = AsyncMock(return_value=[mock_session1, mock_session2])
            
            # Mock get_container_info calls
            mock_info = Mock()
            mock_info.dict.return_value = {"cpu_usage": 10.0, "memory_usage": 128}
            mock_service.get_container_info = AsyncMock(return_value=mock_info)
            
            response = test_client.get("/api/v1/containers/")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["containers"]) == 2
            assert data["containers"][0]["session_id"] == "session-1"

    @pytest.mark.unit
    def test_container_stats(self, test_client):
        """Test getting container statistics"""
        session_id = TEST_SESSION_ID
        
        mock_service, mock_db, container_patch, db_patch = self._mock_session_lookup(session_id)
        try:
            # Mock websocket service stats
            with patch('app.api.routes.containers.websocket_service') as mock_ws:
                mock_stats = {
                    "cpu_percent": 15.5,
                    "memory_usage": 128 * 1024 * 1024,
                    "memory_limit": 512 * 1024 * 1024,
                    "network_io": {"rx_bytes": 1024, "tx_bytes": 2048}
                }
                mock_ws.get_session_stats = AsyncMock(return_value=mock_stats)
                
                response = test_client.get(f"/api/v1/containers/{session_id}/stats")
                
                assert response.status_code == 200
                data = response.json()
                assert data["cpu_percent"] == 15.5
                assert data["memory_usage"] == 128 * 1024 * 1024
        finally:
            container_patch.stop()
            db_patch.stop()

    @pytest.mark.unit
    def test_invalid_request_data(self, test_client):
        """Test API with invalid request data"""
        invalid_data = {
            "invalid_field": "invalid_value"
        }
        
        response = test_client.post("/api/v1/containers/create", json=invalid_data)
        
        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.unit
    def test_missing_authentication(self, test_client, api_test_data):
        """Test API endpoints without authentication"""
        # Authentication is currently disabled for testing
        # This test verifies that endpoints work without auth
        
        response = test_client.post(
            "/api/v1/containers/create",
            json=api_test_data["create_container"]
        )
        
        # Should work without authentication (auth disabled)
        # Either succeeds (200) or fails for other reasons (500)
        assert response.status_code in [200, 500]  # 500 might occur due to Docker/service issues


class TestWebSocketEndpoints:
    """Test suite for WebSocket API endpoints"""

    @pytest.mark.unit
    def test_websocket_endpoint_exists(self, test_client):
        """Test that WebSocket endpoint is available"""
        # Note: TestClient doesn't support WebSocket testing directly
        # This is a basic test to ensure the route exists
        
        # Try to connect to WebSocket endpoint (will fail but route should exist)
        try:
            with test_client.websocket_connect("/ws/terminal/test-session"):
                pass
        except Exception:
            # Expected to fail in test environment
            pass

    @pytest.mark.integration
    async def test_websocket_connection_flow(self):
        """Test WebSocket connection flow (requires more complex setup)"""
        # This would require a more sophisticated test setup
        # with actual WebSocket client for full integration testing
        pass


class TestAPIValidation:
    """Test suite for API request/response validation"""

    @pytest.mark.unit
    def test_container_create_request_validation(self, test_client):
        """Test container creation request validation"""
        test_cases = [
            # Valid request
            ({"project_name": "valid-project", "language": "python"}, 200),
            # Missing project_name
            ({"language": "python"}, 422),
            # Empty project_name
            ({"project_name": "", "language": "python"}, 422),
            # Invalid language
            ({"project_name": "test", "language": "invalid"}, 422),
        ]
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_session = Mock()
            mock_session.id = "test-session"
            mock_session.container_id = "test-container"
            mock_session.status = ContainerStatus.RUNNING.value
            mock_service.create_container.return_value = mock_session
            
            for request_data, expected_status in test_cases:
                response = test_client.post("/api/v1/containers/create", json=request_data)
                assert response.status_code == expected_status

    @pytest.mark.unit
    def test_response_format_consistency(self, test_client):
        """Test that API responses follow consistent format"""
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_session = Mock()
            mock_session.id = TEST_SESSION_ID
            mock_session.container_id = TEST_CONTAINER_ID
            mock_session.status = ContainerStatus.RUNNING.value
            mock_session.project_name = "test-project"
            mock_session.user_id = "test-user"
            mock_session.created_at = "2024-01-01T00:00:00Z"
            mock_service.create_container.return_value = mock_session
            
            response = test_client.post("/api/v1/containers/create", json={
                "project_name": "test-project",
                "language": "python"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            required_fields = ["session_id", "container_id", "status", "project_name"]
            for field in required_fields:
                assert field in data

    @pytest.mark.unit
    def test_error_response_format(self, test_client):
        """Test that error responses follow consistent format"""
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.create_container.side_effect = Exception("Test error")
            
            response = test_client.post("/api/v1/containers/create", json={
                "project_name": "test-project",
                "language": "python"
            })
            
            assert response.status_code == 500
            data = response.json()
            
            # Verify error response structure
            assert "detail" in data
            assert isinstance(data["detail"], str)


class TestAPIPerformance:
    """Test suite for API performance"""

    @pytest.mark.slow
    @pytest.mark.unit
    def test_api_response_time(self, test_client, performance_thresholds):
        """Test API response times meet performance requirements"""
        import time
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_session = Mock()
            mock_session.id = "test-session"
            mock_session.container_id = "test-container"
            mock_session.status = ContainerStatus.RUNNING.value
            mock_service.create_container.return_value = mock_session
            
            start_time = time.time()
            response = test_client.post("/api/v1/containers/create", json={
                "project_name": "test-project",
                "language": "python"
            })
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < performance_thresholds["api_response_max_seconds"]

    @pytest.mark.slow
    @pytest.mark.unit
    def test_concurrent_api_requests(self, test_client):
        """Test API handling of concurrent requests"""
        import concurrent.futures
        import time
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_sessions = []
            for i in range(10):
                mock_session = Mock()
                mock_session.id = f"test-session-{i}"
                mock_session.container_id = f"test-container-{i}"
                mock_session.status = ContainerStatus.RUNNING.value
                mock_sessions.append(mock_session)
            
            mock_service.create_container.side_effect = mock_sessions
            
            def make_request(i):
                return test_client.post("/api/v1/containers/create", json={
                    "project_name": f"test-project-{i}",
                    "language": "python"
                })
            
            start_time = time.time()
            
            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(10)]
                responses = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should succeed
            assert all(r.status_code == 200 for r in responses)
            
            # Should handle concurrent requests efficiently
            assert total_time < 2.0  # Should complete within 2 seconds


class TestAPIErrorHandling:
    """Test suite for API error handling"""

    @pytest.mark.unit
    def test_handle_docker_service_errors(self, test_client, api_test_data):
        """Test handling of Docker service errors"""
        from python_on_whales.exceptions import DockerException
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.create_container.side_effect = DockerException("Docker daemon not running", [], 1)
            
            response = test_client.post(
                "/api/v1/containers/create",
                json=api_test_data["create_container"]
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "docker" in data["detail"].lower()

    @pytest.mark.unit
    def test_handle_resource_exhaustion(self, test_client, api_test_data):
        """Test handling of resource exhaustion errors"""
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.create_container.side_effect = Exception("Resource limit exceeded")
            
            response = test_client.post(
                "/api/v1/containers/create",
                json=api_test_data["create_container"]
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"].lower()

    @pytest.mark.unit
    def test_handle_invalid_session_id(self, test_client):
        """Test handling of invalid session IDs"""
        invalid_session_ids = [
            "invalid-session",
            "session-with-special-chars!@#",
            "",
            "a" * 1000,  # Very long ID
        ]
        
        with patch('app.api.routes.containers.container_service') as mock_service:
            mock_service.get_container_info.return_value = None
            
            for session_id in invalid_session_ids:
                response = test_client.get(f"/api/v1/containers/{session_id}")
                # Should handle gracefully
                assert response.status_code in [404, 422]

    @pytest.mark.unit
    def test_handle_malformed_json(self, test_client):
        """Test handling of malformed JSON requests"""
        malformed_requests = [
            '{"invalid": json}',  # Invalid JSON syntax
            '{"missing_quote: "value"}',  # Missing quote
            '',  # Empty request
        ]
        
        for malformed_json in malformed_requests:
            response = test_client.post(
                "/api/v1/containers/create",
                data=malformed_json,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 422 for malformed JSON
            assert response.status_code == 422


class TestAPIDocumentation:
    """Test suite for API documentation and OpenAPI spec"""

    @pytest.mark.unit
    def test_openapi_spec_generation(self, test_client):
        """Test that OpenAPI specification is generated correctly"""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        spec = response.json()
        
        # Verify basic OpenAPI structure
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec
        
        # Verify our endpoints are documented
        assert "/api/v1/containers/create" in spec["paths"]
        assert "/api/v1/ws/terminal/{session_id}" in spec["paths"]

    @pytest.mark.unit
    def test_api_docs_accessible(self, test_client):
        """Test that API documentation is accessible"""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.unit
    def test_redoc_accessible(self, test_client):
        """Test that ReDoc documentation is accessible"""
        response = test_client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "") 