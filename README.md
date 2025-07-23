# Python Execution Platform

A secure browser-based IDE for Python code execution with integrated terminal, Docker sandboxing, and review workflow.

## 🏗️ Architecture

```
Browser ──HTTPS/WebSocket──▶ FastAPI Backend
                              │
                              └── Docker Exec → Sandbox Container (python:3.11)
                              │
                              └── Supabase Postgres (remote)
```

### Tech Stack
- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui + xterm.js + Monaco
- **Backend**: FastAPI + SQLModel + WebSockets  
- **Database**: Supabase Postgres + Auth
- **Sandbox**: Docker python:3.11-slim (rootless)
- **Package Manager**: Bun
- **Deployment**: Single VM with Docker Compose

## 🚀 Quick Start

### Prerequisites
- [Bun](https://bun.sh/) (latest version)
- [Docker](https://www.docker.com/) and Docker Compose
- [Python 3.11+](https://www.python.org/)
- [Supabase](https://supabase.com/) account

### 1. Clone and Setup
```bash
git clone <repository-url>
cd python-execution-platform

# Copy environment template
cp env.example .env
# Edit .env with your configuration
```

### 2. Install Dependencies
```bash
# Install frontend dependencies
bun run install:frontend

# Install backend dependencies  
bun run install:backend
```

### 3. Configure Environment
Update `.env` with your Supabase credentials:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/python_platform
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
JWT_SECRET=your-super-secret-jwt-key
```

### 4. Start Development
```bash
# Start all services with Docker Compose
bun run dev

# Or start services individually:
bun run dev:frontend  # Frontend on :3000
bun run dev:backend   # Backend on :8000
```

## 📁 Project Structure

```
python-execution-platform/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   │   ├── ui/          # shadcn/ui components
│   │   │   ├── editor/      # Monaco editor
│   │   │   ├── terminal/    # xterm.js terminal
│   │   │   └── common/      # Shared components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # Utility functions
│   │   ├── stores/          # Zustand stores
│   │   ├── types/           # TypeScript definitions
│   │   └── utils/           # Helper functions
│   ├── package.json
│   └── index.ts             # Bun server entry point
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Core functionality
│   │   ├── models/          # SQLModel models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utility functions
│   ├── tests/               # Backend tests
│   └── requirements.txt
├── docker/                  # Docker configurations
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── Dockerfile.sandbox
├── docker-compose.yml       # Orchestration
├── CLAUDE.md               # AI assistant instructions
└── README.md
```

## 🔧 Development

### Available Scripts

**Root Level:**
- `bun run dev` - Start all services with Docker Compose
- `bun run build` - Build all Docker images
- `bun run test` - Run all tests
- `bun run lint` - Run linting
- `bun run clean` - Clean up Docker containers and volumes

**Frontend:**
- `bun run dev:frontend` - Start frontend development server
- `bun run test:frontend` - Run frontend tests
- `bun run lint:frontend` - Lint frontend code

**Backend:**
- `bun run dev:backend` - Start backend development server
- `bun run test:backend` - Run backend tests

### Key Features

#### 🖥️ Code Editor (Monaco)
- Python syntax highlighting and IntelliSense
- File tree navigation
- Auto-save functionality
- Undo/redo history
- Find and replace

#### 🖲️ Integrated Terminal (xterm.js)
- Real-time character echo (<50ms latency)
- Full shell command support
- ANSI escape sequence handling
- Command history

#### 🐳 Docker Sandbox Security
- Containers start with `--network=none`
- Resource limits: 1 vCPU, 512MB RAM
- Rootless execution
- Network access only for package installation

#### 📦 Package Installation Strategy
```bash
# Default: No network access
docker run --network=none python:3.11-slim

# On pip install detection:
docker network connect pypi-net $CONTAINER_ID
# Install packages (only PyPI domains whitelisted)  
docker network disconnect pypi-net $CONTAINER_ID
```

#### 💾 Persistence Layer
- Auto-save files to Supabase Postgres
- Restore last session state on login
- Version control for submissions

#### 👥 Review Workflow
- Submit button for learners
- Diff visualization for reviewers
- Comment system
- Approve/reject functionality

## 🔒 Security

### Container Security
- Run as non-root user (UID 1000)
- Resource limits enforced
- Network isolation by default
- Whitelist only PyPI domains during installation
- Monitor and log all container activities

### Input Validation
- Sanitize all user inputs
- Validate file paths and names
- Escape terminal output before display
- Rate limit API endpoints

### Authentication & Authorization
- Supabase Auth with magic links
- Role-based access control (learner/reviewer)
- Secure API endpoints

## 📊 Performance Targets

- **Cold start**: Sandbox ≤ 1.5s
- **Character echo**: p95 ≤ 80ms
- **File operations**: < 200ms
- **Package installation**: < 30s
- **Overall uptime**: ≥ 99%

## 🧪 Testing

### Running Tests
```bash
# All tests
bun run test

# Frontend tests only
bun run test:frontend

# Backend tests only  
bun run test:backend
```

### Test Strategy
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Mock external dependencies
- Maintain 80%+ coverage

## 🚢 Deployment

### Docker Compose (Production)
```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables
See `env.example` for all required environment variables.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and type checking
6. Submit a pull request

### Code Quality Standards
- Use TypeScript strict mode
- Follow ESLint configuration
- Write tests for new features
- Use conventional commits
- Maintain proper error handling

## 📝 Success Metrics

The platform should achieve:
- Users can type `print('hi')` and run `python main.py` within 2 seconds of login
- `pip install seaborn` succeeds and network is immediately isolated
- Reviewers can see diffs and approve/reject submissions
- All code passes linting, type checking, and tests
- Security vulnerabilities are minimized through proper sandboxing

## 🆘 Troubleshooting

### Common Issues

**WebSocket Connection Issues:**
- Check CORS configuration
- Verify authentication tokens
- Monitor connection state in UI

**Container Management Issues:**
- Ensure Docker daemon is running
- Check resource limits and availability
- Monitor container health

**Performance Issues:**
- Profile database queries
- Optimize bundle sizes
- Monitor resource usage

## 📄 License

[Add your license here]

## 🙋‍♂️ Support

For questions and support, please [open an issue](https://github.com/your-repo/issues).
