#!/usr/bin/env python3
"""
Debug script to test file synchronization between Monaco Editor and Docker container
"""
import asyncio
import aiohttp
import json
import time

# Configuration - adjust these for your setup
API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"  # Replace with your test user
TEST_PASSWORD = "testpassword123"  # Replace with your test password

async def debug_file_sync():
    """Debug file synchronization issues"""
    print("🔍 Debugging File Synchronization Issues")
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
            if not token:
                print("❌ No access token received")
                return
            
            print("✅ Login successful")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get or create container
        print("2. 🐳 Getting container...")
        async with session.get(f"{API_BASE}/containers/", headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to get containers: {resp.status}")
                return
            
            containers = await resp.json()
            if not containers:
                print("📦 No containers found, creating one...")
                async with session.post(f"{API_BASE}/containers/create", 
                                      json={}, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"❌ Failed to create container: {resp.status}")
                        return
                    container_data = await resp.json()
                    container_id = container_data["session_id"]
            else:
                container_id = containers[0]["session_id"]
            
            print(f"✅ Using container: {container_id}")
        
        # Test file operations
        test_file_path = "/workspace/debug_test.py"
        original_content = '''# Original content
print("This is the ORIGINAL code")
print("If you see this, the file sync is NOT working")
'''
        
        updated_content = '''# Updated content  
print("This is the UPDATED code")
print("If you see this, the file sync IS working!")
print("Success! Monaco editor changes are reflected in container")
'''
        
        print(f"3. 📝 Creating test file: {test_file_path}")
        async with session.post(f"{API_BASE}/containers/{container_id}/files", 
                              json={"path": test_file_path, "content": original_content},
                              headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to create file: {resp.status}")
                print(await resp.text())
                return
            print("✅ Test file created")
        
        print("4. 📖 Reading file back...")
        async with session.get(f"{API_BASE}/containers/{container_id}/files/content?path={test_file_path}",
                             headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to read file: {resp.status}")
                return
            
            file_data = await resp.json()
            if file_data["content"] == original_content:
                print("✅ File read correctly")
            else:
                print("❌ File content mismatch on read")
                return
        
        print("5. ✏️ Updating file content...")
        async with session.post(f"{API_BASE}/containers/{container_id}/files", 
                              json={"path": test_file_path, "content": updated_content},
                              headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to update file: {resp.status}")
                print(await resp.text())
                return
            print("✅ File updated via API")
        
        print("6. 🔍 Verifying update...")
        async with session.get(f"{API_BASE}/containers/{container_id}/files/content?path={test_file_path}",
                             headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Failed to read updated file: {resp.status}")
                return
            
            file_data = await resp.json()
            if file_data["content"] == updated_content:
                print("✅ File update verified via API")
            else:
                print("❌ File update NOT reflected in API read")
                print(f"Expected: {updated_content[:50]}...")
                print(f"Got: {file_data['content'][:50]}...")
                return
        
        print("\n" + "=" * 50)
        print("🎯 MANUAL TESTING INSTRUCTIONS:")
        print("=" * 50)
        print(f"1. Open Monaco Editor in your browser")
        print(f"2. Load the file: {test_file_path}")
        print(f"3. You should see the UPDATED content (not original)")
        print(f"4. Make a change in Monaco Editor")
        print(f"5. Save the file (Ctrl+S or Save button)")
        print(f"6. Click Run button")
        print(f"7. Check terminal output - it should show your changes")
        print("")
        print("🔍 DEBUGGING CHECKLIST:")
        print("✅ API file save/read working")
        print("? Monaco Editor loading correct content")
        print("? Auto-save working when typing")
        print("? Manual save working before execution")
        print("? Terminal executing the updated file")
        print("")
        print("📋 If execution shows old code, check:")
        print("- Browser console for save errors")
        print("- Network tab for failed API calls")
        print("- Container logs for file write issues")

if __name__ == "__main__":
    asyncio.run(debug_file_sync())