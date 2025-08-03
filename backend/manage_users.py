#!/usr/bin/env python3
"""
User management script for testing authentication
"""
import asyncio
import sys
from app.core.auth import create_user_account, authenticate_user
from app.core.supabase import get_supabase_client
from app.services.database_service import db_service


async def create_test_user():
    """Create a test user for authentication testing"""
    email = "test@example.com"
    password = "password123"
    
    try:
        print(f"Creating test user: {email}")
        result = await create_user_account(
            email=email,
            password=password,
            full_name="Test User"
        )
        print("✅ User created successfully!")
        print(f"User ID: {result['user_id']}")
        print(f"Email confirmation required: {result['email_confirmation_required']}")
        return email, password
    except Exception as e:
        if "already registered" in str(e):
            print("✅ User already exists")
            return email, password
        else:
            print(f"❌ Failed to create user: {e}")
            return None, None


async def test_login(email: str, password: str):
    """Test user login"""
    try:
        print(f"\nTesting login for: {email}")
        auth_result = await authenticate_user(email=email, password=password)
        print("✅ Login successful!")
        print(f"User ID: {auth_result['user'].id}")
        print(f"Email: {auth_result['user'].email}")
        print(f"Email confirmed: {auth_result['user'].email_confirmed_at is not None}")
        print(f"Access token: {auth_result['access_token'][:50]}...")
        return auth_result['access_token']
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None


async def confirm_user_email(email: str):
    """Manually confirm user email in Supabase (for testing/admin purposes)"""
    try:
        supabase = get_supabase_client()
        
        # This is a workaround - we'll use the service key to update the user
        print(f"\nAttempting to confirm email for: {email}")
        
        # Get user by email (using service key)
        users = supabase.auth.admin.list_users()
        user_to_confirm = None
        
        for user in users:
            if user.email == email:
                user_to_confirm = user
                break
        
        if user_to_confirm:
            # Update user to confirm email
            updated_user = supabase.auth.admin.update_user_by_id(
                user_to_confirm.id,
                {"email_confirm": True}
            )
            print("✅ Email confirmed successfully!")
            return True
        else:
            print("❌ User not found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to confirm email: {e}")
        return False


async def list_users():
    """List all users in the database"""
    try:
        print("\n=== Users in Database ===")
        from app.models.container import User
        from app.core.supabase import get_db_session
        from sqlmodel import select
        
        with get_db_session() as session:
            users = session.exec(select(User)).all()
            
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Name: {user.full_name}")
            print(f"Created: {user.created_at}")
            print("---")
            
    except Exception as e:
        print(f"❌ Failed to list users: {e}")


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_users.py create    - Create test user")
        print("  python manage_users.py login     - Test login")
        print("  python manage_users.py confirm   - Confirm test user email")
        print("  python manage_users.py list      - List all users")
        print("  python manage_users.py test      - Full test flow")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        await create_test_user()
    elif command == "login":
        await test_login("test@example.com", "password123")
    elif command == "confirm":
        await confirm_user_email("test@example.com")
    elif command == "list":
        await list_users()
    elif command == "test":
        print("=== Full Authentication Test ===")
        email, password = await create_test_user()
        if email and password:
            # Try login first
            token = await test_login(email, password)
            if not token:
                # If login fails, try to confirm email
                print("\nLogin failed, attempting to confirm email...")
                if await confirm_user_email(email):
                    await test_login(email, password)
        await list_users()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())