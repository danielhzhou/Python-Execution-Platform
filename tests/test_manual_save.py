#!/usr/bin/env python3
"""
Manual test to verify file save and read from Docker container
"""
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

async def test_manual_save():
    print("🧪 Testing Manual File Save to Docker Container")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Login
        print("1. 🔐 Logging in...")
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
            print("✅ Login successful")
        
        # Get container
        print("2. 🐳 Getting container...")
        async with session.get(f"{API_BASE}/containers/", headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to get containers: {resp.status}")
                return
            
            containers = await resp.json()
            if not containers:
                print("❌ No containers found")
                return
            
            container_id = containers[0]["session_id"]
            print(f"✅ Using container: {container_id}")
        
        # Test the exact content you're trying to save
        test_content = '''# Welcome to Python Execution Platform
# Start coding here...

def main():
    print("Hello, World!")
    print("This is your Python workspace!")
    
    # Try some basic Python features
    numbers = [3, 3, 3, 3, 3]
    squared = [x**2 for x in numbers]
    print(f"Original numbers: {numbers}")
    print(f"Squared numbers: {squared}")
    
    # You can install packages using: pip install package-name
    # Then run your code by clicking the Run button or pressing Ctrl+Enter

if __name__ == "__main__":
    main()
'''
        
        file_path = "/workspace/main.py"
        
        print(f"3. 💾 Saving your edited content to {file_path}...")
        print(f"📝 Content preview: {test_content[:100]}...")
        
        async with session.post(f"{API_BASE}/containers/{container_id}/files", 
                              json={"path": file_path, "content": test_content},
                              headers=headers) as resp:
            
            print(f"📊 Save response status: {resp.status}")
            response_text = await resp.text()
            print(f"📄 Save response: {response_text}")
            
            if resp.status != 200:
                print(f"❌ Save failed with status {resp.status}")
                return
            
            print("✅ Save request completed")
        
        print("4. 📖 Reading file back from container...")
        async with session.get(f"{API_BASE}/containers/{container_id}/files/content?path={file_path}",
                             headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Read failed: {resp.status}")
                return
            
            file_data = await resp.json()
            read_content = file_data.get("content", "")
            
            print(f"📄 Read content preview: {read_content[:100]}...")
            
            if "[3, 3, 3, 3, 3]" in read_content:
                print("✅ SUCCESS: File contains your edited content!")
            elif "[1, 2, 3, 4, 5]" in read_content:
                print("❌ FAILURE: File still contains original content")
            else:
                print("⚠️ UNKNOWN: File content is different than expected")
        
        print("\n" + "=" * 50)
        print("🎯 NEXT STEPS:")
        print("1. Check the backend logs for save request details")
        print("2. Try editing and saving in Monaco Editor")
        print("3. Check browser console for frontend save logs")
        print("4. Run this test again to verify the save worked")

if __name__ == "__main__":
    asyncio.run(test_manual_save())