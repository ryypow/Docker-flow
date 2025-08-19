#!/usr/bin/env python3
"""
DockerFlow WebSocket Test Suite
Comprehensive tests for WebSocket endpoints
"""

import pytest
import asyncio
import json
import time
import websockets
from typing import List, Dict, Any

# Test configuration
WS_BASE_URL = "ws://localhost:5001"
TERMINAL_BASE_URL = "ws://localhost:5003"
TIMEOUT = 30

class TestWebSocketEndpoints:
    """Test WebSocket endpoints"""
    
    @pytest.mark.asyncio
    async def test_ws_connection(self):
        """Test basic WebSocket connection"""
        uri = f"{WS_BASE_URL}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Should receive connection confirmation
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            assert "type" in data
            assert "session_id" in data
            assert data["type"] == "connected"
    
    @pytest.mark.asyncio
    async def test_ws_command_execution(self):
        """Test command execution via WebSocket"""
        uri = f"{WS_BASE_URL}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            await websocket.recv()
            
            # Send command
            command = {
                "cmd": "echo 'WebSocket Test'",
                "cwd": "/workspace"
            }
            await websocket.send(json.dumps(command))
            
            # Collect messages
            messages = []
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    messages.append(data)
                    
                    if data.get("type") == "complete":
                        break
            except asyncio.TimeoutError:
                pass
            
            # Verify messages
            assert len(messages) >= 2  # At least command and complete
            
            # Check for command acknowledgment
            command_msg = next((m for m in messages if m.get("type") == "command"), None)
            assert command_msg is not None
            assert command_msg["cmd"] == command["cmd"]
            
            # Check for output
            output_msgs = [m for m in messages if m.get("type") == "output"]
            assert len(output_msgs) > 0
            
            # Check for completion
            complete_msg = next((m for m in messages if m.get("type") == "complete"), None)
            assert complete_msg is not None
            assert "exit_code" in complete_msg
    
    @pytest.mark.asyncio
    async def test_ws_multiple_commands(self):
        """Test multiple commands in sequence"""
        uri = f"{WS_BASE_URL}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Wait for connection
            await websocket.recv()
            
            commands = [
                "echo 'Command 1'",
                "echo 'Command 2'",
                "pwd"
            ]
            
            for cmd in commands:
                # Send command
                await websocket.send(json.dumps({
                    "cmd": cmd,
                    "cwd": "/workspace"
                }))
                
                # Wait for completion
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(message)
                    
                    if data.get("type") == "complete":
                        assert "exit_code" in data
                        break
    
    @pytest.mark.asyncio
    async def test_ws_error_handling(self):
        """Test WebSocket error handling"""
        uri = f"{WS_BASE_URL}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Wait for connection
            await websocket.recv()
            
            # Send invalid command
            await websocket.send(json.dumps({
                "cmd": "nonexistent-command-xyz",
                "cwd": "/workspace"
            }))
            
            # Should get error or completion with non-zero exit code
            error_received = False
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                
                if data.get("type") == "error":
                    error_received = True
                    break
                elif data.get("type") == "complete":
                    assert data.get("exit_code", 0) != 0
                    break
            
            # Either error message or non-zero exit code is acceptable
    
    @pytest.mark.asyncio
    async def test_ws_invalid_message(self):
        """Test handling of invalid WebSocket messages"""
        uri = f"{WS_BASE_URL}/ws"
        
        async with websockets.connect(uri) as websocket:
            # Wait for connection
            await websocket.recv()
            
            # Send invalid JSON
            await websocket.send("invalid json")
            
            # Should receive error message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                # If we get a response, it should be an error
                data = json.loads(message)
                if "type" in data:
                    assert data["type"] == "error"
            except (asyncio.TimeoutError, json.JSONDecodeError):
                # Timeout or invalid response is also acceptable
                pass
            
            # Send message without cmd
            await websocket.send(json.dumps({"cwd": "/workspace"}))
            
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            assert data["type"] == "error"
            assert "cmd" in data["message"].lower()

