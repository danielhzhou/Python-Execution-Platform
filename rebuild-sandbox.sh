#!/bin/bash

echo "🏗️ Rebuilding sandbox container with Node.js optimizations..."

# Stop any running containers
echo "🛑 Stopping existing containers..."
docker stop $(docker ps -q --filter "ancestor=python-execution-platform-sandbox" 2>/dev/null) 2>/dev/null || true

# Remove old sandbox image
echo "🗑️ Removing old sandbox image..."
docker rmi python-execution-platform-sandbox 2>/dev/null || true

# Build new sandbox image
echo "🔨 Building new sandbox image..."
docker build -f docker/Dockerfile.sandbox -t python-execution-platform-sandbox .

if [ $? -eq 0 ]; then
    echo "✅ Sandbox container rebuilt successfully!"
    echo ""
    echo "🎯 New features:"
    echo "   • npm-safe - Optimized package installation"
    echo "   • npm-light - Production-only dependencies"
    echo "   • npm-clean - Clean up node_modules"
    echo "   • Automatic exclusion of large directories from file listings"
    echo "   • 30-second timeout protection for file operations"
    echo ""
    echo "📖 See NODE_JS_GUIDE.md for usage instructions"
else
    echo "❌ Failed to build sandbox container"
    exit 1
fi