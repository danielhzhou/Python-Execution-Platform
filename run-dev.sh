#!/bin/bash

# Development script to run backend and frontend manually
# This script starts both services in parallel

set -e

echo "🚀 Starting Python Execution Platform Development Environment"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to kill processes on specific ports
cleanup_ports() {
    echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
    
    if port_in_use 8000; then
        echo -e "${YELLOW}  Killing process on port 8000 (backend)${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    fi
    
    if port_in_use 5173; then
        echo -e "${YELLOW}  Killing process on port 5173 (frontend)${NC}"
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    fi
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 is not installed${NC}"
        exit 1
    fi
    
    if ! command_exists node; then
        echo -e "${RED}❌ Node.js is not installed${NC}"
        exit 1
    fi
    
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites satisfied${NC}"
}

# Function to setup backend
setup_backend() {
    echo -e "${BLUE}🔧 Setting up backend...${NC}"
    
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}  Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install/upgrade dependencies
    echo -e "${YELLOW}  Installing dependencies...${NC}"
    pip install -q -r requirements.txt
    pip install -q pydantic[email]  # Fix for email validation
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}  Creating .env file...${NC}"
        cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./app.db

# Container settings
CONTAINER_IMAGE=python:3.11-slim
CONTAINER_MEMORY_LIMIT=512m
CONTAINER_CPU_LIMIT=1.0

# Terminal settings
TERMINAL_ROWS=24
TERMINAL_COLS=80

# Security
JWT_SECRET_KEY=dev-secret-key-change-in-production

# Development
DEBUG=true
ENVIRONMENT=development
EOF
        echo -e "${GREEN}  ✅ Created .env file with default settings${NC}"
    fi
    
    cd ..
    echo -e "${GREEN}✅ Backend setup complete${NC}"
}

# Function to setup frontend
setup_frontend() {
    echo -e "${BLUE}🔧 Setting up frontend...${NC}"
    
    cd frontend
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}  Installing dependencies...${NC}"
        if command_exists bun; then
            bun install
        else
            npm install
        fi
    fi
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}  Creating .env file...${NC}"
        cat > .env << EOF
VITE_API_URL=http://localhost:8000/api
EOF
        echo -e "${GREEN}  ✅ Created .env file${NC}"
    fi
    
    cd ..
    echo -e "${GREEN}✅ Frontend setup complete${NC}"
}

# Function to start backend
start_backend() {
    echo -e "${BLUE}🚀 Starting backend server...${NC}"
    cd backend
    source venv/bin/activate
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}🚀 Starting frontend server...${NC}"
    cd frontend
    if command_exists bun; then
        bun dev &
    else
        npm run dev &
    fi
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
}

# Function to wait for services
wait_for_services() {
    echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
    
    # Wait for backend
    echo -e "${YELLOW}  Waiting for backend (http://localhost:8000)...${NC}"
    timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}  ✅ Backend is ready${NC}"
            break
        fi
        sleep 1
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        echo -e "${RED}  ❌ Backend failed to start${NC}"
        exit 1
    fi
    
    # Wait for frontend
    echo -e "${YELLOW}  Waiting for frontend (http://localhost:5173)...${NC}"
    timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:5173 >/dev/null 2>&1; then
            echo -e "${GREEN}  ✅ Frontend is ready${NC}"
            break
        fi
        sleep 1
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        echo -e "${YELLOW}  ⚠️  Frontend might still be starting${NC}"
    fi
}

# Function to show status
show_status() {
    echo ""
    echo -e "${GREEN}🎉 Development environment is ready!${NC}"
    echo "=============================================="
    echo -e "${BLUE}📱 Frontend:${NC} http://localhost:5173"
    echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:8000"
    echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8000/docs"
    echo -e "${BLUE}💚 Health Check:${NC} http://localhost:8000/health"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
}

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    cleanup_ports
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Main execution
main() {
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    # Check if --clean flag is passed
    if [ "$1" = "--clean" ]; then
        cleanup_ports
        echo -e "${GREEN}✅ Ports cleaned up${NC}"
        exit 0
    fi
    
    # Run setup steps
    check_prerequisites
    cleanup_ports
    setup_backend
    setup_frontend
    
    # Start services
    start_backend
    sleep 3  # Give backend time to start
    start_frontend
    
    # Wait for services and show status
    wait_for_services
    show_status
    
    # Keep script running
    while true; do
        sleep 1
    done
}

# Run main function
main "$@" 