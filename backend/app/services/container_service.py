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
        
        if not DOCKER_AVAILABLE:
            logger.error("❌ Docker client not available - cannot create container")
            raise ImportError("Docker client not available. Please install python-on-whales and ensure Docker is running.")
        
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
                networks=settings.PACKAGE_NETWORK_NAME,  # Connect to package installation network
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
                
                # Create a simple README
                readme_content = '''# Python Workspace

Welcome to your Python development environment!

## Files in this workspace:
- `main.py` - Your main Python script (edit and run this)
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
                
                # Cache initial files for instant access
                try:
                    await self._cache_initial_files(session.id, {
                        '/workspace/main.py': welcome_content,
                        '/workspace/README.md': readme_content
                    })
                    logger.info("🚀 Initial files cached for instant access")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Failed to cache initial files: {cache_error}")
                    # Don't fail container creation if caching fails
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to create initial files: {e}")
                # Don't fail container creation if file creation fails
            
            # Setup initial Python environment in container
            logger.info("🐍 Setting up Python environment...")
            try:
                # Test Python environment without creating files
                result = container.execute(["python3", "-c", "print('Python environment ready!')"])
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
        try:
            self._check_docker_available()
        except Exception as e:
            logger.error(f"Docker not available for container info: {e}")
            return None
            
        # Get session from database first, then check runtime cache
        session = await db_service.get_terminal_session(session_id)
        if not session:
            return None
            
        # Look up container by session ID (how containers are stored)
        # First try with the database session ID (how containers are actually stored)
        container = None
        if hasattr(session, 'id'):
            container = self.active_containers.get(session.id)
        
        # Fallback to session_id parameter if not found
        if not container:
            container = self.active_containers.get(session_id)
        
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
        # Look up container by session ID (how containers are stored)
        container = None
        if self.docker:
            # First try with the database session ID (how containers are actually stored)
            if hasattr(session, 'id'):
                container = self.active_containers.get(session.id)
            
            # Fallback to session_id parameter if not found
            if not container:
                container = self.active_containers.get(session_id)
        
        if container:
            try:
                logger.info(f"Terminating container {container.name}")
                
                # No need to disconnect from networks - container will be removed
                
                # Stop and remove container
                container.stop(time=5)
                container.remove(volumes=True)
                
                # Clean up runtime references
                # Remove from active_containers using the session ID key
                if session_id in self.active_containers:
                    del self.active_containers[session_id]
                elif hasattr(session, 'id') and session.id in self.active_containers:
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
            
    # Network access methods removed - containers now have PyPI access by default
            

        
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
        """Ensure the package installation network exists"""
        try:
            # Check if network exists
            networks = self.docker.network.list()
            network_exists = any(net.name == settings.PACKAGE_NETWORK_NAME for net in networks)
            
            if not network_exists:
                logger.info(f"Creating package installation network: {settings.PACKAGE_NETWORK_NAME}")
                logger.info(f"Allowed domains: {', '.join(settings.ALLOWED_DOMAINS[:5])}... ({len(settings.ALLOWED_DOMAINS)} total)")
                self.docker.network.create(
                    name=settings.PACKAGE_NETWORK_NAME,
                    driver="bridge",
                    internal=False  # Allow external access to package repositories
                )
        except DockerException as e:
            logger.error(f"Failed to ensure package installation network exists: {e}")
            

            

            
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
                    for container_id in list(self.active_containers.keys()):
                        session = await db_service.get_terminal_session_by_container(container_id)
                        if session and session.status == ContainerStatus.TERMINATED.value:
                            logger.info(f"Cleaning up Docker container for terminated session: {session.id}")
                            await self.terminate_container(session.id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in container cleanup task: {e}")

    async def _cache_initial_files(self, container_id: str, files: Dict[str, str]):
        """Cache initial files to the frontend cache for instant access"""
        try:
            # Import here to avoid circular imports
            from app.services.websocket_service import websocket_service
            
            # Send initial files to all connected clients for this container
            # This will be picked up by the frontend and cached automatically
            for file_path, content in files.items():
                cache_message = {
                    "type": "initial_file_cache",
                    "data": {
                        "container_id": container_id,
                        "file_path": file_path,
                        "content": content,
                        "language": "python" if file_path.endswith('.py') else "markdown",
                        "size": len(content),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                # Broadcast to all sessions for this container
                await websocket_service.manager._broadcast_to_session(container_id, cache_message)
                
            logger.info(f"📦 Cached {len(files)} initial files for container {container_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache initial files: {e}")
            # Don't raise - this is a performance optimization, not critical


# Global container service instance
container_service = ContainerService() 