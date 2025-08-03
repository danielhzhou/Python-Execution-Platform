-- Complete submission system schema migration
-- Run this in your Supabase SQL Editor to fix all schema issues

-- First, let's see what we have
SELECT 'Current submissions table columns:' as info;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'submissions' 
ORDER BY ordinal_position;

-- Fix the submissions table schema
DO $$
BEGIN
    -- Ensure submissions table exists
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'submissions') THEN
        -- Create the table with correct schema
        CREATE TABLE submissions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            submitter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            storage_path TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            submitted_at TIMESTAMPTZ,
            reviewed_at TIMESTAMPTZ,
            reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL
        );
        RAISE NOTICE 'Created submissions table with correct schema';
    ELSE
        -- Table exists, fix columns one by one
        
        -- Fix user_id -> submitter_id
        IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'user_id') THEN
            ALTER TABLE submissions RENAME COLUMN user_id TO submitter_id;
            RAISE NOTICE 'Renamed user_id to submitter_id';
        ELSIF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'submitter_id') THEN
            ALTER TABLE submissions ADD COLUMN submitter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE;
            RAISE NOTICE 'Added submitter_id column';
        END IF;
        
        -- Add missing columns
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'storage_path') THEN
            ALTER TABLE submissions ADD COLUMN storage_path TEXT;
            RAISE NOTICE 'Added storage_path column';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'reviewed_at') THEN
            ALTER TABLE submissions ADD COLUMN reviewed_at TIMESTAMPTZ;
            RAISE NOTICE 'Added reviewed_at column';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'reviewer_id') THEN
            ALTER TABLE submissions ADD COLUMN reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL;
            RAISE NOTICE 'Added reviewer_id column';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submissions' AND column_name = 'updated_at') THEN
            ALTER TABLE submissions ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added updated_at column';
        END IF;
    END IF;
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_submissions_submitter_id ON submissions(submitter_id);
    CREATE INDEX IF NOT EXISTS idx_submissions_project_id ON submissions(project_id);
    CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
    CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at);
    CREATE INDEX IF NOT EXISTS idx_submissions_reviewer_id ON submissions(reviewer_id);
    
    RAISE NOTICE 'Submissions table schema is now up to date';
END
$$;

-- Fix submission_files table
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'submission_files') THEN
        CREATE TABLE submission_files (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            content TEXT,
            storage_path TEXT,
            file_size INTEGER,
            mime_type TEXT,
            diff_content TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        RAISE NOTICE 'Created submission_files table';
    ELSE
        -- Add missing columns to submission_files
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submission_files' AND column_name = 'storage_path') THEN
            ALTER TABLE submission_files ADD COLUMN storage_path TEXT;
            RAISE NOTICE 'Added storage_path to submission_files';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submission_files' AND column_name = 'file_size') THEN
            ALTER TABLE submission_files ADD COLUMN file_size INTEGER;
            RAISE NOTICE 'Added file_size to submission_files';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submission_files' AND column_name = 'mime_type') THEN
            ALTER TABLE submission_files ADD COLUMN mime_type TEXT;
            RAISE NOTICE 'Added mime_type to submission_files';
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submission_files' AND column_name = 'diff_content') THEN
            ALTER TABLE submission_files ADD COLUMN diff_content TEXT;
            RAISE NOTICE 'Added diff_content to submission_files';
        END IF;
    END IF;
    
    -- Create indexes for submission_files
    CREATE INDEX IF NOT EXISTS idx_submission_files_submission_id ON submission_files(submission_id);
    CREATE INDEX IF NOT EXISTS idx_submission_files_file_path ON submission_files(file_path);
END
$$;

-- Fix submission_reviews table
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'submission_reviews') THEN
        CREATE TABLE submission_reviews (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            comment TEXT,
            file_path TEXT,
            line_number INTEGER,
            is_resolved BOOLEAN DEFAULT FALSE,
            reviewed_at TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        RAISE NOTICE 'Created submission_reviews table';
    ELSE
        -- Add missing columns to submission_reviews
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'submission_reviews' AND column_name = 'updated_at') THEN
            ALTER TABLE submission_reviews ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added updated_at to submission_reviews';
        END IF;
    END IF;
    
    -- Create indexes for submission_reviews
    CREATE INDEX IF NOT EXISTS idx_submission_reviews_submission_id ON submission_reviews(submission_id);
    CREATE INDEX IF NOT EXISTS idx_submission_reviews_reviewer_id ON submission_reviews(reviewer_id);
END
$$;

-- Add role column to users table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'role') THEN
        ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'submitter';
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        RAISE NOTICE 'Added role column to users table';
    END IF;
END
$$;

-- Final verification
SELECT 'Final submissions table schema:' as info;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'submissions' 
ORDER BY ordinal_position;