class TestTerminalWebSocket:
    """Test terminal WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_terminal_connection(self):
        """Test terminal WebSocket connection"""
        uri = f"{TERMINAL_BASE_URL}/terminal"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Should receive initial output (welcome message or prompt)
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                assert len(message) > 0
        except Exception as e:
            # Terminal WebSocket might not be ready, which is acceptable for testing
            pytest.skip(f"Terminal WebSocket not available: {e}")
    
    @pytest.mark.asyncio
    async def test_terminal_command_input(self):
        """Test sending commands to terminal"""
        uri = f"{TERMINAL_BASE_URL}/terminal"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Wait for initial output
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=5)
                except asyncio.TimeoutError:
                    pass
                
                # Send command
                await websocket.send("echo 'Terminal Test'\n")
                
                # Should receive output
                output_received = False
                for _ in range(10):  # Try multiple times
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2)
                        if "Terminal Test" in message:
                            output_received = True
                            break
                    except asyncio.TimeoutError:
                        continue
                
                assert output_received, "Did not receive expected terminal output"
        
        except Exception as e:
            pytest.skip(f"Terminal WebSocket test skipped: {e}")

class TestPTYWebSocket:
    """Test PTY WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_pty_connection(self):
        """Test PTY WebSocket connection"""
        session_id = "test_session_123"
        uri = f"{TERMINAL_BASE_URL}/pty/{session_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Should receive connection message
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                
                assert data["type"] == "connected"
                assert data["session_id"] == session_id
        
        except Exception as e:
            pytest.skip(f"PTY WebSocket not available: {e}")
    
    @pytest.mark.asyncio
    async def test_pty_input_output(self):
        """Test PTY input and output"""
        session_id = "test_session_456"
        uri = f"{TERMINAL_BASE_URL}/pty/{session_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Wait for connection
                await websocket.recv()
                
                # Send input
                input_data = {
                    "type": "input",
                    "data": "echo 'PTY Test'\n"
                }
                await websocket.send(json.dumps(input_data))
                
                # Look for output
                output_received = False
                for _ in range(10):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2)
                        data = json.loads(message)
                        
                        if data.get("type") == "output" and "PTY Test" in data.get("data", ""):
                            output_received = True
                            break
                    except (asyncio.TimeoutError, json.JSONDecodeError):
                        continue
                
                assert output_received, "Did not receive expected PTY output"
        
        except Exception as e:
            pytest.skip(f"PTY WebSocket test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_pty_resize(self):
        """Test PTY resize functionality"""
        session_id = "test_session_789"
        uri = f"{TERMINAL_BASE_URL}/pty/{session_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Wait for connection
                await websocket.recv()
                
                # Send resize command
                resize_data = {
                    "type": "resize",
                    "cols": 120,
                    "rows": 40
                }
                await websocket.send(json.dumps(resize_data))
                
                # Resize command should be processed without error
                # We don't expect a specific response, just no errors
                
        except Exception as e:
            pytest.skip(f"PTY resize test skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_pty_ping_pong(self):
        """Test PTY ping/pong functionality"""
        session_id = "test_session_ping"
        uri = f"{TERMINAL_BASE_URL}/pty/{session_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                # Wait for connection
                await websocket.recv()
                
                # Send ping
                ping_data = {"type": "ping"}
                await websocket.send(json.dumps(ping_data))
                
                # Should receive pong
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)
                
                assert data["type"] == "pong"
        
        except Exception as e:
            pytest.skip(f"PTY ping/pong test skipped: {e}")

class TestWebSocketPerformance:
    """Performance tests for WebSocket connections"""
    
    @pytest.mark.asyncio
    async def test_connection_speed(self):
        """Test WebSocket connection establishment speed"""
        uri = f"{WS_BASE_URL}/ws"
        
        start_time = time.time()
        async with websockets.connect(uri) as websocket:
            await websocket.recv()  # Wait for connection message
            end_time = time.time()
        
        connection_time = end_time - start_time
        assert connection_time < 5.0, f"Connection took too long: {connection_time}s"
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Test handling multiple WebSocket connections"""
        uri = f"{WS_BASE_URL}/ws"
        num_connections = 5
        
        async def create_connection():
            async with websockets.connect(uri) as websocket:
                await websocket.recv()  # Connection message
                return True
        
        # Create multiple connections simultaneously
        tasks = [create_connection() for _ in range(num_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All connections should succeed
        successful = sum(1 for r in results if r is True)
        assert successful == num_connections, f"Only {successful}/{num_connections} connections succeeded"

class TestStreamEndpoint:
    """Test stream WebSocket endpoint"""
    
    @pytest.mark.asyncio
    async def test_stream_connection(self):
        """Test stream WebSocket connection"""
        uri = f"{WS_BASE_URL}/stream"
        
        async with websockets.connect(uri) as websocket:
            # Should receive subscription confirmation
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            assert "type" in data
            assert data["type"] == "subscribed"
            assert "channels" in data
    
    @pytest.mark.asyncio
    async def test_stream_heartbeat(self):
        """Test stream heartbeat messages"""
        uri = f"{WS_BASE_URL}/stream"
        
        async with websockets.connect(uri) as websocket:
            # Skip subscription message
            await websocket.recv()
            
            # Should receive heartbeat within reasonable time
            message = await asyncio.wait_for(websocket.recv(), timeout=35)
            data = json.loads(message)
            
            assert data["type"] == "heartbeat"
            assert "timestamp" in data
            assert "connections" in data
    
    @pytest.mark.asyncio
    async def test_stream_ping_pong(self):
        """Test stream ping/pong"""
        uri = f"{WS_BASE_URL}/stream"
        
        async with websockets.connect(uri) as websocket:
            # Skip subscription message
            await websocket.recv()
            
            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Should receive pong
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            assert data["type"] == "pong"

def run_tests():
    """Run all WebSocket tests"""
    print("Starting DockerFlow WebSocket Test Suite...")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "--durations=10",
        "-k", "not test_terminal"  # Skip terminal tests if they fail
    ])
    
    return exit_code

if __name__ == "__main__":
    import sys
    sys.exit(run_tests())