"""
Tests for ContainerService - Docker container management
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from python_on_whales.exceptions import DockerException

from app.services.container_service import ContainerService
from app.models.container import ContainerStatus, TerminalSession
from app.core.config import settings


class TestContainerService:
    """Test suite for ContainerService"""

    @pytest.mark.unit
    async def test_service_initialization(self, mock_docker_client):
        """Test ContainerService initialization"""
        service = ContainerService()
        assert service.active_containers == {}
        assert service.container_sessions == {}
        assert not service._cleanup_task_running
        
    @pytest.mark.unit
    async def test_service_start_stop(self, mock_docker_client):
        """Test service startup and shutdown"""
        service = ContainerService()
        service.docker = mock_docker_client
        
        # Test start
        await service.start()
        assert service._cleanup_task_running
        
        # Test stop
        await service.stop()
        assert not service._cleanup_task_running

    @pytest.mark.unit
    async def test_create_container_success(self, container_service, test_container_config):
        """Test successful container creation"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        assert session.user_id == test_container_config["user_id"]
        assert session.project_name == test_container_config["project_name"]
        assert session.status == ContainerStatus.RUNNING.value
        assert session.container_id in container_service.active_containers
        assert session.id in container_service.container_sessions

    @pytest.mark.unit
    async def test_create_container_duplicate_user(self, container_service, test_container_config):
        """Test container creation with duplicate user (should replace existing)"""
        # Create first container
        session1 = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name="project1"
        )
        
        # Create second container for same user
        session2 = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name="project2"
        )
        
        # First container should be terminated
        assert session1.id not in container_service.container_sessions
        assert session2.id in container_service.container_sessions
        assert len(container_service.container_sessions) == 1

    @pytest.mark.unit
    async def test_create_container_docker_failure(self, mock_docker_client):
        """Test container creation with Docker failure"""
        service = ContainerService()
        service.docker = mock_docker_client
        
        # Mock Docker run to raise exception
        mock_docker_client.run.side_effect = DockerException("Docker error")
        
        with pytest.raises(Exception) as exc_info:
            await service.create_container("test-user", "test-project")
        
        assert "Container creation failed" in str(exc_info.value)

    @pytest.mark.unit
    async def test_get_container_info_success(self, container_service, test_container_config):
        """Test getting container information"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        info = await container_service.get_container_info(session.id)
        
        assert info.session_id == session.id
        assert info.container_id == session.container_id
        assert info.status == ContainerStatus.RUNNING.value
        assert info.cpu_usage > 0
        assert info.memory_usage > 0

    @pytest.mark.unit
    async def test_get_container_info_not_found(self, container_service):
        """Test getting info for non-existent container"""
        info = await container_service.get_container_info("non-existent-id")
        assert info is None

    @pytest.mark.unit
    async def test_terminate_container_success(self, container_service, test_container_config):
        """Test successful container termination"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        success = await container_service.terminate_container(session.id)
        
        assert success
        assert session.id not in container_service.container_sessions
        assert session.container_id not in container_service.active_containers

    @pytest.mark.unit
    async def test_terminate_container_not_found(self, container_service):
        """Test terminating non-existent container"""
        success = await container_service.terminate_container("non-existent-id")
        assert not success

    @pytest.mark.unit
    async def test_enable_network_access(self, container_service, test_container_config):
        """Test enabling network access for package installation"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        success = await container_service.enable_network_access(session.container_id)
        assert success
        
        # Verify network was connected
        container_service.docker.network.connect.assert_called_once()

    @pytest.mark.unit
    async def test_disable_network_access(self, container_service, test_container_config):
        """Test disabling network access after package installation"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        # Enable first
        await container_service.enable_network_access(session.container_id)
        
        # Then disable
        success = await container_service.disable_network_access(session.container_id)
        assert success
        
        # Verify network was disconnected
        container_service.docker.network.disconnect.assert_called_once()

    @pytest.mark.unit
    async def test_cleanup_expired_containers(self, container_service, test_container_config):
        """Test cleanup of expired containers"""
        # Create container
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        # Mock the session as expired
        session.created_at = session.created_at.replace(year=2020)  # Make it old
        container_service.container_sessions[session.id] = session
        
        # Run cleanup
        await container_service._cleanup_expired_containers()
        
        # Container should be removed
        assert session.id not in container_service.container_sessions

    @pytest.mark.unit
    async def test_list_user_containers(self, container_service, test_container_config):
        """Test listing containers for a specific user"""
        user_id = test_container_config["user_id"]
        
        # Create multiple containers for the user
        session1 = await container_service.create_container(user_id, "project1")
        session2 = await container_service.create_container(user_id, "project2")
        
        # Create container for different user
        await container_service.create_container("other-user", "project3")
        
        user_containers = await container_service.list_user_containers(user_id)
        
        # Should only return containers for the specified user
        assert len(user_containers) == 1  # Only latest due to replacement policy
        assert user_containers[0].user_id == user_id

    @pytest.mark.unit
    async def test_container_stats_collection(self, container_service, test_container_config):
        """Test container statistics collection"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        stats = await container_service._get_container_stats(session.container_id)
        
        assert "cpu_percent" in stats
        assert "memory_usage" in stats
        assert "memory_limit" in stats
        assert stats["cpu_percent"] >= 0
        assert stats["memory_usage"] > 0

    @pytest.mark.unit
    async def test_network_creation(self, container_service):
        """Test PyPI network creation"""
        await container_service._ensure_pypi_network()
        
        # Should attempt to create network
        container_service.docker.network.create.assert_called_once_with(
            settings.PYPI_NETWORK_NAME
        )

    @pytest.mark.unit
    async def test_container_health_check(self, container_service, test_container_config):
        """Test container health checking"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        is_healthy = await container_service._check_container_health(session.container_id)
        assert is_healthy  # Mock container is always healthy

    @pytest.mark.unit
    async def test_concurrent_container_creation(self, container_service):
        """Test concurrent container creation for different users"""
        tasks = []
        for i in range(5):
            task = container_service.create_container(f"user-{i}", f"project-{i}")
            tasks.append(task)
        
        sessions = await asyncio.gather(*tasks)
        
        # All containers should be created successfully
        assert len(sessions) == 5
        assert len(container_service.container_sessions) == 5
        
        # Each should have unique IDs
        session_ids = [s.id for s in sessions]
        assert len(set(session_ids)) == 5

    @pytest.mark.unit
    async def test_resource_limits_enforcement(self, container_service, test_container_config):
        """Test that resource limits are properly set"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        # Verify Docker run was called with correct resource limits
        call_args = container_service.docker.run.call_args
        assert call_args.kwargs["cpus"] == settings.CONTAINER_CPU_LIMIT
        assert call_args.kwargs["memory"] == settings.CONTAINER_MEMORY_LIMIT
        assert call_args.kwargs["user"] == "1000:1000"  # Non-root user

    @pytest.mark.unit
    async def test_container_naming_convention(self, container_service, test_container_config):
        """Test container naming follows expected convention"""
        session = await container_service.create_container(
            user_id=test_container_config["user_id"],
            project_name=test_container_config["project_name"]
        )
        
        # Check that container name follows pattern
        call_args = container_service.docker.run.call_args
        container_name = call_args.kwargs["name"]
        
        assert container_name.startswith("pyexec-")
        assert test_container_config["user_id"] in container_name
        assert len(container_name.split("-")) >= 3  # pyexec-user-hash format

    @pytest.mark.unit
    def test_container_session_model(self, mock_terminal_session):
        """Test TerminalSession model validation"""
        session = mock_terminal_session
        
        assert session.user_id == "test-user"
        assert session.container_id == "test-container-id"
        assert session.status == ContainerStatus.RUNNING.value

    @pytest.mark.slow
    @pytest.mark.unit
    async def test_cleanup_task_running(self, container_service):
        """Test that cleanup task runs periodically"""
        # Start service
        await container_service.start()
        
        # Wait a short time to ensure cleanup task is running
        await asyncio.sleep(0.1)
        
        assert container_service._cleanup_task_running
        
        # Stop service
        await container_service.stop()
        assert not container_service._cleanup_task_running


class TestContainerServiceIntegration:
    """Integration tests for ContainerService (require Docker)"""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_real_container_creation(self, skip_if_no_docker):
        """Test creating a real Docker container"""
        service = ContainerService()
        await service.start()
        
        try:
            session = await service.create_container("integration-test-user", "test-project")
            
            assert session.container_id
            assert session.status == ContainerStatus.RUNNING.value
            
            # Verify container actually exists
            info = await service.get_container_info(session.id)
            assert info is not None
            assert info.status == ContainerStatus.RUNNING.value
            
            # Clean up
            await service.terminate_container(session.id)
            
        finally:
            await service.stop()

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.slow
    async def test_real_container_execution(self, skip_if_no_docker):
        """Test executing commands in a real container"""
        service = ContainerService()
        await service.start()
        
        try:
            session = await service.create_container("integration-test-user", "test-project")
            container = service.active_containers[session.container_id]
            
            # Test basic command execution
            result = container.execute(["echo", "Hello, World!"])
            assert "Hello, World!" in result
            
            # Test Python execution with pre-installed libraries
            result = container.execute([
                "python", "-c", 
                "import pandas as pd; print(f'pandas {pd.__version__}')"
            ])
            assert "pandas" in result
            
            # Clean up
            await service.terminate_container(session.id)
            
        finally:
            await service.stop()

    @pytest.mark.integration
    @pytest.mark.docker
    @pytest.mark.network
    async def test_network_isolation(self, skip_if_no_docker):
        """Test network isolation and PyPI access"""
        service = ContainerService()
        await service.start()
        
        try:
            session = await service.create_container("integration-test-user", "test-project")
            container = service.active_containers[session.container_id]
            
            # Test that network is initially disabled
            result = container.execute(["ping", "-c", "1", "google.com"])
            # Should fail due to no network access
            
            # Enable network access
            await service.enable_network_access(session.container_id)
            
            # Now PyPI access should work (if network is configured properly)
            # This is a basic test - full network testing would require more setup
            
            # Disable network access
            await service.disable_network_access(session.container_id)
            
            # Clean up
            await service.terminate_container(session.id)
            
        finally:
            await service.stop() 