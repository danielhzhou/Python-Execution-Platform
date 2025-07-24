#!/bin/bash

# Python Execution Platform - Test Runner
# Usage: ./run_tests.sh [test_type]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Python Execution Platform - Test Runner${NC}"
echo -e "${BLUE}============================================${NC}"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${RED}❌ Virtual environment not found. Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Set Python path
export PYTHONPATH=.

# Determine test type
TEST_TYPE=${1:-"unit"}

case $TEST_TYPE in
    "unit")
        echo -e "${GREEN}🔬 Running Unit Tests (Core Business Logic)${NC}"
        echo -e "${YELLOW}These tests verify that all core services work correctly${NC}"
        echo ""
        PYTHONPATH=. pytest tests/test_container_service.py tests/test_terminal_service.py tests/test_websocket_service.py -m "unit" --tb=short -v
        ;;
    "api")
        echo -e "${GREEN}🌐 Running API Integration Tests${NC}"
        echo -e "${YELLOW}Note: Some may fail - this is expected for incomplete API routes${NC}"
        echo ""
        PYTHONPATH=. pytest tests/test_api_endpoints.py -m "unit" --tb=short -v
        ;;
    "all")
        echo -e "${GREEN}🚀 Running All Tests${NC}"
        echo -e "${YELLOW}Note: API integration tests may fail - this is expected${NC}"
        echo ""
        PYTHONPATH=. pytest -m "unit" --tb=short
        ;;
    "integration")
        echo -e "${GREEN}🐳 Running Integration Tests (Requires Docker)${NC}"
        echo -e "${YELLOW}These tests require Docker to be running${NC}"
        echo ""
        PYTHONPATH=. pytest -m "integration" --tb=short -v
        ;;
    "help")
        echo -e "${GREEN}Available test types:${NC}"
        echo -e "  ${YELLOW}unit${NC}        - Core business logic tests (recommended)"
        echo -e "  ${YELLOW}api${NC}         - API endpoint tests"
        echo -e "  ${YELLOW}integration${NC} - Docker integration tests"
        echo -e "  ${YELLOW}all${NC}         - All unit tests"
        echo -e "  ${YELLOW}help${NC}        - Show this help"
        echo ""
        echo -e "${GREEN}Examples:${NC}"
        echo -e "  ./run_tests.sh unit"
        echo -e "  ./run_tests.sh api"
        echo -e "  ./run_tests.sh integration"
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        echo -e "Run './run_tests.sh help' for available options"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}✅ Test run complete!${NC}" 