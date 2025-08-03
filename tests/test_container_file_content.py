#!/usr/bin/env python3
"""
Test to check what's actually in the container file
"""
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

async def check_container_file():
    print("🔍 Checking actual container file content")
    print("=" * 50)
    
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
        
        # Read the main.py file
        print("📖 Reading /workspace/main.py from container...")
        async with session.get(f"{API_BASE}/containers/{container_id}/files/content?path=/workspace/main.py",
                             headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to read file: {resp.status}")
                return
            
            file_data = await resp.json()
            content = file_data.get("content", "")
            
            print(f"📊 File size: {len(content)} characters")
            print("📄 File content:")
            print("-" * 40)
            print(content)
            print("-" * 40)
            
            # Check for the specific changes
            if "[3, 3, 3, 3, 3]" in content:
                print("✅ SUCCESS: File contains your edited content [3, 3, 3, 3, 3]")
            elif "[1, 2, 3, 4, 5]" in content:
                print("❌ PROBLEM: File still contains original content [1, 2, 3, 4, 5]")
            else:
                print("⚠️  UNKNOWN: File doesn't contain expected array")
            
            # Check line by line
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'numbers = [' in line:
                    print(f"🎯 Line {i}: {line}")

if __name__ == "__main__":
    asyncio.run(check_container_file())