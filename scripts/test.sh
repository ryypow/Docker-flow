#!/bin/bash
set -e

echo "🚀 Running DockerFlow Test Suite"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "ANTHROPIC_API_KEY=test-key-for-ci" >> .env
fi

print_status "Building Docker image..."
docker compose build

print_status "Starting services..."
docker compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Test health endpoint
print_status "Testing health endpoint..."
if curl -f http://localhost:5002/health > /dev/null 2>&1; then
    print_success "Health endpoint is responding"
else
    print_error "Health endpoint is not responding"
    docker compose logs
    exit 1
fi

# Test web UI
print_status "Testing web UI..."
if curl -f http://localhost:5000 > /dev/null 2>&1; then
    print_success "Web UI is accessible"
else
    print_error "Web UI is not accessible"
    exit 1
fi

# Test WebSocket endpoint
print_status "Testing WebSocket endpoint..."
if curl -f http://localhost:5001 > /dev/null 2>&1; then
    print_success "WebSocket endpoint is accessible"
else
    print_warning "WebSocket endpoint test skipped (requires special client)"
fi

# Test terminal endpoint
print_status "Testing terminal endpoint..."
if curl -f http://localhost:7681 > /dev/null 2>&1; then
    print_success "Terminal endpoint is accessible"
else
    print_error "Terminal endpoint is not accessible"
    exit 1
fi

# Run Python tests
print_status "Running Python unit tests..."
docker compose exec -T dockerflow python -m pytest tests/ -v || {
    print_error "Python tests failed"
    exit 1
}

print_success "All tests passed!"

# Cleanup
print_status "Cleaning up..."
docker compose down

print_success "Test suite completed successfully! ✅"