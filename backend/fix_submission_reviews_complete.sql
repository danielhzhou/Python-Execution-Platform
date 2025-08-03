-- Complete fix for submission_reviews table to match the SQLModel
-- This ensures all columns exist and have the correct names

DO $$
BEGIN
    -- Create the table if it doesn't exist
    CREATE TABLE IF NOT EXISTS submission_reviews (
        id TEXT PRIMARY KEY,
        submission_id TEXT NOT NULL,
        reviewer_id TEXT NOT NULL,
        status TEXT NOT NULL,
        comment TEXT,
        file_path TEXT,
        line_number INTEGER,
        is_resolved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Add missing columns if they don't exist
    
    -- Fix comment column (rename from comments if it exists)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'comments'
    ) THEN
        ALTER TABLE submission_reviews RENAME COLUMN comments TO comment;
        RAISE NOTICE 'Renamed comments column to comment';
    END IF;
    
    -- Add comment column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'comment'
    ) THEN
        ALTER TABLE submission_reviews ADD COLUMN comment TEXT;
        RAISE NOTICE 'Added comment column';
    END IF;

    -- Add file_path column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'file_path'
    ) THEN
        ALTER TABLE submission_reviews ADD COLUMN file_path TEXT;
        RAISE NOTICE 'Added file_path column';
    END IF;

    -- Add line_number column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'line_number'
    ) THEN
        ALTER TABLE submission_reviews ADD COLUMN line_number INTEGER;
        RAISE NOTICE 'Added line_number column';
    END IF;

    -- Add is_resolved column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'is_resolved'
    ) THEN
        ALTER TABLE submission_reviews ADD COLUMN is_resolved BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added is_resolved column';
    END IF;

    -- Add updated_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE submission_reviews ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        RAISE NOTICE 'Added updated_at column';
    END IF;

    -- Add foreign key constraints if they don't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'submission_reviews' 
        AND constraint_name = 'submission_reviews_submission_id_fkey'
    ) THEN
        ALTER TABLE submission_reviews 
        ADD CONSTRAINT submission_reviews_submission_id_fkey 
        FOREIGN KEY (submission_id) REFERENCES submissions(id);
        RAISE NOTICE 'Added submission_id foreign key constraint';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'submission_reviews' 
        AND constraint_name = 'submission_reviews_reviewer_id_fkey'
    ) THEN
        ALTER TABLE submission_reviews 
        ADD CONSTRAINT submission_reviews_reviewer_id_fkey 
        FOREIGN KEY (reviewer_id) REFERENCES users(id);
        RAISE NOTICE 'Added reviewer_id foreign key constraint';
    END IF;

    -- Add indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_submission_reviews_submission_id ON submission_reviews(submission_id);
    CREATE INDEX IF NOT EXISTS idx_submission_reviews_reviewer_id ON submission_reviews(reviewer_id);
    CREATE INDEX IF NOT EXISTS idx_submission_reviews_status ON submission_reviews(status);

    RAISE NOTICE 'submission_reviews table schema is now complete and matches SQLModel';
END $$;