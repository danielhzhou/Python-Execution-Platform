"""
Terminal service for PTY management and command execution
"""
import asyncio
import logging
import re
from typing import Optional, Dict, Callable, AsyncGenerator
from datetime import datetime

from python_on_whales import Container
from python_on_whales.exceptions import DockerException

from app.core.config import settings
from app.models.container import TerminalOutput
from app.services.container_service import container_service

logger = logging.getLogger(__name__)


class TerminalSession:
    """Represents an active terminal session with PTY"""
    
    def __init__(self, session_id: str, container: Container):
        self.session_id = session_id
        self.container = container
        self.process = None
        self.is_active = False
        self.command_history: list = []
        self.current_directory = "/workspace"
        
    async def start_shell(self) -> bool:
        """Start an interactive shell in the container"""
        try:
            logger.info(f"Starting shell for session {self.session_id}")
            
            # Start an interactive bash session
            self.process = self.container.execute(
                ["bash", "-i"],
                tty=True,
                interactive=True,
                detach=True,
                stream=True
            )
            
            self.is_active = True
            logger.info(f"Shell started for session {self.session_id}")
            return True
            
        except DockerException as e:
            logger.error(f"Failed to start shell: {e}")
            return False
            
    async def send_input(self, data: str) -> bool:
        """Send input to the terminal"""
        if not self.is_active or not self.process:
            return False
            
        try:
            # Send data to the process stdin
            if hasattr(self.process, 'stdin') and self.process.stdin:
                self.process.stdin.write(data.encode())
                await self.process.stdin.drain()
                return True
        except Exception as e:
            logger.error(f"Failed to send input: {e}")
            
        return False
        
    async def read_output(self) -> AsyncGenerator[TerminalOutput, None]:
        """Read output from the terminal"""
        if not self.is_active or not self.process:
            return
            
        try:
            while self.is_active:
                # Read from stdout
                if hasattr(self.process, 'stdout') and self.process.stdout:
                    data = await self.process.stdout.read(settings.PTY_BUFFER_SIZE)
                    if data:
                        yield TerminalOutput(
                            data=data.decode('utf-8', errors='ignore'),
                            timestamp=datetime.utcnow(),
                            stream="stdout"
                        )
                        
                # Read from stderr
                if hasattr(self.process, 'stderr') and self.process.stderr:
                    data = await self.process.stderr.read(settings.PTY_BUFFER_SIZE)
                    if data:
                        yield TerminalOutput(
                            data=data.decode('utf-8', errors='ignore'),
                            timestamp=datetime.utcnow(),
                            stream="stderr"
                        )
                        
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
        except Exception as e:
            logger.error(f"Error reading terminal output: {e}")
            
    async def resize_terminal(self, rows: int, cols: int) -> bool:
        """Resize the terminal"""
        try:
            if self.process and hasattr(self.process, 'resize'):
                self.process.resize(rows, cols)
                return True
        except Exception as e:
            logger.error(f"Failed to resize terminal: {e}")
            
        return False
        
    async def close(self):
        """Close the terminal session"""
        self.is_active = False
        if self.process:
            try:
                self.process.terminate()
            except:
                pass


