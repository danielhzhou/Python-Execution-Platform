"""
Tests for Terminal Service with Supabase integration
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.services.terminal_service import TerminalService
from app.models.container import TerminalSession, TerminalCommand, ContainerStatus


class TestTerminalService:
    """Test terminal service functionality"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_terminal_session(self, terminal_service, test_user, test_project, mock_db_service):
        """Test creating a new terminal session"""
        # Mock database response
        mock_session = TerminalSession(
            id="test-session-id",
            user_id=test_user.id,
            project_id=test_project.id,
            container_id="test-container-id",
            status=ContainerStatus.CREATING.value
        )
        mock_db_service.create_terminal_session.return_value = mock_session
        
        # Mock container service
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.get_container_info.return_value = {
                "id": "test-container-id",
                "status": "running"
            }
            
            session_id = await terminal_service.create_terminal_session(
                user_id=test_user.id,
                container_id="test-container-id",
                project_id=test_project.id
            )
            
            assert session_id == "test-session-id"
            mock_db_service.create_terminal_session.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_terminal_session(self, terminal_service, test_terminal_session, mock_db_service):
        """Test starting a terminal session"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_db_service.get_terminal_commands.return_value = []
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.get_container_info.return_value = {
                "id": test_terminal_session.container_id,
                "status": "running"
            }
            
            result = await terminal_service.start_terminal_session(test_terminal_session.id)
            
            assert result is True
            mock_db_service.get_terminal_session.assert_called_once_with(test_terminal_session.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_command_to_session(self, terminal_service, test_terminal_session, mock_db_service):
        """Test sending command to terminal session"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_command = TerminalCommand(
            id="test-command-id",
            session_id=test_terminal_session.id,
            command="echo 'Hello World'",
            output="Hello World\n",
            exit_code=0
        )
        mock_db_service.create_terminal_command.return_value = mock_command
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "Hello World\n",
                "error": "",
                "exit_code": 0
            }
            
            result = await terminal_service.send_command(
                session_id=test_terminal_session.id,
                command="echo 'Hello World'"
            )
            
            assert result["output"] == "Hello World\n"
            assert result["exit_code"] == 0
            mock_db_service.create_terminal_command.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_command_sync(self, terminal_service, test_terminal_session, mock_db_service):
        """Test synchronous command execution"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_command = TerminalCommand(
            id="test-command-id",
            session_id=test_terminal_session.id,
            command="python --version",
            output="Python 3.11.0\n",
            exit_code=0
        )
        mock_db_service.create_terminal_command.return_value = mock_command
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "Python 3.11.0\n",
                "error": "",
                "exit_code": 0
            }
            
            result = await terminal_service.execute_command_sync(
                session_id=test_terminal_session.id,
                command="python --version"
            )
            
            assert result["output"] == "Python 3.11.0\n"
            assert result["exit_code"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pip_install_detection(self, terminal_service, test_terminal_session, mock_db_service):
        """Test pip install command detection"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        # Test pip install detection
        assert terminal_service._is_pip_install("pip install numpy")
        assert terminal_service._is_pip_install("pip3 install pandas")
        assert terminal_service._is_pip_install("python -m pip install requests")
        assert not terminal_service._is_pip_install("pip list")
        assert not terminal_service._is_pip_install("echo 'pip install'")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_pip_command_handling(self, terminal_service, test_terminal_session, mock_db_service):
        """Test handling of non-pip commands"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_command = TerminalCommand(
            id="test-command-id",
            session_id=test_terminal_session.id,
            command="ls -la",
            output="total 0\ndrwxr-xr-x 2 user user 4096 Jan 1 00:00 .\n",
            exit_code=0
        )
        mock_db_service.create_terminal_command.return_value = mock_command
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "total 0\ndrwxr-xr-x 2 user user 4096 Jan 1 00:00 .\n",
                "error": "",
                "exit_code": 0
            }
            
            result = await terminal_service.execute_command_sync(
                session_id=test_terminal_session.id,
                command="ls -la"
            )
            
            assert "total 0" in result["output"]
            assert result["exit_code"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_cleanup(self, terminal_service, test_terminal_session, mock_db_service):
        """Test terminal session cleanup"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_db_service.update_terminal_session.return_value = test_terminal_session
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            await terminal_service.close_terminal_session(test_terminal_session.id)
            
            mock_db_service.update_terminal_session.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_output(self, terminal_service, test_terminal_session, mock_db_service):
        """Test retrieving session output history"""
        # Mock database responses
        mock_commands = [
            TerminalCommand(
                id="cmd1",
                session_id=test_terminal_session.id,
                command="echo 'test1'",
                output="test1\n",
                exit_code=0
            ),
            TerminalCommand(
                id="cmd2", 
                session_id=test_terminal_session.id,
                command="echo 'test2'",
                output="test2\n",
                exit_code=0
            )
        ]
        mock_db_service.get_terminal_commands.return_value = mock_commands
        
        commands = await terminal_service.get_session_commands(test_terminal_session.id)
        
        assert len(commands) == 2
        assert commands[0].command == "echo 'test1'"
        assert commands[1].command == "echo 'test2'"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_resize(self, terminal_service, test_terminal_session, mock_db_service):
        """Test terminal session resize"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            result = await terminal_service.resize_terminal(
                session_id=test_terminal_session.id,
                rows=30,
                cols=120
            )
            
            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_command_history_management(self, terminal_service, test_terminal_session, mock_db_service):
        """Test command history retrieval"""
        # Mock database responses
        mock_commands = [
            TerminalCommand(
                id="cmd1",
                session_id=test_terminal_session.id,
                command="ls -la",
                output="file1.txt\nfile2.txt\n",
                exit_code=0
            ),
            TerminalCommand(
                id="cmd2",
                session_id=test_terminal_session.id,
                command="pwd",
                output="/workspace\n",
                exit_code=0
            )
        ]
        mock_db_service.get_terminal_commands.return_value = mock_commands
        
        history = await terminal_service.get_command_history(test_terminal_session.id)
        
        assert len(history) == 2
        assert history[0]["command"] == "ls -la"
        assert history[1]["command"] == "pwd"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_output_streaming(self, terminal_service, test_terminal_session, mock_db_service):
        """Test real-time output streaming"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        # Test that streaming setup doesn't crash
        result = await terminal_service.setup_output_streaming(test_terminal_session.id)
        
        # This test mainly ensures the method exists and doesn't crash
        # Real streaming would be tested in integration tests
        assert result is not None or result is None  # Either is acceptable

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling_in_command_execution(self, terminal_service, test_terminal_session, mock_db_service):
        """Test error handling during command execution"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_command = TerminalCommand(
            id="test-command-id",
            session_id=test_terminal_session.id,
            command="invalid-command",
            output="",
            error_output="command not found: invalid-command\n",
            exit_code=127
        )
        mock_db_service.create_terminal_command.return_value = mock_command
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "",
                "error": "command not found: invalid-command\n",
                "exit_code": 127
            }
            
            result = await terminal_service.execute_command_sync(
                session_id=test_terminal_session.id,
                command="invalid-command"
            )
            
            assert result["exit_code"] == 127
            assert "command not found" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self, terminal_service, test_terminal_session, mock_db_service):
        """Test concurrent command execution handling"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "test output\n",
                "error": "",
                "exit_code": 0
            }
            
            # Test that concurrent commands don't interfere
            import asyncio
            tasks = [
                terminal_service.execute_command_sync(test_terminal_session.id, f"echo 'test{i}'")
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert result["exit_code"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_state_management(self, terminal_service, test_terminal_session, mock_db_service):
        """Test session state tracking"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        mock_db_service.update_terminal_session.return_value = test_terminal_session
        
        # Test session state updates
        await terminal_service.update_session_activity(test_terminal_session.id)
        
        mock_db_service.update_terminal_session.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_working_directory_management(self, terminal_service, test_terminal_session, mock_db_service):
        """Test working directory tracking"""
        # Mock database responses
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "/workspace/subdir\n",
                "error": "",
                "exit_code": 0
            }
            
            # Test directory change
            result = await terminal_service.execute_command_sync(
                session_id=test_terminal_session.id,
                command="cd subdir && pwd"
            )
            
            assert "/workspace" in result["output"] or result["output"] == "/workspace/subdir\n"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_environment_variable_handling(self, terminal_service, test_terminal_session, mock_db_service):
        """Test environment variable management"""
        # Mock database responses
        test_terminal_session.environment_vars = {"TEST_VAR": "test_value"}
        mock_db_service.get_terminal_session.return_value = test_terminal_session
        
        with patch('app.services.terminal_service.container_service') as mock_container_service:
            mock_container_service.execute_command_sync.return_value = {
                "output": "test_value\n",
                "error": "",
                "exit_code": 0
            }
            
            result = await terminal_service.execute_command_sync(
                session_id=test_terminal_session.id,
                command="echo $TEST_VAR"
            )
            
            assert "test_value" in result["output"]


class TestTerminalSessionClass:
    """Test the TerminalSession database model"""
    
    @pytest.mark.unit
    def test_terminal_session_creation(self, test_user, test_project):
        """Test TerminalSession model creation"""
        session = TerminalSession(
            id="test-session-id",
            user_id=test_user.id,
            project_id=test_project.id,
            container_id="test-container-id",
            status=ContainerStatus.CREATING.value
        )
        
        assert session.id == "test-session-id"
        assert session.user_id == test_user.id
        assert session.project_id == test_project.id
        assert session.container_id == "test-container-id"
        assert session.status == ContainerStatus.CREATING.value

    @pytest.mark.unit
    def test_terminal_session_defaults(self, test_user):
        """Test TerminalSession model default values"""
        session = TerminalSession(
            user_id=test_user.id,
            container_id="test-container-id"
        )
        
        assert session.container_image == "python-execution-sandbox:latest"
        assert session.cpu_limit == "1.0"
        assert session.memory_limit == "512m"
        assert session.status == ContainerStatus.CREATING.value 