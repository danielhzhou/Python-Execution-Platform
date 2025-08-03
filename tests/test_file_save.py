#!/usr/bin/env python3
"""
Quick test to verify file save functionality
"""
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

async def test_file_save():
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(f"{API_BASE}/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }) as resp:
            if resp.status != 200:
                print(f"❌ Login failed: {resp.status}")
                return
            
            login_data = await resp.json()
            token = login_data.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
        
        # Get container
        async with session.get(f"{API_BASE}/containers/", headers=headers) as resp:
            containers = await resp.json()
            if not containers:
                print("❌ No containers found")
                return
            container_id = containers[0]["session_id"]
        
        # Test simple save
        test_content = """print("Hello, World!")
print("This is a test file")
x = 42
print(f"The answer is {x}")
"""
        
        print("🧪 Testing file save...")
        async with session.post(f"{API_BASE}/containers/{container_id}/files", 
                              json={"path": "/workspace/test_save.py", "content": test_content},
                              headers=headers) as resp:
            
            print(f"Status: {resp.status}")
            response_text = await resp.text()
            print(f"Response: {response_text}")
            
            if resp.status == 200:
                print("✅ File save successful!")
            else:
                print(f"❌ File save failed: {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_file_save())