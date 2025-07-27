"""
Terminal service for PTY management and command execution
"""
import asyncio
import logging
import re
import os
import signal
import threading
from typing import Optional, Dict, AsyncGenerator
from datetime import datetime
from queue import Queue, Empty

import ptyprocess
from python_on_whales import Container
from python_on_whales.exceptions import DockerException

from app.core.config import settings
from app.models.container import TerminalOutput
from app.services.container_service import container_service
from app.services.database_service import db_service

logger = logging.getLogger(__name__)


class TerminalSession:
    """Represents an active terminal session with proper PTY"""
    
    def __init__(self, session_id: str, container: Container):
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
        if not self.is_active or not self.pty_process:
            return False
            
        try:
            # Write data to PTY
            self.pty_process.write(data.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Failed to send input: {e}")
            return False
        
    async def read_output(self) -> AsyncGenerator[TerminalOutput, None]:
        """Read output from the terminal"""
        while self.is_active:
            try:
                # Get output from queue with timeout
                try:
                    data = self.output_queue.get(timeout=0.1)
                    yield TerminalOutput(
                        data=data,
                        timestamp=datetime.utcnow(),
                        stream="stdout"
                    )
                except Empty:
                    # No output available, continue
                    pass
                    
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error reading terminal output: {e}")
                break
                
    def _read_output_thread(self):
        """Thread function to read PTY output"""
        try:
            while self.is_active and not self._stop_event.is_set():
                try:
                    # Read from PTY with timeout
                    if self.pty_process and self.pty_process.isalive():
                        data = self.pty_process.read(size=settings.PTY_BUFFER_SIZE, timeout=0.1)
                        if data:
                            # Decode and put in queue
                            decoded_data = data.decode('utf-8', errors='ignore')
                            self.output_queue.put(decoded_data)
                    else:
                        break
                        
                except ptyprocess.exceptions.TIMEOUT:
                    # No data available, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in PTY reader thread: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"PTY reader thread error: {e}")
        finally:
            logger.info(f"PTY reader thread stopped for session {self.session_id}")
            
    async def close(self):
        """Close the terminal session"""
        logger.info(f"Closing terminal session {self.session_id}")
        
        self.is_active = False
        self._stop_event.set()
        
        # Wait for reader thread to finish
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=5)
            
        # Close PTY process
        if self.pty_process:
            try:
                if self.pty_process.isalive():
                    self.pty_process.terminate()
                    # Give it a moment to terminate gracefully
                    for _ in range(10):
                        if not self.pty_process.isalive():
                            break
                        await asyncio.sleep(0.1)
                    
                    # Force kill if still alive
                    if self.pty_process.isalive():
                        self.pty_process.kill()
                        
            except Exception as e:
                logger.error(f"Error closing PTY process: {e}")
            
    async def resize_terminal(self, rows: int, cols: int) -> bool:
        """Resize the terminal"""
        if not self.is_active or not self.pty_process:
            return False
            
        try:
            self.pty_process.setwinsize(rows, cols)
            logger.info(f"Terminal resized to {rows}x{cols} for session {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resize terminal: {e}")
            return False


class TerminalService:
    """Service for managing terminal sessions and PTY operations"""
    
    def __init__(self):
        self.active_sessions: Dict[str, TerminalSession] = {}
        # Enhanced network command patterns
        self.network_command_patterns = {
            'pip_install': re.compile(r'\bpip\s+install\b'),
            'npm_install': re.compile(r'\bnpm\s+install\b'),
            'npm_add': re.compile(r'\bnpm\s+add\b'),
            'yarn_install': re.compile(r'\byarn\s+install\b|\byarn\s+add\b'),
            'pnpm_install': re.compile(r'\bpnpm\s+install\b|\bpnpm\s+add\b'),
            'git_clone': re.compile(r'\bgit\s+clone\s+https?://'),
            'curl': re.compile(r'\bcurl\s+'),
            'wget': re.compile(r'\bwget\s+'),
        }
        
    async def create_terminal_session(self, session_id: str) -> bool:
        """Create a new terminal session"""
        # Get container session from database
        container_session = await db_service.get_terminal_session(session_id)
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
            
        # Record command in database
        await db_service.create_terminal_command(
            session_id=session_id,
            command=command.strip(),
            working_dir=terminal_session.current_directory
        )
        
        # Check if this command needs network access
        if self._needs_network_access(command):
            await self._handle_network_command(session_id, command)
        else:
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
        
    def _needs_network_access(self, command: str) -> bool:
        """Check if command needs network access"""
        return any(pattern.search(command) for pattern in self.network_command_patterns.values())
        
    def _get_command_type(self, command: str) -> str:
        """Get the type of network command"""
        for cmd_type, pattern in self.network_command_patterns.items():
            if pattern.search(command):
                return cmd_type
        return "unknown"
        
    async def _handle_network_command(self, session_id: str, command: str):
        """Handle commands that need network access"""
        command_type = self._get_command_type(command)
        logger.info(f"Handling {command_type} command for session {session_id}")
        
        try:
            # Enable network access
            network_enabled = await container_service.enable_network_access(session_id)
            if not network_enabled:
                error_msg = "Failed to enable network access for command execution\n"
                await self._send_system_message(session_id, error_msg)
                return
                
            # Send appropriate notification based on command type
            notifications = {
                'pip_install': "🐍 Network enabled for Python package installation...\n",
                'npm_install': "📦 Network enabled for npm package installation...\n",
                'npm_add': "📦 Network enabled for npm package installation...\n",
                'yarn_install': "🧶 Network enabled for Yarn package installation...\n",
                'pnpm_install': "⚡ Network enabled for pnpm package installation...\n",
                'git_clone': "🔄 Network enabled for Git repository cloning...\n",
                'curl': "🌐 Network enabled for HTTP request...\n",
                'wget': "📥 Network enabled for file download...\n",
            }
            
            notification = notifications.get(command_type, "🌐 Network access enabled...\n")
            await self._send_system_message(session_id, notification)
            
            # Execute the command (ensure it ends with newline)
            if not command.endswith('\n'):
                command += '\n'
                
            terminal_session = self.active_sessions.get(session_id)
            if terminal_session:
                await terminal_session.send_input(command)
                
                # Wait for command completion (monitor for prompt return)
                # This is a simplified approach - in production you might want more sophisticated detection
                await asyncio.sleep(5)
                
            # Disable network access
            await container_service.disable_network_access(session_id)
            await self._send_system_message(
                session_id, 
                "🔒 Network access disabled. Command execution complete.\n"
            )
            
        except Exception as e:
            logger.error(f"Error handling network command: {e}")
            await self._send_system_message(
                session_id, 
                f"❌ Error during command execution: {str(e)}\n"
            )
            # Ensure network is disabled even on error
            await container_service.disable_network_access(session_id)
            
    async def _send_system_message(self, session_id: str, message: str):
        """Send a system message to the terminal"""
        terminal_session = self.active_sessions.get(session_id)
        if terminal_session:
            # Send as echo command to display the message
            echo_cmd = f'echo "{message.strip()}"\n'
            await terminal_session.send_input(echo_cmd)
            
    async def execute_command_sync(self, session_id: str, command: str) -> Optional[str]:
        """Execute a command synchronously and return the output"""
        # Get container session from database
        container_session = await db_service.get_terminal_session(session_id)
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
            
        except DockerException as e:
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