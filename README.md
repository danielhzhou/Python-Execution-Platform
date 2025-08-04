# Python Execution Platform

A secure browser-based IDE for Python code execution with integrated terminal, Docker sandboxing, and submission review workflow.

## Features

- **🖥️ Browser-based IDE**: Monaco editor with Python syntax highlighting
- **🐳 Docker Sandboxing**: Isolated Python 3.11 containers for secure code execution
- **💻 Integrated Terminal**: Real-time terminal with full Python environment
- **📁 File Management**: Create, edit, and organize Python files
- **🔄 Auto-save**: Automatic file saving as you type
- **👥 Role-based Access**: Separate interfaces for submitters and reviewers
- **📋 Submission System**: Submit code for review with approval/rejection workflow
- **💾 Persistent Storage**: Files saved to Supabase Storage
- **🔒 Secure**: Network isolation, resource limits, and proper authentication

## Architecture

```
Browser ──HTTPS/WebSocket──▶ FastAPI Backend
                              │
                              ├── Docker Containers (Python 3.11)
                              │
                              ├── Supabase Postgres (Database + Auth)
                              │
                              └── Supabase Storage (File Persistence)
```

## Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui + Monaco + xterm.js
- **Backend**: FastAPI + SQLModel + WebSockets
- **Database**: Supabase Postgres + Authentication
- **Containers**: Docker with python:3.11-slim
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Node.js 18+](https://nodejs.org/) or [Bun](https://bun.sh/)
- [Python 3.11+](https://www.python.org/)
- [Supabase](https://supabase.com/) account

### 1. Clone and Setup

```bash
git clone <repository-url>
cd python-execution-platform

# Copy environment template
cp env.example .env
# Edit .env with your Supabase credentials
```

### 2. Configure Environment

Update `.env` with your Supabase credentials:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/python_platform
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
JWT_SECRET=your-super-secret-jwt-key
```

### 3. Start Development

```bash
# Install dependencies
cd frontend && bun install
cd ../backend 
python -m venv venv


# Start backend
cd backend && ./backend.sh

# Start frontend (in another terminal)
cd frontend && ./frontend.sh
```


## User Roles

### Submitters
- Access to full IDE interface
- Can create, edit, and run Python files
- Can submit code for review
- Automatic Docker container creation

### Reviewers/Admins
- Access to review dashboard
- Can approve or reject submissions with comments
- View approved and rejected submissions
- No Docker containers created (review-only access)

## Project Structure

```
python-execution-platform/
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── editor/        # Monaco editor components
│   │   │   ├── terminal/      # xterm.js terminal
│   │   │   ├── submissions/   # Review system
│   │   │   └── layout/        # File tree, header
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # Zustand state management
│   │   └── lib/               # API client and utilities
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── services/          # Business logic
│   │   ├── models/            # Database models
│   │   └── core/              # Configuration
│   └── tests/                 # Test suite
├── docker/                    # Docker configurations
└── docker-compose.yml        # Orchestration
```

## API Endpoints

### Containers
- `POST /api/containers/` - Create container
- `GET /api/containers/` - List containers
- `DELETE /api/containers/{id}` - Delete container

### Files
- `GET /api/containers/{id}/files` - List files
- `POST /api/containers/{id}/files` - Save file
- `GET /api/containers/{id}/files/content` - Get file content

### Submissions
- `POST /api/submissions/` - Create submission
- `GET /api/submissions/pending` - Get pending reviews
- `GET /api/submissions/approved` - Get approved submissions
- `GET /api/submissions/rejected` - Get rejected submissions
- `POST /api/submissions/{id}/review` - Review submission

### WebSocket
- `/ws/{session_id}` - Real-time terminal communication

## Development

### Backend Development

```bash
cd backend

# create virtual environment
python -m venv venv

# Install dependencies
pip install -r requirements.txt

# start backend server
./backend.sh
```

### Frontend Development

```bash
cd frontend

# Install dependencies
bun i

# Start development server
./frontend.sh
```

## Security Features

- **Container Isolation**: Each user gets an isolated Docker container
- **Network Control**: Containers start with no network, enabled only for pip installs
- **Resource Limits**: 1 vCPU, 512MB RAM per container
- **Non-root Execution**: Containers run as unprivileged user
- **Input Validation**: All inputs validated on backend
- **Authentication**: Secure JWT-based authentication via Supabase


### Environment Variables

Required environment variables:
check .env.local

## Support

For questions and support, please [open an issue](https://github.com/your-repo/issues).