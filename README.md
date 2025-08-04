# Python Execution Platform

A browser-based IDE for Python code execution with Docker sandboxing and submission review workflow.

## Features

- **Code Editor**: Monaco editor with Python syntax highlighting
- **Terminal**: Real-time terminal with Docker container execution
- **File Management**: Create, edit, and save Python files
- **Docker Sandboxing**: Isolated Python 3.11 containers for code execution
- **Submission System**: Submit code for review with approval/rejection workflow
- **Role-based Access**: Separate interfaces for submitters and reviewers

## Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui + Monaco + xterm.js
- **Backend**: FastAPI + SQLModel + WebSockets
- **Database**: Supabase Postgres + Auth
- **Sandbox**: Docker python:3.11-slim containers
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Supabase account

### 1. Clone and Setup
```bash
git clone <repository-url>
cd python-execution-platform
cp env.example .env
# Edit .env with your Supabase credentials
```

### 2. Environment Configuration
Update `.env` with your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
DATABASE_URL=your-supabase-postgres-url
JWT_SECRET=your-secret-key
```

### 3. Start Development
```bash
# Install dependencies
cd frontend && bun i
cd ../backend && pip install -r requirements.txt

# Start backend
cd backend && ./backend.sh

# Start frontend (in another terminal)
cd frontend && ./frontend.sh
```

## User Roles

### Submitters
- Access to full IDE interface
- Can create and edit Python files
- Execute code in isolated Docker containers
- Submit projects for review

### Reviewers/Admins
- Access to review dashboard
- Can approve or reject submissions with comments
- View all submitted projects
- Download submission files

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout

### Containers
- `POST /api/containers/` - Create container
- `GET /api/containers/` - List containers
- `DELETE /api/containers/{id}` - Delete container

### Files
- `GET /api/containers/{id}/files` - List files
- `GET /api/containers/{id}/files/content` - Get file content
- `POST /api/containers/{id}/files` - Save file

### Submissions
- `POST /api/submissions/` - Create submission
- `GET /api/submissions/` - List pending submissions
- `GET /api/submissions/approved` - List approved submissions
- `GET /api/submissions/rejected` - List rejected submissions
- `POST /api/submissions/{id}/review` - Review submission

### WebSocket
- `/api/ws/{session_id}` - Terminal WebSocket connection

## Project Structure

```
python-execution-platform/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── lib/             # API client and utilities
│   │   ├── stores/          # Zustand state management
│   │   └── types/           # TypeScript definitions
│   └── package.json
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Configuration and auth
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utilities
│   ├── tests/               # Test suite
│   └── requirements.txt
├── docker/                  # Docker configurations
├── docker-compose.yml       # Orchestration
└── README.md
```

## Security Features

- Docker containers run as non-root user
- Network isolation with controlled package installation
- Input validation and sanitization
- Resource limits (1 vCPU, 512MB RAM per container)
- Secure authentication with Supabase
