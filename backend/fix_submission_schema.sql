-- Quick fix for submission table schema (user_id -> submitter_id)
-- For complete schema migration, use fix_complete_submission_schema.sql instead

-- First, let's see what we have
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'submissions' 
ORDER BY ordinal_position;

-- Fix the column name if needed
DO $$
BEGIN
    -- Check if submissions table has user_id column (old schema)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'user_id'
    ) THEN
        -- Rename user_id to submitter_id
        ALTER TABLE submissions RENAME COLUMN user_id TO submitter_id;
        RAISE NOTICE 'Renamed user_id to submitter_id in submissions table';
    ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'submitter_id'
    ) THEN
        -- Neither column exists, something is wrong
        RAISE EXCEPTION 'submissions table exists but has neither user_id nor submitter_id column';
    ELSE
        RAISE NOTICE 'submissions table already has submitter_id column - no changes needed';
    END IF;
    
    -- Also add reviewer_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'reviewer_id'
    ) THEN
        ALTER TABLE submissions ADD COLUMN reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_submissions_reviewer_id ON submissions(reviewer_id);
        RAISE NOTICE 'Added reviewer_id column to submissions table';
    END IF;
END
$$;