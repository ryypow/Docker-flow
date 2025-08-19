#!/bin/bash
set -e

echo "🚀 DockerFlow Setup Script"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Prerequisites check passed!"

# Setup environment file
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please edit .env file and add your API keys before running DockerFlow"
    echo "Required variables:"
    echo "  - ANTHROPIC_API_KEY: Your Anthropic API key"
    echo "Optional variables:"
    echo "  - OPENAI_API_KEY: Your OpenAI API key"
    echo "  - HF_TOKEN: Your Hugging Face token"
else
    print_status ".env file already exists"
fi

# Build the Docker image
print_status "Building Docker image..."
docker compose build

print_success "DockerFlow setup completed! 🎉"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: docker compose up -d"
echo "3. Open: http://localhost:5000"
echo ""
echo "For more information, see README.md"