class TerminalService:
    """Service for managing terminal sessions and PTY operations"""
    
    def __init__(self):
        self.active_sessions: Dict[str, TerminalSession] = {}
        self.pip_install_pattern = re.compile(r'\bpip\s+install\b')
        
    async def create_terminal_session(self, session_id: str) -> bool:
        """Create a new terminal session"""
        # Get container from container service
        container_session = container_service.container_sessions.get(session_id)
        if not container_session:
            logger.error(f"No container session found for {session_id}")
            return False
            
        container = container_service.active_containers.get(container_session.container_id)
        if not container:
            logger.error(f"No active container found for session {session_id}")
            return False
            
        # Create terminal session
        terminal_session = TerminalSession(session_id, container)
        
        # Start the shell
        if await terminal_session.start_shell():
            self.active_sessions[session_id] = terminal_session
            logger.info(f"Terminal session created for {session_id}")
            return True
            
        return False
        
    async def get_terminal_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get an active terminal session"""
        return self.active_sessions.get(session_id)
        
    async def send_command(self, session_id: str, command: str) -> bool:
        """Send a command to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        # Check if this is a pip install command
        if self._is_pip_install_command(command):
            await self._handle_pip_install(session_id, command)
        else:
            # Send command directly
            await terminal_session.send_input(command)
            
        # Update command history
        terminal_session.command_history.append({
            'command': command.strip(),
            'timestamp': datetime.utcnow()
        })
        
        # Update last activity
        container_session = container_service.container_sessions.get(session_id)
        if container_session:
            container_session.last_activity = datetime.utcnow()
            
        return True
        
    async def send_input(self, session_id: str, data: str) -> bool:
        """Send raw input to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        return await terminal_session.send_input(data)
        
    async def get_output_stream(self, session_id: str) -> Optional[AsyncGenerator[TerminalOutput, None]]:
        """Get the output stream for a terminal session"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return None
            
        return terminal_session.read_output()
        
    async def resize_terminal(self, session_id: str, rows: int, cols: int) -> bool:
        """Resize a terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        return await terminal_session.resize_terminal(rows, cols)
        
    async def close_terminal_session(self, session_id: str) -> bool:
        """Close a terminal session"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        await terminal_session.close()
        del self.active_sessions[session_id]
        logger.info(f"Terminal session closed for {session_id}")
        return True
        
    def _is_pip_install_command(self, command: str) -> bool:
        """Check if command is a pip install command"""
        return bool(self.pip_install_pattern.search(command))
        
    async def _handle_pip_install(self, session_id: str, command: str):
        """Handle pip install commands with network access management"""
        logger.info(f"Handling pip install command for session {session_id}")
        
        try:
            # Enable network access
            network_enabled = await container_service.enable_network_access(session_id)
            if not network_enabled:
                error_msg = "Failed to enable network access for package installation\n"
                await self._send_system_message(session_id, error_msg)
                return
                
            # Send notification to user
            await self._send_system_message(
                session_id, 
                "🌐 Network access enabled for package installation...\n"
            )
            
            # Execute the pip install command
            terminal_session = self.active_sessions.get(session_id)
            if terminal_session:
                await terminal_session.send_input(command)
                
                # Wait a bit for the command to complete
                # In a real implementation, you'd want to monitor the command completion
                await asyncio.sleep(2)
                
            # Disable network access
            await container_service.disable_network_access(session_id)
            await self._send_system_message(
                session_id, 
                "🔒 Network access disabled. Package installation complete.\n"
            )
            
        except Exception as e:
            logger.error(f"Error handling pip install: {e}")
            await self._send_system_message(
                session_id, 
                f"❌ Error during package installation: {str(e)}\n"
            )
            # Ensure network is disabled even on error
            await container_service.disable_network_access(session_id)
            
    async def _send_system_message(self, session_id: str, message: str):
        """Send a system message to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if terminal_session:
            # Send as a system message (could be handled differently in WebSocket)
            await terminal_session.send_input(f"\n# {message}")
            
    async def execute_command_sync(self, session_id: str, command: str) -> Optional[str]:
        """Execute a command synchronously and return the output"""
        container_session = container_service.container_sessions.get(session_id)
        if not container_session:
            return None
            
        container = container_service.active_containers.get(container_session.container_id)
        if not container:
            return None
            
        try:
            # Execute command and capture output
            result = container.execute(
                ["bash", "-c", command],
                capture_output=True,
                text=True
            )
            return result.stdout if result.stdout else result.stderr
            
        except DockerException as e:
            logger.error(f"Failed to execute command: {e}")
            return f"Error: {str(e)}"
            
    async def get_working_directory(self, session_id: str) -> Optional[str]:
        """Get the current working directory"""
        result = await self.execute_command_sync(session_id, "pwd")
        return result.strip() if result else None
        
    async def list_files(self, session_id: str, path: str = ".") -> Optional[str]:
        """List files in a directory"""
        command = f"ls -la {path}"
        return await self.execute_command_sync(session_id, command)


# Global terminal service instance
terminal_service = TerminalService() 