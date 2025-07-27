"""
Container management service using python-on-whales
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from contextlib import asynccontextmanager

try:
    from python_on_whales import DockerClient, Container
    from python_on_whales.exceptions import DockerException
    DOCKER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Docker client not available: {e}")
    DOCKER_AVAILABLE = False
    DockerClient = None
    Container = None
    DockerException = Exception

from app.core.config import settings
from app.models.container import ContainerStatus, ContainerInfo, TerminalSession
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class ContainerService:
    """Service for managing Docker containers and terminal sessions"""
    
    def __init__(self):
        self.docker = None
        self.active_containers: Dict[str, Container] = {}
        # Note: container_sessions now stored in database, this is just for runtime tracking
        self.container_sessions: Dict[str, TerminalSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Initialize Docker client if available
        if DOCKER_AVAILABLE:
            try:
                self.docker = DockerClient(host=settings.DOCKER_HOST)
                # Test Docker connection
                self.docker.system.info()
                self._initialized = True
                logger.info("Docker client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                self.docker = None
        else:
            logger.error("Docker client not available - python-on-whales not installed")
    
    def _check_docker_available(self):
        """Check if Docker is available and raise appropriate error if not"""
        if not DOCKER_AVAILABLE:
            raise ImportError("Docker client not available. Please install python-on-whales: pip install python-on-whales")
        
        if not self.docker:
            raise ConnectionError("Docker daemon is not accessible. Please ensure Docker is running and accessible.")
        
        if not self._initialized:
            raise RuntimeError("Container service not properly initialized")
        
    async def start(self):
        """Start the container service and cleanup task"""
        logger.info("Starting Container Service")
        
        try:
            self._check_docker_available()
            await self._ensure_network_exists()
            self._cleanup_task = asyncio.create_task(self._cleanup_containers())
            logger.info("Container service started successfully")
        except Exception as e:
            logger.error(f"Failed to start container service: {e}")
            # Don't raise the error - allow the service to start in degraded mode
        
    async def stop(self):
        """Stop the container service and cleanup all containers"""
        logger.info("Stopping Container Service")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Clean up all active containers
        for container_id in list(self.active_containers.keys()):
            try:
                await self.terminate_container(container_id)
            except Exception as e:
                logger.error(f"Error terminating container {container_id} during shutdown: {e}")
            
    async def create_container(
        self, 
        user_id: str, 
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        initial_files: Optional[Dict[str, str]] = None
    ) -> TerminalSession:
        """Create a new container for a user"""
        
        # Check Docker availability first
        self._check_docker_available()
        
        # Check if user already has an active container
        existing = await self._get_user_active_container(user_id)
        if existing:
            raise ValueError(f"User {user_id} already has an active container")
            
        session_id = str(uuid.uuid4())
        container_name = f"pyexec-{user_id}-{session_id[:8]}"
        
        try:
            logger.info(f"Creating container {container_name} for user {user_id}")
            
            # Create container with security constraints
            container = self.docker.run(
                image=settings.CONTAINER_IMAGE,
                name=container_name,
                detach=True,
                tty=True,
                interactive=True,
                remove=False,  # We'll manage cleanup manually
                user="1000:1000",  # Non-root user
                networks=[],  # Start with no network access
                cpus=settings.CONTAINER_CPU_LIMIT,
                memory=settings.CONTAINER_MEMORY_LIMIT,
                workdir="/workspace",
                envs={
                    "PYTHONUNBUFFERED": "1",
                    "TERM": "xterm-256color"
                },
                volumes=[
                    # Create a temporary workspace volume
                    (f"{container_name}-workspace", "/workspace")
                ]
            )
            
            # Store container reference
            self.active_containers[container.id] = container
            
            # Create terminal session record in database
            session = await db_service.create_terminal_session(
                user_id=user_id,
                container_id=container.id,
                project_id=project_id,
                container_image=settings.CONTAINER_IMAGE,
                cpu_limit=settings.CONTAINER_CPU_LIMIT,
                memory_limit=settings.CONTAINER_MEMORY_LIMIT,
                environment_vars={}
            )
            
            # Update status to running
            await db_service.update_terminal_session(
                session.id, 
                status=ContainerStatus.RUNNING.value
            )
            
            # Store in runtime cache
            self.container_sessions[session.id] = session
            
            # Initialize workspace if files provided
            if initial_files:
                await self._setup_initial_files(container, initial_files)
                # Store files in database if project exists
                if project_id:
                    for file_path, content in initial_files.items():
                        await db_service.create_project_file(
                            project_id=project_id,
                            file_path=file_path,
                            file_name=file_path.split('/')[-1],
                            content=content,
                            mime_type="text/plain"
                        )
                
            logger.info(f"Container {container_name} created successfully")
            return session
            
        except DockerException as e:
            logger.error(f"Failed to create container: {e}")
            # Clean up database record if container creation failed
            if 'session' in locals():
                await db_service.update_terminal_session(
                    session.id, 
                    status=ContainerStatus.ERROR.value
                )
            raise RuntimeError(f"Container creation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating container: {e}")
            # Clean up database record if container creation failed
            if 'session' in locals():
                await db_service.update_terminal_session(
                    session.id, 
                    status=ContainerStatus.ERROR.value
                )
            raise
            
    async def get_container_info(self, session_id: str) -> Optional[ContainerInfo]:
        """Get container information"""
        try:
            self._check_docker_available()
        except Exception as e:
            logger.error(f"Docker not available for container info: {e}")
            return None
            
        # Get session from database first, then check runtime cache
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return None
            
        container = self.active_containers.get(session.container_id)
        if not container:
            return None
            
        try:
            # Refresh container state
            container.reload()
            stats = container.stats(stream=False)
            
            return ContainerInfo(
                id=container.id,
                status=ContainerStatus.RUNNING if container.state.running else ContainerStatus.STOPPED,
                image=container.image.repo_tags[0] if container.image.repo_tags else "unknown",
                created_at=session.created_at,
                last_activity=session.last_activity,
                cpu_usage=self._calculate_cpu_usage(stats),
                memory_usage=stats.get("memory_usage", 0) if stats else None,
                network_enabled=self._is_network_enabled(container)
            )
        except DockerException as e:
            logger.error(f"Failed to get container info: {e}")
            return None
    
    async def list_user_containers(self, user_id: str) -> List[TerminalSession]:
        """List all containers for a user"""
        try:
            # Get sessions from database
            sessions = await db_service.get_user_terminal_sessions(user_id)
            return sessions
        except Exception as e:
            logger.error(f"Failed to list user containers: {e}")
            return []
            
    async def terminate_container(self, session_id: str) -> bool:
        """Terminate a container and clean up resources"""
        # Get session from database
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return False
        
        # Try to clean up Docker container if Docker is available
        if self.docker and session.container_id in self.active_containers:
            container = self.active_containers[session.container_id]
            try:
                logger.info(f"Terminating container {container.name}")
                
                # Disconnect from networks
                await self._disconnect_from_pypi_network(container)
                
                # Stop and remove container
                container.stop(time=5)
                container.remove(volumes=True)
                
                # Clean up runtime references
                del self.active_containers[session.container_id]
                
                logger.info(f"Container {container.name} terminated successfully")
            except DockerException as e:
                logger.error(f"Failed to terminate container: {e}")
                # Continue with database cleanup even if Docker cleanup fails
        
        # Always update database status
        await db_service.terminate_terminal_session(session_id)
        
        # Clean up runtime references
        if session_id in self.container_sessions:
            del self.container_sessions[session_id]
        
        return True
            
    async def enable_network_access(self, session_id: str) -> bool:
        """Enable network access for package installation"""
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return False
            
        container = self.active_containers.get(session.container_id)
        if not container:
            return False
            
        try:
            # Connect to PyPI network
            self.docker.network.connect(settings.PYPI_NETWORK_NAME, container)
            logger.info(f"Network access enabled for container {container.name}")
            return True
        except DockerException as e:
            logger.error(f"Failed to enable network access: {e}")
            return False
            
    async def disable_network_access(self, session_id: str) -> bool:
        """Disable network access after package installation"""
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return False
            
        container = self.active_containers.get(session.container_id)
        if not container:
            return False
            
        return await self._disconnect_from_pypi_network(container)
        
    async def _get_user_active_container(self, user_id: str) -> Optional[TerminalSession]:
        """Check if user has an active container"""
        # Check database for active sessions
        sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        return sessions[0] if sessions else None
        
    async def _setup_initial_files(self, container: Container, files: Dict[str, str]):
        """Setup initial files in the container workspace"""
        for file_path, content in files.items():
            try:
                # Create file in container
                container.execute([
                    "sh", "-c", 
                    f"mkdir -p $(dirname {file_path}) && cat > {file_path}"
                ], input=content.encode())
            except DockerException as e:
                logger.error(f"Failed to create file {file_path}: {e}")
                
    async def _ensure_network_exists(self):
        """Ensure the PyPI network exists"""
        try:
            # Check if network exists
            networks = self.docker.network.list()
            pypi_network_exists = any(net.name == settings.PYPI_NETWORK_NAME for net in networks)
            
            if not pypi_network_exists:
                logger.info(f"Creating PyPI network: {settings.PYPI_NETWORK_NAME}")
                self.docker.network.create(
                    name=settings.PYPI_NETWORK_NAME,
                    driver="bridge",
                    internal=False  # Allow external access
                )
        except DockerException as e:
            logger.error(f"Failed to ensure PyPI network exists: {e}")
            
    async def _disconnect_from_pypi_network(self, container: Container) -> bool:
        """Disconnect container from PyPI network"""
        try:
            self.docker.network.disconnect(settings.PYPI_NETWORK_NAME, container)
            logger.info(f"Network access disabled for container {container.name}")
            return True
        except DockerException as e:
            logger.error(f"Failed to disable network access: {e}")
            return False
            
    def _is_network_enabled(self, container: Container) -> bool:
        """Check if container has network access"""
        try:
            container.reload()
            networks = container.network_settings.networks
            return settings.PYPI_NETWORK_NAME in networks
        except:
            return False
            
    def _calculate_cpu_usage(self, stats: Dict) -> Optional[float]:
        """Calculate CPU usage percentage from container stats"""
        if not stats:
            return None
        try:
            # Simplified CPU usage calculation
            cpu_stats = stats.get("cpu_stats", {})
            cpu_usage = cpu_stats.get("cpu_usage", {})
            total_usage = cpu_usage.get("total_usage", 0)
            system_usage = cpu_stats.get("system_cpu_usage", 0)
            
            if system_usage > 0:
                return (total_usage / system_usage) * 100.0
        except:
            pass
        return None
        
    async def _cleanup_containers(self):
        """Background task to clean up expired containers"""
        while True:
            try:
                await asyncio.sleep(settings.CONTAINER_CLEANUP_INTERVAL)
                
                # Use database service to find and mark expired sessions
                expired_count = await db_service.cleanup_expired_sessions(
                    timeout_seconds=settings.CONTAINER_TIMEOUT_SECONDS
                )
                
                if expired_count > 0:
                    logger.info(f"Marked {expired_count} expired sessions for cleanup")
                    
                    # Clean up actual Docker containers for expired sessions
                    # Get all terminated sessions that still have active containers
                    for container_id in list(self.active_containers.keys()):
                        session = await db_service.get_terminal_session_by_container(container_id)
                        if session and session.status == ContainerStatus.TERMINATED.value:
                            logger.info(f"Cleaning up Docker container for terminated session: {session.id}")
                            await self.terminate_container(session.id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in container cleanup task: {e}")


# Global container service instance
container_service = ContainerService() 