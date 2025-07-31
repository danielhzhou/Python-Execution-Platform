#!/usr/bin/env python3
"""
Test script to verify Monaco Editor <-> Docker Container integration
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# Configuration
API_BASE = "http://localhost:8000/api"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

class IntegrationTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.container_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def api_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None) -> Dict[Any, Any]:
        """Make an authenticated API request"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        url = f"{API_BASE}{endpoint}"
        
        try:
            async with self.session.request(
                method, 
                url, 
                headers=headers, 
                json=data if data else None
            ) as resp:
                response_data = await resp.json()
                return {
                    "success": resp.status < 400,
                    "status": resp.status,
                    "data": response_data
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def login(self) -> bool:
        """Login and get auth token"""
        print("🔐 Logging in...")
        result = await self.api_request("POST", "/auth/login", {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if result["success"] and "access_token" in result["data"]:
            self.auth_token = result["data"]["access_token"]
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {result}")
            return False
    
    async def create_container(self) -> bool:
        """Create a new container"""
        print("🐳 Creating container...")
        result = await self.api_request("POST", "/containers/create", {})
        
        if result["success"]:
            self.container_id = result["data"]["session_id"]
            print(f"✅ Container created: {self.container_id}")
            # Wait a bit for container to be ready
            await asyncio.sleep(3)
            return True
        else:
            print(f"❌ Container creation failed: {result}")
            return False
    
    async def test_file_operations(self) -> bool:
        """Test file operations: create, read, update, delete"""
        print("📁 Testing file operations...")
        
        # Test 1: Create a new file
        test_content = '''# Monaco Editor <-> Docker Integration Test
print("Hello from Monaco Editor!")
print("This file was created via the API and should be visible in the container")

def test_function():
    return "Integration working!"

if __name__ == "__main__":
    result = test_function()
    print(f"Result: {result}")
'''
        
        print("📝 Creating test file...")
        result = await self.api_request("POST", f"/containers/{self.container_id}/files", {
            "path": "/workspace/integration_test.py",
            "content": test_content
        })
        
        if not result["success"]:
            print(f"❌ File creation failed: {result}")
            return False
        print("✅ File created successfully")
        
        # Test 2: Read the file back
        print("📖 Reading file back...")
        result = await self.api_request("GET", f"/containers/{self.container_id}/files/content?path=/workspace/integration_test.py")
        
        if not result["success"]:
            print(f"❌ File read failed: {result}")
            return False
            
        if result["data"]["content"] != test_content:
            print("❌ File content mismatch!")
            return False
        print("✅ File read successfully with correct content")
        
        # Test 3: Update the file
        updated_content = test_content + '\nprint("File updated via API!")\n'
        print("✏️ Updating file...")
        result = await self.api_request("POST", f"/containers/{self.container_id}/files", {
            "path": "/workspace/integration_test.py",
            "content": updated_content
        })
        
        if not result["success"]:
            print(f"❌ File update failed: {result}")
            return False
        print("✅ File updated successfully")
        
        # Test 4: Verify update
        result = await self.api_request("GET", f"/containers/{self.container_id}/files/content?path=/workspace/integration_test.py")
        if result["success"] and result["data"]["content"] == updated_content:
            print("✅ File update verified")
        else:
            print("❌ File update verification failed")
            return False
        
        # Test 5: List files
        print("📋 Listing container files...")
        result = await self.api_request("GET", f"/containers/{self.container_id}/files")
        
        if not result["success"]:
            print(f"❌ File listing failed: {result}")
            return False
            
        files = result["data"]
        test_file_found = any(f["path"] == "/workspace/integration_test.py" for f in files)
        if not test_file_found:
            print("❌ Test file not found in file listing")
            return False
        print(f"✅ File listing successful ({len(files)} files found)")
        
        # Test 6: Create directory
        print("📁 Creating test directory...")
        result = await self.api_request("POST", f"/containers/{self.container_id}/directories?path=/workspace/test_dir")
        
        if not result["success"]:
            print(f"❌ Directory creation failed: {result}")
            return False
        print("✅ Directory created successfully")
        
        return True
    
    async def cleanup(self):
        """Clean up test resources"""
        if self.container_id:
            print("🧹 Cleaning up container...")
            result = await self.api_request("POST", f"/containers/{self.container_id}/terminate")
            if result["success"]:
                print("✅ Container terminated")
            else:
                print(f"⚠️ Container cleanup failed: {result}")

async def main():
    """Run the integration test"""
    print("🚀 Starting Monaco Editor <-> Docker Container Integration Test")
    print("=" * 60)
    
    async with IntegrationTester() as tester:
        try:
            # Step 1: Login
            if not await tester.login():
                print("❌ Test failed: Could not login")
                return False
            
            # Step 2: Create container
            if not await tester.create_container():
                print("❌ Test failed: Could not create container")
                return False
            
            # Step 3: Test file operations
            if not await tester.test_file_operations():
                print("❌ Test failed: File operations failed")
                return False
            
            print("=" * 60)
            print("🎉 All tests passed! Monaco Editor <-> Docker integration is working!")
            print("=" * 60)
            print("\n📋 Summary:")
            print("✅ Authentication working")
            print("✅ Container creation working")
            print("✅ File creation in container working")
            print("✅ File reading from container working")
            print("✅ File updates in container working")
            print("✅ File listing from container working")
            print("✅ Directory creation in container working")
            print("\n🎯 Monaco editor should now be able to:")
            print("   • Create and edit files directly in the Docker container")
            print("   • Auto-save changes to the container filesystem")
            print("   • Execute code that runs from the actual container files")
            print("   • Browse and manage the container file tree")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False
        finally:
            await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)