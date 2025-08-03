#!/usr/bin/env python3
"""
Setup script for Supabase submission storage bucket
Run this script to create the necessary storage bucket and policies
"""
import os
import sys
from app.core.supabase import get_supabase_client

def setup_submission_bucket():
    """Create submissions bucket with proper folder structure"""
    supabase = get_supabase_client()
    bucket_name = "submissions"
    
    print(f"Setting up Supabase storage bucket: {bucket_name}")
    
    try:
        # Create the bucket
        print("Creating submissions bucket...")
        
        # First check if bucket already exists
        try:
            bucket_list = supabase.storage.list_buckets()
            existing_buckets = [b.name for b in bucket_list.data] if bucket_list.data else []
            
            if bucket_name in existing_buckets:
                print("✓ Bucket already exists")
                bucket_result = type('obj', (object,), {'error': None})()  # Mock success
            else:
                # Create bucket with minimal parameters
                bucket_result = supabase.storage.create_bucket(bucket_name)
        except Exception as e:
            print(f"❌ Error with bucket operations: {e}")
            return False
        
        if bucket_result.error:
            if "already exists" in str(bucket_result.error).lower():
                print("✓ Bucket already exists")
            else:
                print(f"❌ Error creating bucket: {bucket_result.error}")
                return False
        else:
            print("✓ Bucket created successfully")
        
        # Create folder structure by uploading placeholder files
        folders = ["pending", "approved", "rejected"]
        
        for folder in folders:
            placeholder_path = f"{folder}/.gitkeep"
            print(f"Creating folder structure: {folder}/")
            
            upload_result = supabase.storage.from_(bucket_name).upload(
                path=placeholder_path,
                file=b"# This file maintains the folder structure\n",
                file_options={"content-type": "text/plain", "upsert": "true"}
            )
            
            if upload_result.error:
                print(f"⚠️  Warning: Could not create {folder}/ folder: {upload_result.error}")
            else:
                print(f"✓ Created {folder}/ folder")
        
        print("\n✅ Submission storage setup completed!")
        print("\nFolder structure:")
        print("submissions/")
        print("├── pending/{submission_id}/")
        print("│   ├── file1.py                              # Individual files")
        print("│   ├── file2.js")
        print("│   └── ...")
        print("├── approved/{submission_id}/")
        print("│   └── [individual files after approval]")
        print("└── rejected/{submission_id}/")
        print("    └── [individual files after rejection]")
        print("\nNote: Files are stored individually, not as ZIP archives.")
        print("Downloads create ZIP files on-the-fly from individual files.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up storage: {e}")
        return False

def setup_storage_policies():
    """Set up RLS policies for the submissions bucket"""
    print("\n📋 Storage Policies Setup")
    print("Please run the following SQL in your Supabase SQL Editor:")
    print("\n" + "="*60)
    
    policies_sql = """
-- Storage policies for submissions bucket
-- Run this in Supabase SQL Editor

-- Allow authenticated users to upload to pending folder
INSERT INTO storage.policies (name, bucket_id, policy_role, policy_cmd, policy_definition)
VALUES (
  'Allow authenticated uploads to pending',
  'submissions',
  'authenticated',
  'INSERT',
  'auth.role() = ''authenticated'' AND (storage.foldername(name))[1] = ''pending'''
);

-- Allow authenticated users to read their own submissions
INSERT INTO storage.policies (name, bucket_id, policy_role, policy_cmd, policy_definition)
VALUES (
  'Allow users to read own submissions',
  'submissions',
  'authenticated',
  'SELECT',
  'auth.role() = ''authenticated'''
);

-- Allow reviewers to read all submissions
INSERT INTO storage.policies (name, bucket_id, policy_role, policy_cmd, policy_definition)
VALUES (
  'Allow reviewers to read all submissions',
  'submissions',
  'authenticated',
  'SELECT',
  'auth.role() = ''authenticated'''
);

-- Allow reviewers to move files between folders
INSERT INTO storage.policies (name, bucket_id, policy_role, policy_cmd, policy_definition)
VALUES (
  'Allow reviewers to manage submissions',
  'submissions',
  'authenticated',
  'UPDATE',
  'auth.role() = ''authenticated'''
);

INSERT INTO storage.policies (name, bucket_id, policy_role, policy_cmd, policy_definition)
VALUES (
  'Allow reviewers to delete submissions',
  'submissions',
  'authenticated',
  'DELETE',
  'auth.role() = ''authenticated'''
);
"""
    
    print(policies_sql)
    print("="*60)
    print("\n📝 Note: These policies provide basic access control.")
    print("For production, you should implement more granular role-based policies.")

if __name__ == "__main__":
    print("🚀 Supabase Submission Storage Setup")
    print("="*40)
    
    # Check if we have the required environment variables
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
        print("❌ Missing required environment variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_KEY")
        print("\nPlease set these in your .env file or environment.")
        sys.exit(1)
    
    success = setup_submission_bucket()
    
    if success:
        setup_storage_policies()
        print("\n🎉 Setup completed! Your submission system is ready to use.")
    else:
        print("\n❌ Setup failed. Please check your Supabase configuration.")
        sys.exit(1)