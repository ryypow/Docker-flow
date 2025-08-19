#!/bin/bash
set -e

# Initialize environment
export HOME=/home/dockerflow
export PATH="$PATH:/app/bin:/home/dockerflow/.local/bin"

# Function to check if port is available
check_port() {
    nc -z localhost $1 2>/dev/null
    return $?
}

# Start services with error handling
echo "🚀 Starting DockerFlow services..."

# Create necessary directories (with proper error handling)
mkdir -p /workspace/.claude /workspace/.cache 2>/dev/null || true

# Start FastAPI servers in background
echo "📡 Starting API server on port 5002..."
python3 /app/server/main.py &
API_PID=$!

echo "🔌 Starting WebSocket server on port 5001..."
python3 /app/server/ws.py &
WS_PID=$!

echo "🎨 Starting UI server on port 5000..."
python3 /app/server/ui.py &
UI_PID=$!

# Start terminal service if available
if command -v ttyd &> /dev/null; then
    echo "💻 Starting terminal service on port 7681..."
    ttyd -p 7681 -c dockerflow:dockerflow bash &
    TTYD_PID=$!
fi

# Wait for services to start
sleep 3

# Verify services are running
echo ""
echo "✅ DockerFlow is ready!"
echo ""
echo "🌐 Access points:"
echo "   UI:       http://localhost:5000"
echo "   Terminal: http://localhost:7681"
echo "   API:      http://localhost:5002"
echo "   WebSocket: ws://localhost:5001"
echo ""
echo "📚 Quick commands:"
echo "   npx claude-flow --help     # Claude-Flow help"
echo "   npx claude-flow sparc modes # List SPARC modes"
echo "   cf scan                     # Scan project (alias)"
echo ""
echo "💡 Tips:"
echo "   - Your workspace is mounted at /workspace"
echo "   - API keys are loaded from .env file"
echo "   - Use 'docker exec -it dockerflow bash' for CLI access"
echo ""

# Function to handle shutdown
cleanup() {
    echo "Shutting down DockerFlow services..."
    kill $API_PID $WS_PID $UI_PID 2>/dev/null || true
    if [ ! -z "$TTYD_PID" ]; then
        kill $TTYD_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Keep container running and monitor services
while true; do
    # Check if main services are still running
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "API server died, restarting..."
        python3 /app/server/main.py &
        API_PID=$!
    fi
    
    if ! kill -0 $WS_PID 2>/dev/null; then
        echo "WebSocket server died, restarting..."
        python3 /app/server/ws.py &
        WS_PID=$!
    fi
    
    if ! kill -0 $UI_PID 2>/dev/null; then
        echo "UI server died, restarting..."
        python3 /app/server/ui.py &
        UI_PID=$!
    fi
    
    sleep 30
done