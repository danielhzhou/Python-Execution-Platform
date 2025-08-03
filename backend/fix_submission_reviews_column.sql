-- Fix submission_reviews table column name from 'comments' to 'comment'
-- This fixes the mismatch between database and SQLModel

-- Check if 'comments' column exists and rename it to 'comment'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_reviews' 
        AND column_name = 'comments'
    ) THEN
        ALTER TABLE submission_reviews RENAME COLUMN comments TO comment;
        RAISE NOTICE 'Renamed comments column to comment in submission_reviews table';
    ELSE
        -- If comments doesn't exist, check if comment exists
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'submission_reviews' 
            AND column_name = 'comment'
        ) THEN
            -- Add comment column if neither exists
            ALTER TABLE submission_reviews ADD COLUMN comment TEXT;
            RAISE NOTICE 'Added comment column to submission_reviews table';
        ELSE
            RAISE NOTICE 'comment column already exists in submission_reviews table';
        END IF;
    END IF;
END $$;