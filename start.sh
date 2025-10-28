#!/bin/bash

# Tom Storytelling - Docker Quick Start Script

echo "🚀 Starting Tom Storytelling Application..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please create .env file from .env.example"
    echo "   cp .env.example .env"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker Desktop"
    exit 1
fi

# Build and start containers
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting containers..."
docker-compose up -d

echo "✅ Application started successfully!"
echo "📍 API available at: http://localhost:8000"
echo "📖 API docs at: http://localhost:8000/docs"
echo "🏥 Health check: http://localhost:8000/health"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop app: docker-compose down"
