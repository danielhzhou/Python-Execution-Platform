#!/usr/bin/env python3
"""
Test to verify the Docker client consistency fix
"""
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

async def test_docker_client_fix():
    print("🔧 Testing Docker Client Consistency Fix")
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
            print(f"✅ Using container: {container_id}")
        
        # Test content with clear marker
        test_content = f'''# Docker Client Consistency Test
# Timestamp: {asyncio.get_event_loop().time()}

def main():
    print("DOCKER CLIENT FIX TEST")
    print("This should appear in execution!")
    
    # Your edited numbers
    numbers = [3, 3, 3, 3, 3]
    squared = [x**2 for x in numbers]
    print(f"Original numbers: {{numbers}}")
    print(f"Squared numbers: {{squared}}")

if __name__ == "__main__":
    main()
'''
        
        # Save the test content
        print("💾 Saving test content with Docker client fix...")
        async with session.post(f"{API_BASE}/containers/{container_id}/files", 
                              json={"path": "/workspace/main.py", "content": test_content},
                              headers=headers) as resp:
            
            print(f"📊 Save status: {resp.status}")
            if resp.status != 200:
                error_text = await resp.text()
                print(f"❌ Save failed: {error_text}")
                return
            
            print("✅ File saved successfully")
        
        # Read it back immediately
        print("📖 Reading file back...")
        async with session.get(f"{API_BASE}/containers/{container_id}/files/content?path=/workspace/main.py",
                             headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Read failed: {resp.status}")
                return
            
            file_data = await resp.json()
            read_content = file_data.get("content", "")
            
            # Check if our test content is there
            if "DOCKER CLIENT FIX TEST" in read_content and "[3, 3, 3, 3, 3]" in read_content:
                print("✅ SUCCESS: File contains the correct test content!")
                print("🎯 The Docker client fix appears to be working!")
            else:
                print("❌ FAILURE: File doesn't contain expected content")
                print(f"📄 Content preview: {read_content[:200]}...")
        
        print("\n" + "=" * 50)
        print("🎯 NEXT: Try running the code in Monaco Editor")
        print("You should see 'DOCKER CLIENT FIX TEST' in the output")

if __name__ == "__main__":
    asyncio.run(test_docker_client_fix())