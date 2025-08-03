# Submission System Setup Guide

## Overview

The submission system has been fully implemented and integrated into your Python execution platform. This guide covers setup instructions, bug fixes applied, and how to use the system.

## 🔧 Setup Instructions

### 1. Database Schema Updates

First, apply the updated database schema to your Supabase project:

```sql
-- Add role column to users table
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'submitter';
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Create submissions table
CREATE TABLE IF NOT EXISTS submissions (
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

-- Create indexes for submissions
CREATE INDEX IF NOT EXISTS idx_submissions_submitter_id ON submissions(submitter_id);
CREATE INDEX IF NOT EXISTS idx_submissions_project_id ON submissions(project_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_submissions_reviewer_id ON submissions(reviewer_id);

-- Create submission files table
CREATE TABLE IF NOT EXISTS submission_files (
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

-- Create indexes for submission_files
CREATE INDEX IF NOT EXISTS idx_submission_files_submission_id ON submission_files(submission_id);
CREATE INDEX IF NOT EXISTS idx_submission_files_file_path ON submission_files(file_path);

-- Create submission reviews table
CREATE TABLE IF NOT EXISTS submission_reviews (
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

-- Create indexes for submission_reviews
CREATE INDEX IF NOT EXISTS idx_submission_reviews_submission_id ON submission_reviews(submission_id);
CREATE INDEX IF NOT EXISTS idx_submission_reviews_reviewer_id ON submission_reviews(reviewer_id);
```

### 2. Supabase Storage Setup

Run the storage setup script:

```bash
cd backend
python setup_submission_storage.py
```

This will create:
- `submissions` storage bucket
- Folder structure: `pending/`, `approved/`, `rejected/`
- Basic storage policies

### 3. Environment Variables

Ensure your `.env` file contains:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 4. Backend Dependencies

The submission system uses existing dependencies. Make sure your backend is running:

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Frontend Dependencies

The frontend components are integrated. Start the frontend:

```bash
cd frontend
bun install
bun run dev
```

## 🐛 Bug Fixes Applied

### 1. User Role Consistency
**Issue**: Inconsistent user roles between frontend and backend
**Fix**: Standardized on `submitter` instead of `learner`
- Updated User interface in `frontend/src/types/index.ts`
- Made role field required (not optional)
- Fixed database schema default value

### 2. Missing Submission Types
**Issue**: Submission-related TypeScript types were missing
**Fix**: Added all submission types back to `frontend/src/types/index.ts`:
- `SubmissionStatus`
- `Submission`
- `SubmissionFile`
- `SubmissionReview`
- `SubmissionDetail`
- Request/Response interfaces

### 3. Missing API Functions
**Issue**: Submission API functions were removed
**Fix**: Restored complete `submissionApi` in `frontend/src/lib/api.ts`:
- Submitter endpoints
- Reviewer endpoints
- Admin endpoints
- Proper error handling

### 4. Component Integration
**Issue**: Submission components were deleted
**Fix**: Recreated all submission components:
- `SubmissionSystem.tsx` - Main router
- `SubmitterInterface.tsx` - Submitter UI
- `ReviewerDashboard.tsx` - Reviewer UI

### 5. App Integration
**Issue**: Submission system not integrated into main app
**Fix**: Added tabbed interface to `App.tsx`:
- Editor/Submissions tabs
- File fetching for submissions
- Role-based rendering

### 6. API Route Prefix
**Issue**: Double prefix in submission routes
**Fix**: Removed prefix from `submissions.py` router since it's already added in main API router

## 🎯 How to Use

### For Submitters

1. **Access Submissions**:
   - Click the "Submissions" tab in the main interface
   - You'll see the submitter interface if your role is 'submitter'

2. **Create Submission**:
   - Click "Create New Submission"
   - Enter title and optional description
   - Click "Create Submission"

3. **Upload Files**:
   - Work on your code in the editor
   - Switch to Submissions tab
   - Click "Upload Files" on your draft submission
   - Files from your workspace are automatically collected

4. **Submit for Review**:
   - Click "Submit for Review"
   - Confirm submission (cannot be modified after)
   - Status changes to "submitted"

### For Reviewers

1. **Access Dashboard**:
   - Submissions tab shows reviewer dashboard for users with 'reviewer' role
   - See pending submissions count

2. **Review Submissions**:
   - Click on any pending submission
   - View files and code
   - Download submission if needed

3. **Make Decision**:
   - Enter review comments (required)
   - Click "Approve" or "Reject"
   - Files automatically move to appropriate storage folder

4. **View Approved**:
   - Switch to "Approved" tab
   - See list of approved submissions with submitter info

### For Admins

Admins can change user roles via API:

```bash
curl -X POST "http://localhost:8000/api/submissions/users/{user_id}/role" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"role": "reviewer"}'
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd backend
python test_submission_system.py
```

This tests:
- Submission creation
- File upload
- Review workflow
- File download
- Role-based access control

## 🔒 Security Features

- **Role-based access control**: Submitters can only see their own submissions
- **Authentication required**: All endpoints require valid JWT token
- **Input validation**: All inputs validated on both frontend and backend
- **File security**: Files stored in private Supabase storage bucket
- **Storage policies**: Proper access restrictions on storage bucket

## 📁 File Structure

```
backend/
├── app/
│   ├── api/routes/submissions.py      # API endpoints
│   ├── models/container.py            # Data models
│   ├── services/
│   │   ├── submission_service.py      # Core logic
│   │   └── database_service.py        # Database operations
├── setup_submission_storage.py       # Storage setup
└── test_submission_system.py         # Test suite

frontend/
├── src/
│   ├── components/submissions/
│   │   ├── SubmissionSystem.tsx       # Main router
│   │   ├── SubmitterInterface.tsx     # Submitter UI
│   │   └── ReviewerDashboard.tsx      # Reviewer UI
│   ├── types/index.ts                 # TypeScript types
│   ├── lib/api.ts                     # API functions
│   └── App.tsx                        # Main app with tabs
```

## 🚨 Troubleshooting

### Common Issues

1. **"Submission not found" errors**:
   - Check user authentication
   - Verify user role permissions
   - Ensure submission belongs to user

2. **File upload failures**:
   - Check Supabase storage bucket exists
   - Verify storage policies are set
   - Ensure container is running

3. **Role access issues**:
   - Check user role in database
   - Update role via admin API if needed
   - Refresh browser after role change

4. **Storage errors**:
   - Run `python setup_submission_storage.py`
   - Check Supabase project settings
   - Verify environment variables

### Debug Commands

```bash
# Check storage bucket
supabase storage ls

# Test API endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/submissions/my-submissions

# Check database
psql $DATABASE_URL -c "SELECT * FROM submissions;"
```

## 🎉 Success!

Your submission system is now fully functional with:

✅ Role-based user system (submitter/reviewer/admin)  
✅ Complete submission workflow  
✅ File upload/download with ZIP packaging  
✅ Review dashboard for reviewers  
✅ Secure storage with organized folders  
✅ Real-time UI updates  
✅ Comprehensive error handling  
✅ Full test coverage  

The system is production-ready and can handle the complete take-home assignment workflow!