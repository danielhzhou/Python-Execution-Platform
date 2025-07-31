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
            
            # Recover any existing containers that are running but not tracked
            await self._recover_lost_containers()
            
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
        """Create a new container for code execution - ensures only one container per user"""
        logger.info(f"🚀 Starting container creation for user {user_id}")
        logger.info(f"   Project ID: {project_id}")
        logger.info(f"   Project Name: {project_name}")
        logger.info(f"   Initial Files: {len(initial_files) if initial_files else 0} files")
        
        try:
            self._check_docker_available()
        except Exception as e:
            logger.error(f"❌ Docker not available: {e}")
            raise ConnectionError(f"Docker service not available: {str(e)}")
        
        # ALWAYS cleanup existing containers first to ensure single container per user
        logger.info(f"🧹 Cleaning up any existing containers for user {user_id}")
        existing_sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
        
        if existing_sessions:
            logger.info(f"⚠️  Found {len(existing_sessions)} existing active container(s) - cleaning up...")
            for session in existing_sessions:
                try:
                    logger.info(f"   Terminating existing container: {session.container_id}")
                    await self.terminate_container(session.id)
                except Exception as e:
                    logger.warning(f"   Failed to cleanup container {session.id}: {e}")
                    # Continue anyway - we'll create a new one
        
        # Additional Docker-level cleanup to catch any orphaned containers
        await self._cleanup_orphaned_containers(str(user_id))
        
        container_id = f"pyexec-{str(user_id)[:8]}-{uuid.uuid4().hex[:8]}"
        logger.info(f"🐳 Creating Docker container with ID: {container_id}")
        
        try:
            # Create database session first
            logger.info("💾 Creating database session record...")
            
            # Handle project_id - convert to UUID or set to None
            processed_project_id = None
            if project_id:
                try:
                    # Try to parse as UUID
                    import uuid as uuid_module
                    uuid_module.UUID(project_id)
                    processed_project_id = project_id
                except ValueError:
                    # If not a valid UUID, set to None
                    logger.warning(f"Invalid project_id UUID format: {project_id}, setting to None")
                    processed_project_id = None
            
            session = await db_service.create_terminal_session(
                user_id=user_id,
                project_id=processed_project_id,
                container_id=container_id
            )
            logger.info(f"✅ Database session created: {session.id}")
            
            # Create Docker container with Python execution environment
            logger.info(f"🏗️  Starting Docker container creation...")
            container = self.docker.run(
                image=settings.CONTAINER_IMAGE,
                name=container_id,
                detach=True,
                interactive=True,
                tty=True,
                remove=False,  # Don't auto-remove so we can inspect logs
                volumes=[
                    ("/tmp", "/tmp", "rw")
                ],
                envs={
                    "PYTHONUNBUFFERED": "1",
                    "TERM": "xterm-256color",
                    "PYTHONPATH": "/workspace",
                    **(initial_files or {})
                },
                workdir="/workspace",
                user="1000:1000",  # Run as non-root user
                memory=settings.CONTAINER_MEMORY_LIMIT,
                cpus=settings.CONTAINER_CPU_LIMIT,
                networks="none",  # Start with no network access
                command=["/bin/bash", "--login"]  # Start with login shell for better Python environment
            )
            
            logger.info(f"🎉 Docker container created successfully!")
            logger.info(f"   Container ID: {container.id}")
            logger.info(f"   Container Name: {container.name}")
            logger.info(f"   Status: {container.state.status}")
            
            # Create initial workspace files
            logger.info("📝 Creating initial workspace files...")
            try:
                # Create a welcome Python file
                welcome_content = '''# Welcome to Python Execution Platform
# Start coding here...

def main():
    print("Hello, World!")
    print("This is your Python workspace!")
    
    # Try some basic Python features
    numbers = [1, 2, 3, 4, 5]
    squared = [x**2 for x in numbers]
    print(f"Original numbers: {numbers}")
    print(f"Squared numbers: {squared}")
    
    # You can install packages using: pip install package-name
    # Then run your code by clicking the Run button or pressing Ctrl+Enter

if __name__ == "__main__":
    main()
'''
                
                # Write the welcome file to the container
                container.execute(
                    ["bash", "-c", f"cat > /workspace/main.py << 'EOF'\n{welcome_content}\nEOF"]
                )
                
                # Create a requirements.txt file
                requirements_content = '''# Add your Python package dependencies here
# For example:
# numpy==1.24.3
# pandas==2.0.3
# matplotlib==3.7.1
# requests==2.31.0

# Then install them using: pip install -r requirements.txt
'''
                
                container.execute(
                    ["bash", "-c", f"cat > /workspace/requirements.txt << 'EOF'\n{requirements_content}\nEOF"]
                )
                
                # Create a simple README
                readme_content = '''# Python Workspace

Welcome to your Python development environment!

## Files in this workspace:
- `main.py` - Your main Python script (edit and run this)
- `requirements.txt` - Python package dependencies
- `README.md` - This file

## How to use:
1. Edit `main.py` in the code editor
2. Click the "Run" button to execute your code
3. Install packages: `pip install package-name`
4. Use the terminal for any additional commands

Happy coding! 🐍
'''
                
                container.execute(
                    ["bash", "-c", f"cat > /workspace/README.md << 'EOF'\n{readme_content}\nEOF"]
                )
                
                # Make sure files have correct permissions
                container.execute(["chown", "-R", "1000:1000", "/workspace"])
                
                logger.info("✅ Initial workspace files created successfully")
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to create initial files: {e}")
                # Don't fail container creation if file creation fails
            
            # Setup initial Python environment in container
            logger.info("🐍 Setting up Python environment...")
            try:
                # Create a simple Python test file and ensure Python is working
                container.execute([
                    "sh", "-c", 
                    "echo 'print(\"Python environment ready!\")' > /workspace/test.py && python3 /workspace/test.py"
                ])
                logger.info("✅ Python environment verified")
            except Exception as e:
                logger.warning(f"Python environment setup warning: {e}")
            
            # Update database with running status
            logger.info("📝 Updating database session to RUNNING status...")
            updated_session = await db_service.update_terminal_session(
                session.id,
                status=ContainerStatus.RUNNING.value,
                container_id=container.id
            )
            
            # Store container reference
            self.active_containers[session.id] = container
            self.container_sessions[container.id] = session.id
            
            logger.info(f"✅ Container creation completed successfully!")
            logger.info(f"   Session ID: {session.id}")
            logger.info(f"   Container Ready: {container_id}")
            logger.info(f"   Total Active Containers: {len(self.active_containers)}")
            
            return updated_session or session
            
        except DockerException as e:
            logger.error(f"❌ Docker error during container creation: {e}")
            # Update session status to error
            if 'session' in locals():
                await db_service.update_terminal_session(
                    session.id,
                    status=ContainerStatus.ERROR.value
                )
            raise ConnectionError(f"Failed to create Docker container: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error during container creation: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            # Update session status to error
            if 'session' in locals():
                await db_service.update_terminal_session(
                    session.id,
                    status=ContainerStatus.ERROR.value
                )
            raise
            
    async def get_container_info(self, session_id: str) -> Optional[ContainerInfo]:
        """Get container information"""
        # Get session from database first
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return None
            
        container = await self.get_container_by_session(session_id)
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
        """List all active containers for a user"""
        try:
            # Get only active sessions from database
            sessions = await db_service.get_user_terminal_sessions(user_id, active_only=True)
            logger.info(f"Found {len(sessions)} active containers for user {user_id}")
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
        container = await self.get_container_by_session(session_id)
        
        if container:
            try:
                logger.info(f"Terminating container {container.name}")
                
                # Disconnect from networks
                await self._disconnect_from_pypi_network(container)
                
                # Stop and remove container
                container.stop(time=5)
                container.remove(volumes=True)
                
                # Clean up runtime references - use session.id as the key
                if session.id in self.active_containers:
                    del self.active_containers[session.id]
                
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
            
        container = await self.get_container_by_session(session_id)
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
            
        container = await self.get_container_by_session(session_id)
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
    
    async def get_container_by_session(self, session_id: str) -> Optional[Container]:
        """Get Docker container by session ID with unified lookup logic"""
        try:
            self._check_docker_available()
        except Exception as e:
            logger.error(f"Docker not available for container lookup: {e}")
            return None
            
        # First try direct lookup by session ID
        container = self.active_containers.get(session_id)
        if container:
            return container
            
        # Get session from database to try alternative lookups
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return None
            
        if hasattr(session, 'id') and session.id != session_id:
            container = self.active_containers.get(session.id)
            if container:
                return container
                
        return None

    async def get_container_session(self, container_id: str) -> Optional[TerminalSession]:
        """Get terminal session by container ID"""
        try:
            # First try to get session from database by container ID
            session = await db_service.get_terminal_session_by_container(container_id)
            if session:
                return session
            
            # If not found by container ID, try by session ID (for backward compatibility)
            session = await db_service.get_terminal_session(container_id)
            return session
            
        except Exception as e:
            logger.error(f"Error getting container session for {container_id}: {e}")
            return None
        
    async def _cleanup_orphaned_containers(self, user_id: str):
        """Clean up any Docker containers for this user that aren't tracked in database"""
        if not self.docker:
            return
            
        try:
            # Find all containers with names matching this user's pattern
            user_prefix = f"pyexec-{user_id[:8]}"
            all_containers = self.docker.container.list(all=True)
            
            orphaned_containers = []
            for container in all_containers:
                if container.name.startswith(user_prefix):
                    # Check if this container is tracked in our active_containers
                    is_tracked = any(
                        tracked_container.id == container.id 
                        for tracked_container in self.active_containers.values()
                    )
                    
                    if not is_tracked:
                        orphaned_containers.append(container)
            
            if orphaned_containers:
                logger.info(f"🧹 Found {len(orphaned_containers)} orphaned containers for user {user_id}")
                for container in orphaned_containers:
                    try:
                        logger.info(f"   Removing orphaned container: {container.name}")
                        if container.state.status == "running":
                            container.stop(time=5)
                        container.remove(volumes=True)
                    except Exception as e:
                        logger.warning(f"   Failed to remove orphaned container {container.name}: {e}")
                        
        except Exception as e:
            logger.error(f"Error during orphaned container cleanup: {e}")

    async def _recover_lost_containers(self):
        """Recover containers that are running in Docker but not tracked in memory"""
        if not self.docker:
            return
            
        try:
            logger.info("🔍 Scanning for lost containers to recover...")
            
            # Get all running containers with our naming pattern
            all_containers = self.docker.container.list(filters={"name": "pyexec-"})
            
            # Get all active sessions from database
            from app.services.database_service import db_service
            active_sessions = []
            try:
                all_sessions = await db_service.get_all_terminal_sessions()
                active_sessions = [s for s in all_sessions if s.status != ContainerStatus.TERMINATED.value]
            except Exception as e:
                logger.error(f"Failed to get database sessions: {e}")
                return
            
            recovered_count = 0
            for container in all_containers:
                # Find matching database session
                matching_session = None
                for session in active_sessions:
                    # Match by container ID (full or partial) or container name
                    if (container.id == session.container_id or 
                        container.id.startswith(session.container_id) or
                        session.container_id.startswith(container.id) or
                        container.name == session.container_id):
                        matching_session = session
                        break
                
                if matching_session:
                    # Check if already tracked
                    if matching_session.id not in self.active_containers:
                        logger.info(f"🔄 Recovering lost container: {container.name} -> session {matching_session.id}")
                        self.active_containers[matching_session.id] = container
                        self.container_sessions[container.id] = matching_session.id
                        recovered_count += 1
                        
                        # Update database status to RUNNING if needed
                        if matching_session.status != ContainerStatus.RUNNING.value:
                            await db_service.update_terminal_session(
                                matching_session.id,
                                status=ContainerStatus.RUNNING.value
                            )
                else:
                    logger.warning(f"⚠️ Found orphaned container with no database session: {container.name}")
            
            if recovered_count > 0:
                logger.info(f"✅ Recovered {recovered_count} lost containers")
            else:
                logger.info("✅ No lost containers found")
                
        except Exception as e:
            logger.error(f"Error during container recovery: {e}")

    async def recover_containers(self):
        """Public method to manually trigger container recovery"""
        await self._recover_lost_containers()

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
                    for session_id in list(self.active_containers.keys()):
                        session = await db_service.get_terminal_session(session_id)
                        if session and session.status == ContainerStatus.TERMINATED.value:
                            logger.info(f"Cleaning up Docker container for terminated session: {session_id}")
                            await self.terminate_container(session_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in container cleanup task: {e}")


# Global container service instance
container_service = ContainerService()    