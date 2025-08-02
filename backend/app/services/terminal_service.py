"""
Terminal service for managing Docker container PTY sessions and terminal I/O
"""
import asyncio
import logging
import re
import os
import signal
import threading
from typing import Optional, Dict, AsyncGenerator, List
from datetime import datetime
from queue import Queue, Empty

import ptyprocess

from app.core.config import settings
from app.models.container import TerminalOutput, ContainerStatus
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class TerminalSession:
    """Represents an active terminal session with proper PTY inside a Docker container"""
    
    def __init__(self, session_id: str, container):
        self.session_id = session_id
        self.container = container
        self.pty_process = None
        self.is_active = False
        self.command_history: list = []
        self.current_directory = "/workspace"
        self.output_queue = Queue()
        self.reader_thread = None
        self._stop_event = threading.Event()
        
    async def start_shell(self) -> bool:
        """Start an interactive shell with proper PTY in the container"""
        try:
            logger.info(f"Starting PTY shell for session {self.session_id}")
            
            # Create a PTY process that runs docker exec with proper terminal
            docker_cmd = [
                'docker', 'exec', '-it', 
                self.container.id,
                '/bin/bash', '--login'
            ]
            
            # Start the PTY process
            self.pty_process = ptyprocess.PtyProcess.spawn(
                docker_cmd,
                dimensions=(settings.TERMINAL_ROWS, settings.TERMINAL_COLS),
                cwd=None,
                env=os.environ.copy()
            )
            
            self.is_active = True
            
            # Start the output reader thread
            self.reader_thread = threading.Thread(
                target=self._read_output_thread,
                daemon=True
            )
            self.reader_thread.start()
            
            logger.info(f"PTY shell started for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start PTY shell: {e}")
            return False
            
    async def send_input(self, data: str) -> bool:
        """Send input to the terminal"""
        try:
            if self.pty_process and self.pty_process.isalive():
                self.pty_process.write(data.encode('utf-8'))
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send input: {e}")
            return False
            
    async def get_output(self) -> Optional[str]:
        """Get output from the terminal"""
        try:
            return self.output_queue.get_nowait()
        except Empty:
            return None
            
    def _read_output_thread(self):
        """Thread function to read PTY output"""
        while not self._stop_event.is_set() and self.is_active:
            try:
                # Read from PTY with timeout
                if self.pty_process and self.pty_process.isalive():
                    import select
                    ready, _, _ = select.select([self.pty_process.fd], [], [], 0.1)
                    if ready:
                        # Data is available, read it
                        data = self.pty_process.read(size=settings.PTY_BUFFER_SIZE or 8192)
                        if data:
                            # Decode and put in queue
                            decoded_data = data.decode('utf-8', errors='ignore')
                            self.output_queue.put(decoded_data)
                    # If no data available, just continue (timeout case)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error in PTY reader thread: {e}")
                break
                
        logger.info(f"PTY reader thread stopped for session {self.session_id}")
        
    async def close(self):
        """Close the terminal session"""
        self.is_active = False
        self._stop_event.set()
        
        if self.pty_process:
            try:
                self.pty_process.terminate()
                self.pty_process.wait()
            except Exception as e:
                logger.error(f"Error closing PTY process: {e}")
                
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)


