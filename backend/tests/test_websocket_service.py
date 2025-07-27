"""
Tests for WebSocketService - Real-time terminal communication
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.websocket_service import WebSocketService, WebSocketMessage
from fastapi import WebSocketDisconnect

# Test constants with valid UUID formats
TEST_SESSION_ID = "550e8400-e29b-41d4-a716-446655440000"


class TestWebSocketService:
    """Test suite for WebSocketService"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_initialization(self, websocket_service):
        """Test WebSocketService initialization"""
        assert websocket_service.manager.active_connections == {}
        assert websocket_service.manager.session_connections == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_terminal_connection_success(self, websocket_service, mock_websocket):
        """Test successful WebSocket terminal connection"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.container_service') as mock_container_service, \
             patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            
            # Mock container service
            mock_container_session = Mock()
            mock_container_service.container_sessions = {session_id: mock_container_session}
            
            # Mock terminal service
            mock_terminal_session = Mock()
            mock_terminal_service.get_terminal_session = AsyncMock(return_value=mock_terminal_session)
            
            # Mock message receiving to simulate client interaction
            mock_websocket.receive_text.side_effect = [
                '{"type": "terminal_input", "data": {"data": "ls -la\\n"}}',
                WebSocketDisconnect()  # Simulate disconnect
            ]
            
            # This should handle the connection without raising
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass  # Expected when connection closes
            
            # Verify connection was accepted
            mock_websocket.accept.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_terminal_input_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling terminal input messages"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_terminal_service.send_input = AsyncMock(return_value=True)
            
            # Process terminal input message
            message = websocket_messages["terminal_input"]
            await websocket_service.manager.handle_message(mock_websocket, session_id, json.dumps({"type": "input", "data": {"data": "ls -la"}}))
            
            # Verify input was sent to terminal
            mock_terminal_service.send_input.assert_called_once_with(
                session_id, 
                "ls -la"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_terminal_resize_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling terminal resize messages"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_terminal_service.resize_terminal = AsyncMock(return_value=True)
            
            # Process resize message
            await websocket_service.manager.handle_message(mock_websocket, session_id, json.dumps({"type": "resize", "data": {"rows": 24, "cols": 80}}))
            
            # Verify resize was called
            mock_terminal_service.resize_terminal.assert_called_once_with(
                session_id,
                24,
                80
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling ping messages"""
        session_id = TEST_SESSION_ID
        
        # Process ping message
        await websocket_service.manager.handle_message(mock_websocket, session_id, json.dumps({"type": "ping"}))
        
        # Verify pong response was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "pong"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, websocket_service, mock_websocket):
        """Test handling unknown message types"""
        session_id = TEST_SESSION_ID
        
        unknown_message = json.dumps({
            "type": "unknown_type",
            "data": {"some": "data"}
        })
        
        # Should handle gracefully without raising
        await websocket_service.manager.handle_message(mock_websocket, session_id, unknown_message)
        
        # Unknown message types are just logged, no response sent
        mock_websocket.send_text.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_output_to_session(self, websocket_service, mock_websocket):
        """Test broadcasting output to specific session"""
        session_id = TEST_SESSION_ID
        message_data = {"type": "terminal_output", "data": {"output": "Hello from terminal!\n"}}
        
        # Add connection to session connections
        websocket_service.manager.session_connections[session_id] = {mock_websocket}
        
        await websocket_service.manager._broadcast_to_session(session_id, message_data)
        
        # Verify message was sent to WebSocket
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "terminal_output"
        assert sent_message["data"]["output"] == "Hello from terminal!\n"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_broadcast_output_no_connection(self, websocket_service):
        """Test broadcasting output when no connection exists"""
        session_id = "non-existent-session"
        output_data = "Hello from terminal!\n"
        
        # Should handle gracefully when no connection exists
        await websocket_service.manager._broadcast_to_session(session_id, output_data)
        
        # No error should be raised

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self, websocket_service, mock_websocket):
        """Test proper cleanup when WebSocket disconnects"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.container_service') as mock_container_service, \
             patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            
            # Mock container service
            mock_container_session = Mock()
            mock_container_service.container_sessions = {session_id: mock_container_session}
            
            # Mock terminal service
            mock_terminal_session = Mock()
            mock_terminal_service.get_terminal_session = AsyncMock(return_value=mock_terminal_session)
            mock_terminal_service.close_terminal_session = AsyncMock()
            
            # Simulate disconnect during message handling
            mock_websocket.receive_text.side_effect = WebSocketDisconnect()
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Verify terminal session was closed
            mock_terminal_service.close_terminal_session.assert_called_once_with(session_id)
            
            # Verify connection was removed
            assert session_id not in websocket_service.manager.active_connections

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_statistics_tracking(self, websocket_service, mock_websocket):
        """Test connection statistics are properly tracked"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.container_service') as mock_container_service, \
             patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            
            # Mock services
            mock_container_service.get_container_info = AsyncMock(return_value=None)
            mock_terminal_session = Mock()
            mock_terminal_session.is_active = True
            mock_terminal_session.command_history = ["cmd1", "cmd2"]
            mock_terminal_service.get_terminal_session = AsyncMock(return_value=mock_terminal_session)
            
            # Add a connection to session_connections
            websocket_service.manager.session_connections[session_id] = {mock_websocket}
            
            # Get session stats
            stats = await websocket_service.manager.get_session_stats(session_id)
            
            # Verify statistics are returned correctly
            assert stats["session_id"] == session_id
            assert stats["connected_clients"] == 1
            assert stats["terminal_active"] == True
            assert stats["command_history_count"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, websocket_service):
        """Test handling multiple concurrent WebSocket connections"""
        session_id = TEST_SESSION_ID
        mock_websockets = [Mock() for _ in range(3)]
        
        # Mock the accept method for each websocket
        for ws in mock_websockets:
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
        
        # Test that multiple websockets can connect to the same session
        await websocket_service.manager.connect(mock_websockets[0], session_id)
        await websocket_service.manager.connect(mock_websockets[1], session_id)
        await websocket_service.manager.connect(mock_websockets[2], session_id)
        
        # Verify all connections are tracked
        assert session_id in websocket_service.manager.session_connections
        assert len(websocket_service.manager.session_connections[session_id]) == 3
        assert len(websocket_service.manager.active_connections) == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_message_validation(self, websocket_service, mock_websocket):
        """Test WebSocket message validation"""
        session_id = TEST_SESSION_ID
        
        # Test messages that should trigger validation errors and send error responses
        validation_error_messages = [
            '{"invalid": "structure"}',  # Missing type field
            '"not a dict"',  # Wrong message type - not JSON object
            'invalid json',  # Invalid JSON
        ]
        
        for invalid_msg in validation_error_messages:
            # Should handle invalid messages gracefully
            await websocket_service.manager.handle_message(mock_websocket, session_id, invalid_msg)
            
            # Should send error response for validation errors
            mock_websocket.send_text.assert_called()
            mock_websocket.send_text.reset_mock()
            
        # Test unknown message type (should not send error response, just log warning)
        await websocket_service.manager.handle_message(mock_websocket, session_id, '{"type": "unknown_type"}')
        # Unknown types are just logged, no error response sent
        mock_websocket.send_text.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, websocket_service, mock_websocket):
        """Test WebSocket error handling and recovery"""
        session_id = TEST_SESSION_ID
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_terminal_service.send_input = AsyncMock(side_effect=Exception("Terminal error"))
            
            # Send message that will cause terminal error
            message = json.dumps({"type": "input", "data": {"data": "failing_command\n"}})
            
            # Should handle terminal errors gracefully
            await websocket_service.manager.handle_message(mock_websocket, session_id, message)
            
            # Should send error message to client
            mock_websocket.send_text.assert_called()
            sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_message["type"] == "error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_output_streaming_performance(self, websocket_service, mock_websocket):
        """Test output streaming performance with high-frequency updates"""
        session_id = TEST_SESSION_ID
        websocket_service.manager.session_connections[session_id] = {mock_websocket}
        
        # Send output messages rapidly
        output_messages = [{"type": "terminal_output", "data": {"output": f"Line {i}\n"}} for i in range(3)]
        
        tasks = []
        for output in output_messages:
            task = websocket_service.manager._broadcast_to_session(session_id, output)
            tasks.append(task)
        
        # All should complete without blocking
        await asyncio.gather(*tasks)
        
        # Verify messages were sent via send_text
        assert mock_websocket.send_text.call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_heartbeat(self, websocket_service, mock_websocket):
        """Test WebSocket connection heartbeat mechanism"""
        session_id = TEST_SESSION_ID
        
        # Test ping-pong directly with the manager
        await websocket_service.manager.handle_message(mock_websocket, session_id, json.dumps({"type": "ping"}))
        await websocket_service.manager.handle_message(mock_websocket, session_id, json.dumps({"type": "ping"}))
        
        # Should have responded to both pings
        assert mock_websocket.send_text.call_count == 2
        
                # All responses should be pongs
        for call in mock_websocket.send_text.call_args_list:
            message = json.loads(call[0][0])
            assert message["type"] == "pong"

    @pytest.mark.unit
    def test_websocket_message_model(self):
        """Test WebSocketMessage model validation"""
        # Valid message
        valid_msg = WebSocketMessage(
            type="terminal_input",
            data={"command": "ls -la"}
        )
        assert valid_msg.type == "terminal_input"
        assert valid_msg.data["command"] == "ls -la"
        
        # Message with minimal data
        minimal_msg = WebSocketMessage(type="ping")
        assert minimal_msg.type == "ping"
        assert minimal_msg.data == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_not_found_handling(self, websocket_service, mock_websocket):
        """Test handling when terminal session is not found"""
        session_id = "non-existent-session"
        
        with patch('app.services.websocket_service.container_service') as mock_container_service:
            # Container session doesn't exist
            mock_container_service.container_sessions = {}
            
            # Should close websocket with error code
            await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            
            # Should close websocket with invalid session code
            mock_websocket.close.assert_called_once_with(code=1008, reason="Invalid session ID")


