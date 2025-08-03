#!/usr/bin/env python3
"""
Simple WebSocket test for basic connectivity
"""
import asyncio
import websockets
import json

async def test_simple_websocket():
    try:
        uri = "ws://localhost:8000/api/ws/test"
        print(f"Connecting to test WebSocket: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Wait for initial message
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No initial message received")
            
            # Send a test message
            await websocket.send("Hello WebSocket!")
            print("Sent: Hello WebSocket!")
            
            # Wait for echo
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Echo received: {response}")
            except asyncio.TimeoutError:
                print("No echo received")
                
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_websocket()) 