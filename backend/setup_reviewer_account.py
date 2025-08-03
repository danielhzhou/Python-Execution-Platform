#!/usr/bin/env python3
"""
Setup script to create a centralized reviewer account.
Run this script to create or update the reviewer account.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.database_service import db_service
from app.core.supabase import get_supabase_client


async def setup_reviewer_account():
    """Create or update the centralized reviewer account"""
    
    # Configuration
    REVIEWER_EMAIL = "reviewer@pythonplatform.com"
    REVIEWER_PASSWORD = "ReviewerPass123!"  # Change this to a secure password
    REVIEWER_NAME = "Platform Reviewer"
    
    print("🔧 Setting up centralized reviewer account...")
    
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Try to create the user in Supabase Auth
        print(f"📧 Creating Supabase auth account for {REVIEWER_EMAIL}...")
        
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": REVIEWER_EMAIL,
                "password": REVIEWER_PASSWORD,
                "email_confirm": True,  # Skip email confirmation
                "user_metadata": {
                    "full_name": REVIEWER_NAME
                }
            })
            
            supabase_user = auth_response.user
            print(f"✅ Supabase user created with ID: {supabase_user.id}")
            
        except Exception as e:
            if "already registered" in str(e).lower() or "already exists" in str(e).lower():
                print(f"ℹ️  User {REVIEWER_EMAIL} already exists in Supabase Auth")
                # Get existing user
                users_response = supabase.auth.admin.list_users()
                supabase_user = None
                for user in users_response:
                    if user.email == REVIEWER_EMAIL:
                        supabase_user = user
                        break
                
                if not supabase_user:
                    print(f"❌ Could not find existing user {REVIEWER_EMAIL}")
                    return False
                    
                print(f"✅ Found existing Supabase user with ID: {supabase_user.id}")
            else:
                print(f"❌ Error creating Supabase user: {e}")
                return False
        
        # Create or update user in our database with reviewer role
        print("🗄️  Creating/updating user in database...")
        
        user_record = await db_service.create_or_update_user(
            user_id=supabase_user.id,
            email=REVIEWER_EMAIL,
            full_name=REVIEWER_NAME,
            role="reviewer"  # Set as reviewer
        )
        
        print(f"✅ Database user record created/updated:")
        print(f"   - ID: {user_record.id}")
        print(f"   - Email: {user_record.email}")
        print(f"   - Name: {user_record.full_name}")
        print(f"   - Role: {user_record.role}")
        
        print("\n🎉 Reviewer account setup complete!")
        print(f"\n📋 Login credentials:")
        print(f"   Email: {REVIEWER_EMAIL}")
        print(f"   Password: {REVIEWER_PASSWORD}")
        print(f"\n⚠️  IMPORTANT: Change the password after first login!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up reviewer account: {e}")
        return False


async def main():
    """Main function"""
    print("🚀 Python Execution Platform - Reviewer Account Setup")
    print("=" * 60)
    
    # Check environment variables
    required_env_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "DATABASE_URL"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment.")
        return
    
    success = await setup_reviewer_account()
    
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())