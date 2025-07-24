"""
Test fixtures and configuration for the Python Execution Platform backend
"""
import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.container_service import ContainerService
from app.services.terminal_service import TerminalService
from app.services.websocket_service import WebSocketService
from app.models.container import TerminalSession, ContainerStatus


# Remove custom event_loop fixture to avoid conflicts with pytest-asyncio


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing without actual Docker operations."""
    with patch('app.services.container_service.DockerClient') as mock:
        mock_client = Mock()
        mock_container = Mock()
        
        # Configure mock container
        mock_container.id = "test-container-id"
        mock_container.name = "test-container"
        mock_container.execute.return_value = "test output"
        mock_container.stats.return_value = {
            'cpu_percent': 10.5,
            'memory_usage': 256 * 1024 * 1024,  # 256MB
            'memory_limit': 512 * 1024 * 1024   # 512MB
        }
        
        # Configure container state and image for get_container_info
        mock_container.state.running = True
        mock_container.image.repo_tags = ["python-execution-sandbox:latest"]
        mock_container.reload.return_value = None
        
        # Configure mock client
        mock_client.return_value.run.return_value = mock_container
        mock_client.return_value.container.list.return_value = []
        mock_client.return_value.network.list.return_value = []  # Return empty list for network.list()
        mock_client.return_value.network.create.return_value = None
        mock_client.return_value.network.connect.return_value = None
        mock_client.return_value.network.disconnect.return_value = None
        
        mock.return_value = mock_client.return_value
        yield mock_client.return_value


@pytest_asyncio.fixture
async def container_service(mock_docker_client):
    """Create a ContainerService instance with mocked Docker client."""
    service = ContainerService()
    service.docker = mock_docker_client
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
def mock_terminal_session():
    """Create a mock terminal session for testing."""
    return TerminalSession(
        id="test-session-id",
        user_id="test-user",
        container_id="test-container-id",
        status=ContainerStatus.RUNNING.value
    )


@pytest_asyncio.fixture
async def terminal_service(container_service, mock_terminal_session):
    """Create a TerminalService instance for testing."""
    service = TerminalService()
    # Mock the container service dependency
    with patch('app.services.terminal_service.container_service', container_service):
        yield service


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest_asyncio.fixture
async def websocket_service():
    """Create a WebSocketService instance for testing."""
    service = WebSocketService()
    yield service
    # Cleanup any active connections
    service.manager.active_connections.clear()


@pytest.fixture
def test_container_config():
    """Test configuration for container creation."""
    return {
        "user_id": "test-user-123",
        "project_name": "test-project",
        "image": "python-execution-sandbox:latest",
        "cpu_limit": "0.5",
        "memory_limit": "256m"
    }


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing execution."""
    return """
import pandas as pd
import numpy as np

# Create test data
data = pd.DataFrame({
    'x': np.random.normal(0, 1, 10),
    'y': np.random.normal(0, 1, 10)
})

print(f"Data shape: {data.shape}")
print(data.head())
"""


@pytest.fixture
def sample_commands():
    """Sample terminal commands for testing."""
    return [
        "ls -la",
        "pwd",
        "python --version",
        "pip list",
        "echo 'Hello, World!'",
        "cat /etc/os-release"
    ]


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="pyexec_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    test_settings = {
        "CONTAINER_IMAGE": "python-execution-sandbox:test",
        "CONTAINER_CPU_LIMIT": "0.5",
        "CONTAINER_MEMORY_LIMIT": "256m",
        "CONTAINER_TIMEOUT_SECONDS": 300,
        "PYPI_NETWORK_NAME": "test-pypi-net",
        "ALLOWED_DOMAINS": ["pypi.org", "files.pythonhosted.org"],
        "RATE_LIMIT_PER_MINUTE": 30,
        "MAX_CONTAINERS_PER_USER": 1
    }
    
    with patch.object(settings, '__dict__', test_settings):
        yield test_settings


@pytest.fixture
def docker_available():
    """Check if Docker is available for integration tests."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def skip_if_no_docker(docker_available):
    """Skip test if Docker is not available."""
    if not docker_available:
        pytest.skip("Docker is not available")


# Test data fixtures
@pytest.fixture
def test_user_data():
    """Test user data for authentication tests."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser"
    }


@pytest.fixture
def websocket_messages():
    """Sample WebSocket messages for testing."""
    return {
        "terminal_input": {
            "type": "terminal_input",
            "data": {"data": "ls -la\n"}
        },
        "terminal_resize": {
            "type": "terminal_resize", 
            "data": {"rows": 30, "cols": 120}
        },
        "ping": {
            "type": "ping",
            "data": {}
        }
    }


@pytest.fixture
def api_test_data():
    """Test data for API endpoint testing."""
    return {
        "create_container": {
            "project_name": "test-project",
            "initial_files": {"main.py": "print('Hello, World!')"}
        },
        "execute_command": {
            "command": "python --version",
            "timeout": 30
        },
        "file_operation": {
            "filename": "test.py",
            "content": "print('Hello, World!')",
            "operation": "write"
        }
    }


# Async context managers for testing
@pytest.fixture
async def mock_container_context():
    """Context manager for mocking container operations."""
    containers = {}
    
    class MockContainerContext:
        async def create_container(self, user_id: str, project_name: str):
            container_id = f"mock-{user_id}-{project_name}"
            containers[container_id] = {
                "id": container_id,
                "user_id": user_id,
                "project_name": project_name,
                "status": "running"
            }
            return container_id
            
        async def get_container(self, container_id: str):
            return containers.get(container_id)
            
        async def cleanup(self):
            containers.clear()
    
    context = MockContainerContext()
    yield context
    await context.cleanup()


# Performance testing fixtures
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing."""
    return {
        "container_startup_max_seconds": 2.0,
        "command_execution_max_seconds": 1.0,
        "websocket_message_max_seconds": 0.1,
        "api_response_max_seconds": 0.5
    } 