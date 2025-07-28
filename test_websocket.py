#!/usr/bin/env python3
"""
Simple WebSocket test to check terminal connection
"""
import asyncio
import websockets
import json

async def test_websocket():
    # First, let's get a container ID by listing containers
    import requests
    
    try:
        # Test without auth first
        response = requests.get('http://localhost:8000/api/containers/')
        print(f"Container API response: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("Authentication required - this is expected")
            return
            
    except Exception as e:
        print(f"Error testing container API: {e}")
        return
    
    # For now, let's use the container we saw in docker ps
    container_id = "pyexec-ca3874d8-8fea7abf"
    
    try:
        uri = f"ws://localhost:8000/api/ws/terminal/{container_id}"
        print(f"Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected!")
            
            # Send a test message
            test_message = {
                "type": "terminal_input",
                "data": "echo 'Hello from WebSocket test'\n"
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"Sent: {test_message}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No response received within 5 seconds")
                
    except Exception as e:
        print(f"WebSocket connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 