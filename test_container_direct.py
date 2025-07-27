#!/usr/bin/env python3
"""
Direct test of container functionality without auth
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_container_creation():
    """Test container creation directly"""
    try:
        from app.services.container_service import container_service
        from app.services.database_service import db_service
        
        print("🧪 Testing container creation...")
        
        # Test user ID (UUID format)
        test_user_id = "f9cdc232-8f27-4ddf-a137-56704f8e4343"
        
        print(f"📝 Creating container for user: {test_user_id}")
        
        # Create container
        session = await container_service.create_container(
            user_id=test_user_id,
            project_id="test-project",
            project_name="Test Project",
            initial_files={"main.py": "print('Hello World!')"}
        )
        
        print(f"✅ Container created successfully!")
        print(f"   Session ID: {session.id}")
        print(f"   Container ID: {session.container_id}")
        print(f"   Status: {session.status}")
        
        # Test terminal session creation
        print("\n🖥️  Testing terminal session creation...")
        from app.services.terminal_service import terminal_service
        
        # Debug: Check what's in active_containers
        print(f"🔍 Active containers: {list(container_service.active_containers.keys())}")
        print(f"🔍 Looking for session: {session.id}")
        print(f"🔍 Session type: {type(session.id)}")
        
        terminal_success = await terminal_service.create_terminal_session(str(session.id))
        
        if terminal_success:
            print("✅ Terminal session created successfully!")
        else:
            print("❌ Terminal session creation failed")
            
        # Cleanup
        print("\n🧹 Cleaning up...")
        cleanup_success = await container_service.terminate_container(str(session.id))
        
        if cleanup_success:
            print("✅ Container terminated successfully!")
        else:
            print("❌ Container termination failed")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_container_creation())
    sys.exit(0 if success else 1) 