class TerminalService:
    """Service for managing terminal sessions and PTY operations"""
    
    def __init__(self):
        self.active_sessions: Dict[str, TerminalSession] = {}
        # Network commands now work by default with PyPI network access
        
    async def create_terminal_session(self, session_id: str) -> bool:
        """Create a new terminal session"""
        # Get container session from database
        container_session = await db_service.get_terminal_session(session_id)
        if not container_session:
            logger.error(f"No container session found for {session_id}")
            return False
            
        # Import container_service here to avoid circular import
        from app.services.container_service import container_service
        
        # Try to get container using session_id as both string and UUID
        container = container_service.active_containers.get(session_id)
        if not container and hasattr(container_session, 'id'):
            # If not found, try with the actual session ID from the database record
            container = container_service.active_containers.get(container_session.id)
        
        if not container:
            logger.error(f"No active container found for session {session_id}")
            logger.error(f"Available containers: {list(container_service.active_containers.keys())}")
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
            
        # Record command in database
        await db_service.create_terminal_command(
            session_id=session_id,
            command=command.strip(),
            working_dir=terminal_session.current_directory
        )
        
        # Send command directly (ensure it ends with newline)
        if not command.endswith('\n'):
            command += '\n'
        await terminal_session.send_input(command)
            
        # Update command history in memory
        terminal_session.command_history.append({
            'command': command.strip(),
            'timestamp': datetime.utcnow()
        })
        
        # Update last activity in database
        await db_service.update_terminal_session(
            session_id, 
            last_activity=datetime.utcnow()
        )
            
        return True
        
    async def send_input(self, session_id: str, data: str) -> bool:
        """Send raw input to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        return await terminal_session.send_input(data)
        
    async def get_output_stream(self, session_id: str) -> Optional[AsyncGenerator[TerminalOutput, None]]:
        """Get an async generator for terminal output"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return None
            
        async def output_generator():
            while terminal_session.is_active:
                output = await terminal_session.get_output()
                if output:
                    yield TerminalOutput(
                        session_id=session_id,
                        data=output,
                        stream="stdout",
                        timestamp=datetime.utcnow()
                    )
                else:
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.01)
                    
        return output_generator()
        
    def _needs_network_access(self, command: str) -> bool:
        """Network commands now work by default - no special handling needed"""
        return False  # Always return False since network is always available
        
    async def _handle_network_command(self, session_id: str, command: str):
        """Handle commands that need network access with process-aware management"""
        from app.services.container_service import container_service
        
        try:
            # Enable network access
            network_enabled = await container_service.enable_network_access(session_id)
            if not network_enabled:
                error_msg = "⚠️ Failed to enable network access, trying command anyway...\n"
                await self._send_system_message(session_id, error_msg)
                # Don't return - still try to execute the command
                # It might work if the container already has network access
                
            # Send appropriate notification based on command type
            if self.network_command_patterns['pip_install'].search(command):
                await self._send_system_message(session_id, "🌐 Network enabled for pip install...\n")
            elif any(pattern.search(command) for pattern in [
                self.network_command_patterns['npm_install'],
                self.network_command_patterns['yarn_install'],
                self.network_command_patterns['pnpm_install']
            ]):
                await self._send_system_message(session_id, "🌐 Network enabled for package installation...\n")
                
            # Send the command
            if not command.endswith('\n'):
                command += '\n'
            terminal_session = self.active_sessions.get(session_id)
            if terminal_session:
                await terminal_session.send_input(command)
                
            # Monitor the command process instead of using fixed timeout
            await self._monitor_network_command(session_id, command)
                
            # Disable network access after command completes
            await container_service.disable_network_access(session_id)
            await self._send_system_message(
                session_id, 
                "🔒 Network access disabled for security\n"
            )
            
        except Exception as e:
            logger.error(f"Error handling network command: {e}")
            # Send error message to user but don't terminate session
            await self._send_system_message(
                session_id, 
                f"⚠️ Network command error: {str(e)}\n"
            )
            # Ensure network is disabled even on error
            try:
                await container_service.disable_network_access(session_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup network access: {cleanup_error}")
            
    async def _monitor_network_command(self, session_id: str, command: str):
        """Monitor a network command until completion"""
        from app.services.container_service import container_service
        
        # Get container session from database
        container_session = await db_service.get_terminal_session(session_id)
        if not container_session:
            logger.warning(f"No container session found for monitoring: {session_id}, using fallback timing")
            await asyncio.sleep(60)  # Fallback to reasonable wait time
            return
            
        # Get the container
        container = container_service.active_containers.get(container_session.id)
        if not container:
            logger.warning(f"No active container found for monitoring: {container_session.id}, using fallback timing")
            await asyncio.sleep(60)  # Fallback to reasonable wait time
            return
        
        # Extract the base command (e.g., "pip" from "pip install pytorch")
        base_command = command.strip().split()[0]
        
        # Monitor for process completion with timeout
        max_wait_time = 300  # 5 minutes maximum
        check_interval = 5   # Check every 5 seconds (less frequent to reduce overhead)
        elapsed_time = 0
        
        logger.info(f"Monitoring {base_command} process for session {session_id}")
        
        # Initial wait to let the command start
        await asyncio.sleep(10)
        elapsed_time += 10
        
        while elapsed_time < max_wait_time:
            try:
                # Check if the command process is still running
                # Use a more robust check that won't fail if pgrep isn't available
                result = container.execute(
                    ["sh", "-c", f"ps aux | grep -v grep | grep {base_command} | wc -l"],
                    capture_output=True,
                    text=True
                )
                
                if result.return_code == 0:
                    process_count = int(result.stdout.strip())
                    if process_count == 0:
                        # Process not found, command completed
                        logger.info(f"{base_command} process completed for session {session_id}")
                        break
                else:
                    logger.warning(f"Could not check {base_command} process status, continuing monitoring")
                    
                # Process still running or check failed, wait and check again
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                logger.warning(f"Error monitoring {base_command} process: {e}")
                # If we can't monitor, wait a reasonable time and break
                await asyncio.sleep(30)
                break
        
        if elapsed_time >= max_wait_time:
            logger.warning(f"{base_command} process monitoring timed out after {max_wait_time}s")
        
        logger.info(f"Finished monitoring {base_command} process for session {session_id}")
    
    async def _send_system_message(self, session_id: str, message: str):
        """Send a system message to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if terminal_session:
            # Add system message styling
            styled_message = f"\033[36m{message}\033[0m"
            await terminal_session.send_input(f"echo '{styled_message}'\n")
            
    async def execute_command_sync(self, session_id: str, command: str) -> Optional[str]:
        """Execute a command synchronously and return the output"""
        # Get container session from database
        container_session = await db_service.get_terminal_session(session_id)
        if not container_session:
            return None
            
        from app.services.container_service import container_service
        
        # Try to get container using session_id as both string and UUID
        container = container_service.active_containers.get(session_id)
        if not container and hasattr(container_session, 'id'):
            # If not found, try with the actual session ID from the database record
            container = container_service.active_containers.get(container_session.id)
        
        if not container:
            return None
            
        try:
            # Execute command and capture output
            result = container.execute(
                ["bash", "-c", command],
                capture_output=True,
                text=True
            )
            
            # Record command in database with output
            await db_service.create_terminal_command(
                session_id=session_id,
                command=command,
                working_dir="/workspace",
                exit_code=result.return_code,
                output=result.stdout,
                error_output=result.stderr
            )
            
            return result.stdout if result.stdout else result.stderr
                
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            # Record failed command
            await db_service.create_terminal_command(
                session_id=session_id,
                command=command,
                working_dir="/workspace",
                exit_code=-1,
                error_output=str(e)
            )
            return f"Error: {str(e)}"
            
    async def close_terminal_session(self, session_id: str) -> bool:
        """Close a terminal session"""
        terminal_session = self.active_sessions.get(session_id)
        if not terminal_session:
            return False
            
        await terminal_session.close()
        del self.active_sessions[session_id]
        
        # Update database status
        await db_service.update_terminal_session(
            session_id, 
            status=ContainerStatus.TERMINATED.value,
            terminated_at=datetime.utcnow()
        )
        
        return True


# Create global terminal service instance
terminal_service = TerminalService() 