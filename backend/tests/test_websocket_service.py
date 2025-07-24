"""
Tests for WebSocketService - Real-time terminal communication
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.websocket_service import WebSocketService, WebSocketMessage
from fastapi import WebSocketDisconnect


class TestWebSocketService:
    """Test suite for WebSocketService"""

    @pytest.mark.unit
    async def test_service_initialization(self, websocket_service):
        """Test WebSocketService initialization"""
        assert websocket_service.active_connections == {}
        assert websocket_service.connection_stats == {}

    @pytest.mark.unit
    async def test_handle_terminal_connection_success(self, websocket_service, mock_websocket):
        """Test successful WebSocket terminal connection"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.start_session = AsyncMock()
            
            # Mock message receiving to simulate client interaction
            mock_websocket.receive_json.side_effect = [
                {"type": "terminal_input", "data": {"data": "ls -la\n"}},
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
    async def test_handle_terminal_input_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling terminal input messages"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.send_command = AsyncMock()
            
            # Process terminal input message
            message = websocket_messages["terminal_input"]
            await websocket_service._handle_message(mock_websocket, session_id, message)
            
            # Verify command was sent to terminal
            mock_terminal_service.send_command.assert_called_once_with(
                mock_session, 
                message["data"]["data"]
            )

    @pytest.mark.unit
    async def test_handle_terminal_resize_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling terminal resize messages"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.resize_session = AsyncMock()
            
            # Process resize message
            message = websocket_messages["terminal_resize"]
            await websocket_service._handle_message(mock_websocket, session_id, message)
            
            # Verify resize was called
            mock_terminal_service.resize_session.assert_called_once_with(
                mock_session,
                rows=message["data"]["rows"],
                cols=message["data"]["cols"]
            )

    @pytest.mark.unit
    async def test_handle_ping_message(self, websocket_service, mock_websocket, websocket_messages):
        """Test handling ping messages"""
        session_id = "test-session-123"
        
        # Process ping message
        message = websocket_messages["ping"]
        await websocket_service._handle_message(mock_websocket, session_id, message)
        
        # Verify pong response was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "pong"

    @pytest.mark.unit
    async def test_handle_unknown_message_type(self, websocket_service, mock_websocket):
        """Test handling unknown message types"""
        session_id = "test-session-123"
        
        unknown_message = {
            "type": "unknown_type",
            "data": {"some": "data"}
        }
        
        # Should handle gracefully without raising
        await websocket_service._handle_message(mock_websocket, session_id, unknown_message)
        
        # Should send error response
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "error"

    @pytest.mark.unit
    async def test_broadcast_output_to_session(self, websocket_service, mock_websocket):
        """Test broadcasting output to specific session"""
        session_id = "test-session-123"
        output_data = "Hello from terminal!\n"
        
        # Add connection to active connections
        websocket_service.active_connections[session_id] = mock_websocket
        
        await websocket_service.broadcast_output(session_id, output_data)
        
        # Verify output was sent to WebSocket
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "terminal_output"
        assert sent_message["data"]["output"] == output_data

    @pytest.mark.unit
    async def test_broadcast_output_no_connection(self, websocket_service):
        """Test broadcasting output when no connection exists"""
        session_id = "non-existent-session"
        output_data = "Hello from terminal!\n"
        
        # Should handle gracefully when no connection exists
        await websocket_service.broadcast_output(session_id, output_data)
        
        # No error should be raised

    @pytest.mark.unit
    async def test_connection_cleanup_on_disconnect(self, websocket_service, mock_websocket):
        """Test proper cleanup when WebSocket disconnects"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.cleanup_session = AsyncMock()
            
            # Simulate disconnect during message handling
            mock_websocket.receive_json.side_effect = WebSocketDisconnect()
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Verify session was cleaned up
            mock_terminal_service.cleanup_session.assert_called_once_with(mock_session)
            
            # Verify connection was removed
            assert session_id not in websocket_service.active_connections

    @pytest.mark.unit
    async def test_connection_statistics_tracking(self, websocket_service, mock_websocket):
        """Test connection statistics are properly tracked"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            
            # Simulate some messages
            messages = [
                {"type": "terminal_input", "data": {"data": "command1\n"}},
                {"type": "terminal_input", "data": {"data": "command2\n"}},
                {"type": "ping", "data": {}},
                WebSocketDisconnect()
            ]
            mock_websocket.receive_json.side_effect = messages
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Verify statistics were tracked
            assert session_id in websocket_service.connection_stats
            stats = websocket_service.connection_stats[session_id]
            assert stats["messages_received"] >= 3
            assert stats["messages_sent"] >= 1  # At least pong response

    @pytest.mark.unit
    async def test_concurrent_connections(self, websocket_service):
        """Test handling multiple concurrent WebSocket connections"""
        mock_websockets = [AsyncMock() for _ in range(3)]
        session_ids = [f"session-{i}" for i in range(3)]
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_sessions = [Mock() for _ in range(3)]
            mock_terminal_service.get_session.side_effect = mock_sessions
            
            # Set up each websocket to disconnect immediately
            for ws in mock_websockets:
                ws.receive_json.side_effect = [WebSocketDisconnect()]
            
            # Handle connections concurrently
            tasks = []
            for i, (ws, session_id) in enumerate(zip(mock_websockets, session_ids)):
                task = websocket_service.handle_terminal_connection(ws, session_id)
                tasks.append(task)
            
            # All should complete without interference
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should result in WebSocketDisconnect (expected)
            assert all(isinstance(r, WebSocketDisconnect) for r in results)

    @pytest.mark.unit
    async def test_message_validation(self, websocket_service, mock_websocket):
        """Test WebSocket message validation"""
        session_id = "test-session-123"
        
        invalid_messages = [
            {"invalid": "structure"},  # Missing type
            {"type": "terminal_input"},  # Missing data
            {"type": "terminal_input", "data": "invalid"},  # Wrong data type
            "not a dict",  # Wrong message type
        ]
        
        for invalid_msg in invalid_messages:
            # Should handle invalid messages gracefully
            await websocket_service._handle_message(mock_websocket, session_id, invalid_msg)
            
            # Should send error response for each
            mock_websocket.send_json.assert_called()
            mock_websocket.send_json.reset_mock()

    @pytest.mark.unit
    async def test_websocket_error_handling(self, websocket_service, mock_websocket):
        """Test WebSocket error handling and recovery"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            mock_terminal_service.send_command.side_effect = Exception("Terminal error")
            
            # Send message that will cause terminal error
            message = {"type": "terminal_input", "data": {"data": "failing_command\n"}}
            
            # Should handle terminal errors gracefully
            await websocket_service._handle_message(mock_websocket, session_id, message)
            
            # Should send error message to client
            mock_websocket.send_json.assert_called()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "error"

    @pytest.mark.unit
    async def test_output_streaming_performance(self, websocket_service, mock_websocket):
        """Test output streaming performance with high-frequency updates"""
        session_id = "test-session-123"
        websocket_service.active_connections[session_id] = mock_websocket
        
        # Send many output messages rapidly
        output_messages = [f"Line {i}\n" for i in range(100)]
        
        tasks = []
        for output in output_messages:
            task = websocket_service.broadcast_output(session_id, output)
            tasks.append(task)
        
        # All should complete without blocking
        await asyncio.gather(*tasks)
        
        # Verify all messages were sent
        assert mock_websocket.send_json.call_count == 100

    @pytest.mark.unit
    async def test_connection_heartbeat(self, websocket_service, mock_websocket):
        """Test WebSocket connection heartbeat mechanism"""
        session_id = "test-session-123"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_session = Mock()
            mock_terminal_service.get_session.return_value = mock_session
            
            # Simulate heartbeat messages
            messages = [
                {"type": "ping", "data": {}},
                {"type": "ping", "data": {}},
                WebSocketDisconnect()
            ]
            mock_websocket.receive_json.side_effect = messages
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Should have responded to both pings
            assert mock_websocket.send_json.call_count >= 2
            
            # All responses should be pongs
            for call in mock_websocket.send_json.call_args_list:
                message = call[0][0]
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
    async def test_session_not_found_handling(self, websocket_service, mock_websocket):
        """Test handling when terminal session is not found"""
        session_id = "non-existent-session"
        
        with patch('app.services.websocket_service.terminal_service') as mock_terminal_service:
            mock_terminal_service.get_session.return_value = None
            
            mock_websocket.receive_json.side_effect = [WebSocketDisconnect()]
            
            try:
                await websocket_service.handle_terminal_connection(mock_websocket, session_id)
            except WebSocketDisconnect:
                pass
            
            # Should send error message about session not found
            mock_websocket.send_json.assert_called()
            sent_message = mock_websocket.send_json.call_args[0][0]
            assert sent_message["type"] == "error"
            assert "session not found" in sent_message["data"]["message"].lower()


class TestWebSocketServiceIntegration:
    """Integration tests for WebSocketService"""

    @pytest.mark.integration
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
    async def test_websocket_performance_under_load(self, websocket_service):
        """Test WebSocket performance under high message load"""
        import time
        
        session_id = "performance-test-session"
        mock_websocket = AsyncMock()
        websocket_service.active_connections[session_id] = mock_websocket
        
        # Send many messages and measure performance
        start_time = time.time()
        
        tasks = []
        for i in range(1000):
            task = websocket_service.broadcast_output(session_id, f"Output line {i}\n")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle 1000 messages in reasonable time (< 1 second)
        assert duration < 1.0
        assert mock_websocket.send_json.call_count == 1000 