class TestWebSocketServiceIntegration:
    """Integration tests for WebSocketService"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_terminal_workflow(self, websocket_service):
        """Test complete terminal workflow through WebSocket"""
        session_id = "integration-test-session"
        mock_websocket = AsyncMock()
        
        # Simulate a complete terminal interaction
        messages = [
            {"type": "terminal_input", "data": {"data": "echo 'Hello, World!'\n"}},
            {"type": "terminal_input", "data": {"data": "ls -la\n"}},
            {"type": "terminal_resize", "data": {"rows": 30, "cols": 120}},
            {"type": "ping", "data": {}},
            WebSocketDisconnect()
        ]
        mock_websocket.receive_json.side_effect = messages
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.send_command = AsyncMock()
            mock_terminal_service.resize_session = AsyncMock()
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Verify all interactions occurred
            assert mock_terminal_service.send_command.call_count == 2
            mock_terminal_service.resize_session.assert_called_once()
            
            # Verify responses were sent
            assert mock_websocket.send_json.call_count >= 1  # At least pong response

    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_performance_under_load(self, websocket_service):
        """Test WebSocket performance under high message load"""
        import time
        
        session_id = "performance-test-session"
        mock_websocket = AsyncMock()
        websocket_service.manager.active_connections[session_id] = mock_websocket
        
        # Send many messages and measure performance
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            task = websocket_service.manager._broadcast_to_session(session_id, f"Output line {i}\n")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 1000 messages in reasonable time (< 1 second)
        assert duration < 1.0
        assert mock_websocket.send_json.call_count == 1000 