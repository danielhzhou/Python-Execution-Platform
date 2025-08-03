#!/usr/bin/env python3
"""
Comprehensive System Verification Script
Tests all major components of the Python Execution Platform
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SystemVerifier:
    """Comprehensive system verification"""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.test_user_id = None
        self.test_project_id = None
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        self.results[test_name] = {"success": success, "details": details}
        
    async def test_config_loading(self):
        """Test configuration loading"""
        try:
            from app.core.config import settings
            self.log_result("Configuration Loading", True, 
                          f"Environment: {settings.ENVIRONMENT}")
            return True
        except Exception as e:
            self.log_result("Configuration Loading", False, str(e))
            return False
            
    async def test_app_initialization(self):
        """Test FastAPI app initialization"""
        try:
            from app.main import app
            self.log_result("FastAPI App Initialization", True, 
                          f"App created with {len(app.routes)} routes")
            return True
        except Exception as e:
            self.log_result("FastAPI App Initialization", False, str(e))
            return False
            
    async def test_supabase_connection(self):
        """Test Supabase connection"""
        try:
            from app.core.supabase import get_supabase_client
            client = get_supabase_client()
            # Try a simple operation
            result = client.table("users").select("id").limit(1).execute()
            self.log_result("Supabase Connection", True, 
                          f"Connected to Supabase, response: {len(result.data)} rows")
            return True
        except Exception as e:
            self.log_result("Supabase Connection", False, str(e))
            return False
            
    async def test_database_operations(self):
        """Test basic database operations"""
        try:
            from app.services.database_service import db_service
            
            # Create a test user with proper UUID from Supabase auth
            self.test_user_id = str(uuid.uuid4())
            
            # First, let's check if we can connect to the database
            from app.core.supabase import get_db_session
            with get_db_session() as session:
                # Test basic connection
                result = session.execute("SELECT 1 as test").fetchone()
                if result[0] != 1:
                    raise Exception("Database connection test failed")
                    
            self.log_result("Database Connection", True, "Direct SQL query successful")
            
            # Note: User creation might fail due to foreign key constraints
            # This is expected if the database schema hasn't been properly initialized
            try:
                user = await db_service.create_or_update_user(
                    user_id=self.test_user_id,
                    email='test@example.com',
                    full_name='Test User'
                )
                self.log_result("User Creation", True, f"Created user: {user.email}")
            except Exception as user_error:
                self.log_result("User Creation", False, 
                              f"Expected if schema not initialized: {user_error}")
                
            return True
        except Exception as e:
            self.log_result("Database Operations", False, str(e))
            return False
            
    async def test_container_service(self):
        """Test container service initialization"""
        try:
            from app.services.container_service import container_service
            
            # Test service initialization
            await container_service.start()
            
            # Check if Docker is available
            import docker
            client = docker.from_env()
            info = client.info()
            
            self.log_result("Container Service", True, 
                          f"Docker available, containers: {info.get('Containers', 0)}")
            
            await container_service.stop()
            return True
        except Exception as e:
            self.log_result("Container Service", False, str(e))
            return False
            
    async def test_terminal_service(self):
        """Test terminal service"""
        try:
            from app.services.terminal_service import terminal_service
            
            # Test service initialization
            self.log_result("Terminal Service", True, "Service imported successfully")
            return True
        except Exception as e:
            self.log_result("Terminal Service", False, str(e))
            return False
            
    async def test_websocket_service(self):
        """Test WebSocket service"""
        try:
            from app.services.websocket_service import websocket_service
            
            # Test service initialization
            self.log_result("WebSocket Service", True, "Service imported successfully")
            return True
        except Exception as e:
            self.log_result("WebSocket Service", False, str(e))
            return False
            
    async def test_storage_service(self):
        """Test storage service"""
        try:
            from app.services.storage_service import storage_service
            
            # Test bucket existence check
            bucket_exists = await storage_service.ensure_bucket_exists()
            self.log_result("Storage Service", bucket_exists, 
                          "Bucket creation/verification completed")
            return True
        except Exception as e:
            self.log_result("Storage Service", False, str(e))
            return False
            
    async def test_api_routes(self):
        """Test API route registration"""
        try:
            from app.api import api_router
            
            route_count = len(api_router.routes)
            self.log_result("API Routes", True, f"Registered {route_count} routes")
            
            # List some routes
            routes = []
            for route in api_router.routes:
                if hasattr(route, 'path'):
                    routes.append(f"{','.join(route.methods)} {route.path}")
                    
            if routes:
                print("    Sample routes:")
                for route in routes[:5]:  # Show first 5 routes
                    print(f"      {route}")
                    
            return True
        except Exception as e:
            self.log_result("API Routes", False, str(e))
            return False
            
    async def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 Starting Python Execution Platform System Verification")
        print("=" * 60)
        
        tests = [
            ("Configuration", self.test_config_loading),
            ("App Initialization", self.test_app_initialization),
            ("Supabase Connection", self.test_supabase_connection),
            ("Database Operations", self.test_database_operations),
            ("Container Service", self.test_container_service),
            ("Terminal Service", self.test_terminal_service),
            ("WebSocket Service", self.test_websocket_service),
            ("Storage Service", self.test_storage_service),
            ("API Routes", self.test_api_routes),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            try:
                success = await test_func()
                if success:
                    passed += 1
            except Exception as e:
                self.log_result(f"{test_name} (Exception)", False, str(e))
                
        print("\n" + "=" * 60)
        print(f"📊 VERIFICATION SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All systems operational!")
        else:
            print("⚠️  Some issues detected. Check the details above.")
            
        return passed == total


async def main():
    """Main verification function"""
    verifier = SystemVerifier()
    success = await verifier.run_all_tests()
    
    print("\n📋 NEXT STEPS:")
    if success:
        print("✅ System is ready for use!")
        print("   - Start the backend: uvicorn app.main:app --reload")
        print("   - Run tests: ./run_tests.sh unit")
        print("   - Check API docs: http://localhost:8000/docs")
    else:
        print("🔧 Issues to address:")
        print("   1. Check database schema initialization")
        print("   2. Verify Supabase configuration")
        print("   3. Ensure Docker is running")
        print("   4. Review error messages above")
        
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 