"""
Tests for TerminalService - PTY management and command execution
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.services.terminal_service import TerminalService, TerminalSession
from app.models.container import TerminalOutput


class TestTerminalService:
    """Test suite for TerminalService"""

    @pytest.mark.unit
    async def test_create_terminal_session(self, terminal_service, mock_terminal_session):
        """Test creating a new terminal session"""
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container = Mock()
            mock_container_service.active_containers = {"test-container-id": mock_container}
            
            session = await terminal_service.create_session("test-session-id", "test-container-id")
            
            assert session.session_id == "test-session-id"
            assert session.container.id == mock_container.id
            assert not session.is_active

    @pytest.mark.unit
    async def test_start_terminal_session(self, terminal_service):
        """Test starting a terminal session"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        with patch.object(session, '_start_bash_process') as mock_start:
            mock_start.return_value = AsyncMock()
            
            await terminal_service.start_session(session)
            
            assert session.is_active
            mock_start.assert_called_once()

    @pytest.mark.unit
    async def test_send_command_to_session(self, terminal_service, sample_commands):
        """Test sending commands to terminal session"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        session.is_active = True
        session.process = AsyncMock()
        
        for command in sample_commands[:3]:  # Test first 3 commands
            await terminal_service.send_command(session, command)
            
            # Verify command was added to history
            assert command in session.command_history
            
            # Verify process interaction
            session.process.stdin.write.assert_called()

    @pytest.mark.unit
    async def test_execute_command_sync(self, terminal_service, sample_commands):
        """Test synchronous command execution"""
        mock_container = Mock()
        mock_container.execute.return_value = "command output"
        
        session = TerminalSession("test-session", mock_container)
        
        for command in sample_commands[:3]:
            result = await terminal_service.execute_command_sync(session, command)
            
            assert result == "command output"
            mock_container.execute.assert_called_with(["/bin/bash", "-c", command])

    @pytest.mark.unit
    async def test_pip_install_detection(self, terminal_service):
        """Test detection and handling of pip install commands"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        pip_commands = [
            "pip install pandas",
            "pip install numpy scipy",
            "python -m pip install matplotlib",
            "pip3 install requests"
        ]
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.enable_network_access = AsyncMock(return_value=True)
            mock_container_service.disable_network_access = AsyncMock(return_value=True)
            
            for command in pip_commands:
                is_pip = await terminal_service._handle_pip_install(session, command)
                assert is_pip
                
                # Verify network was enabled and disabled
                mock_container_service.enable_network_access.assert_called()
                mock_container_service.disable_network_access.assert_called()

    @pytest.mark.unit
    async def test_non_pip_command_handling(self, terminal_service, sample_commands):
        """Test that non-pip commands don't trigger network changes"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.enable_network_access = AsyncMock()
            mock_container_service.disable_network_access = AsyncMock()
            
            for command in sample_commands:
                is_pip = await terminal_service._handle_pip_install(session, command)
                assert not is_pip
                
                # Verify network methods were not called
                mock_container_service.enable_network_access.assert_not_called()
                mock_container_service.disable_network_access.assert_not_called()

    @pytest.mark.unit
    async def test_session_cleanup(self, terminal_service):
        """Test proper cleanup of terminal sessions"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        session.is_active = True
        session.process = AsyncMock()
        
        await terminal_service.cleanup_session(session)
        
        assert not session.is_active
        session.process.terminate.assert_called_once()

    @pytest.mark.unit
    async def test_get_session_output(self, terminal_service):
        """Test retrieving session output"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        session.output_buffer = ["line 1\n", "line 2\n", "line 3\n"]
        
        output = await terminal_service.get_session_output(session, last_n_lines=2)
        
        assert len(output) == 2
        assert output[0] == "line 2\n"
        assert output[1] == "line 3\n"

    @pytest.mark.unit
    async def test_session_resize(self, terminal_service):
        """Test terminal session resizing"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        session.is_active = True
        session.process = AsyncMock()
        
        await terminal_service.resize_session(session, rows=30, cols=120)
        
        # Verify resize was handled (implementation would depend on PTY library)
        assert session.is_active  # Session should remain active

    @pytest.mark.unit
    async def test_command_history_management(self, terminal_service, sample_commands):
        """Test command history tracking and limits"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Add commands up to the limit
        for i, command in enumerate(sample_commands):
            await terminal_service._add_to_history(session, command)
            
            # Verify command was added
            assert command in session.command_history
            
        # Verify history doesn't exceed maximum
        assert len(session.command_history) <= 100  # Default max history

    @pytest.mark.unit
    async def test_output_streaming(self, terminal_service):
        """Test real-time output streaming"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        session.is_active = True
        
        # Mock output generator
        async def mock_output_generator():
            for i in range(5):
                yield f"output line {i}\n"
                await asyncio.sleep(0.01)  # Simulate streaming delay
        
        output_lines = []
        async for line in terminal_service._stream_output(session, mock_output_generator()):
            output_lines.append(line)
        
        assert len(output_lines) == 5
        assert all("output line" in line for line in output_lines)

    @pytest.mark.unit
    async def test_error_handling_in_command_execution(self, terminal_service):
        """Test error handling during command execution"""
        mock_container = Mock()
        mock_container.execute.side_effect = Exception("Container error")
        
        session = TerminalSession("test-session", mock_container)
        
        # Should handle errors gracefully
        result = await terminal_service.execute_command_sync(session, "failing_command")
        
        # Should return error information rather than raising
        assert "error" in result.lower() or result == ""

    @pytest.mark.unit
    async def test_concurrent_command_execution(self, terminal_service):
        """Test handling concurrent commands in same session"""
        mock_container = Mock()
        mock_container.execute.return_value = "output"
        
        session = TerminalSession("test-session", mock_container)
        
        # Execute multiple commands concurrently
        tasks = []
        for i in range(5):
            task = terminal_service.execute_command_sync(session, f"command_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All commands should complete successfully
        assert len(results) == 5
        assert all(result == "output" for result in results)

    @pytest.mark.unit
    async def test_session_state_management(self, terminal_service):
        """Test terminal session state transitions"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Initial state
        assert not session.is_active
        assert session.command_history == []
        assert session.output_buffer == []
        
        # Start session
        with patch.object(session, '_start_bash_process') as mock_start:
            mock_start.return_value = AsyncMock()
            await terminal_service.start_session(session)
            
            assert session.is_active
        
        # Add some activity
        await terminal_service._add_to_history(session, "test command")
        await terminal_service._add_to_output_buffer(session, "test output")
        
        assert len(session.command_history) == 1
        assert len(session.output_buffer) == 1
        
        # Cleanup
        await terminal_service.cleanup_session(session)
        assert not session.is_active

    @pytest.mark.unit
    async def test_working_directory_management(self, terminal_service):
        """Test working directory tracking and changes"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Test cd command handling
        cd_commands = [
            "cd /workspace",
            "cd ..",
            "cd ~/projects",
            "cd /tmp"
        ]
        
        for command in cd_commands:
            await terminal_service._handle_directory_change(session, command)
            # Implementation would track current directory
            # This test verifies the method can be called without errors

    @pytest.mark.unit
    async def test_environment_variable_handling(self, terminal_service):
        """Test environment variable management in sessions"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        env_commands = [
            "export PYTHONPATH=/workspace",
            "export DEBUG=1",
            "unset TEMP_VAR"
        ]
        
        for command in env_commands:
            # Test that environment commands are handled properly
            await terminal_service._handle_environment_command(session, command)
            # Implementation would manage session environment
            # This test verifies the method can be called without errors


class TestTerminalSessionClass:
    """Test the TerminalSession class directly"""

    @pytest.mark.unit
    def test_terminal_session_initialization(self):
        """Test TerminalSession initialization"""
        mock_container = Mock()
        mock_container.id = "test-container"
        
        session = TerminalSession("test-session", mock_container)
        
        assert session.session_id == "test-session"
        assert session.container == mock_container
        assert not session.is_active
        assert session.command_history == []
        assert session.current_directory == "/workspace"

    @pytest.mark.unit
    async def test_bash_process_management(self):
        """Test bash process lifecycle"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Mock process creation
        mock_process = AsyncMock()
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            await session._start_bash_process()
            
            assert session.process == mock_process
            assert session.is_active

    @pytest.mark.unit
    async def test_output_buffer_management(self):
        """Test output buffer size limits and rotation"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Add many lines to test buffer limits
        for i in range(1500):  # Exceed typical buffer size
            session.output_buffer.append(f"line {i}\n")
        
        # Buffer should be limited to prevent memory issues
        # Implementation would limit buffer size
        assert len(session.output_buffer) <= 1000  # Example limit

    @pytest.mark.unit
    def test_session_statistics(self):
        """Test session statistics collection"""
        mock_container = Mock()
        session = TerminalSession("test-session", mock_container)
        
        # Add some activity
        session.command_history = ["cmd1", "cmd2", "cmd3"]
        
        # Test basic properties
        assert len(session.command_history) == 3
        assert session.session_id == "test-session" 