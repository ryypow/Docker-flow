#!/bin/bash
# DockerFlow Integration Test Suite
# End-to-end testing of the entire DockerFlow system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
COMPOSE_FILE="docker-compose.yml"
TIMEOUT=60
RETRY_ATTEMPTS=3
RETRY_DELAY=5

# URLs
UI_URL="http://localhost:5000"
API_URL="http://localhost:5002"
WS_URL="ws://localhost:5001"
TERMINAL_URL="http://localhost:5003"
TTYD_URL="http://localhost:7681"

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

test_start() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log "Test $TESTS_TOTAL: $1"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    success "$1"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    error "$1"
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=${3:-20}
    
    log "Waiting for $name to be ready at $url..."
    
    for i in $(seq 1 $max_attempts); do
        if curl -s -f "$url" >/dev/null 2>&1; then
            success "$name is ready"
            return 0
        fi
        
        if [ $i -eq $max_attempts ]; then
            error "$name failed to start within timeout"
            return 1
        fi
        
        echo -n "."
        sleep 3
    done
}

check_docker_compose() {
    test_start "Check Docker Compose availability"
    
    if command -v docker-compose >/dev/null 2>&1; then
        test_pass "docker-compose is available"
        return 0
    elif docker compose version >/dev/null 2>&1; then
        test_pass "docker compose (v2) is available"
        return 0
    else
        test_fail "Neither docker-compose nor 'docker compose' is available"
        return 1
    fi
}

start_services() {
    test_start "Start DockerFlow services"
    
    log "Building and starting services..."
    
    # Try docker compose first (v2), then docker-compose (v1)
    if docker compose -f "$COMPOSE_FILE" up -d --build 2>/dev/null; then
        test_pass "Services started successfully with 'docker compose'"
        return 0
    elif docker-compose -f "$COMPOSE_FILE" up -d --build 2>/dev/null; then
        test_pass "Services started successfully with 'docker-compose'"
        return 0
    else
        test_fail "Failed to start services"
        return 1
    fi
}

test_ui_accessibility() {
    test_start "UI accessibility"
    
    if wait_for_service "$UI_URL" "UI Server" 20; then
        # Check if UI loads properly
        response=$(curl -s -o /dev/null -w "%{http_code}" "$UI_URL")
        if [ "$response" = "200" ]; then
            test_pass "UI is accessible and returns 200"
        else
            test_fail "UI returned HTTP $response instead of 200"
        fi
    else
        test_fail "UI server is not accessible"
    fi
}

test_api_endpoints() {
    test_start "API endpoints"
    
    if wait_for_service "$API_URL/health" "API Server" 20; then
        # Test root endpoint
        response=$(curl -s "$API_URL/" | jq -r '.name' 2>/dev/null)
        if [ "$response" = "DockerFlow API" ]; then
            test_pass "API root endpoint works"
        else
            test_fail "API root endpoint failed"
            return 1
        fi
        
        # Test health endpoint
        status=$(curl -s "$API_URL/health" | jq -r '.status' 2>/dev/null)
        if [ "$status" = "healthy" ]; then
            test_pass "API health endpoint works"
        else
            test_fail "API health endpoint failed"
        fi
        
        # Test status endpoint
        if curl -s -f "$API_URL/status" >/dev/null 2>&1; then
            test_pass "API status endpoint works"
        else
            test_fail "API status endpoint failed"
        fi
        
        # Test info endpoint
        if curl -s -f "$API_URL/info" >/dev/null 2>&1; then
            test_pass "API info endpoint works"
        else
            test_fail "API info endpoint failed"
        fi
        
        # Test commands endpoint
        if curl -s -f "$API_URL/commands" >/dev/null 2>&1; then
            test_pass "API commands endpoint works"
        else
            test_fail "API commands endpoint failed"
        fi
    else
        test_fail "API server is not accessible"
    fi
}

test_command_execution() {
    test_start "Command execution via API"
    
    # Test basic command
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"echo \"Integration Test\"","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        output=$(echo "$response" | jq -r '.output')
        if echo "$output" | grep -q "Integration Test"; then
            test_pass "Command execution works"
        else
            test_fail "Command execution output incorrect"
        fi
    else
        test_fail "Command execution failed"
    fi
    
    # Test Node.js availability
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"node --version","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        test_pass "Node.js is available"
    else
        test_fail "Node.js is not available"
    fi
    
    # Test Python availability
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"python3 --version","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        test_pass "Python is available"
    else
        test_fail "Python is not available"
    fi
}

test_claude_flow_availability() {
    test_start "Claude-Flow availability"
    
    # Test claude-flow version
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"npx claude-flow --version","cwd":"/workspace","timeout":30}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        test_pass "Claude-Flow is available"
        
        # Test claude-flow help
        response=$(curl -s -X POST "$API_URL/run" \
            -H "Content-Type: application/json" \
            -d '{"cmd":"npx claude-flow --help","cwd":"/workspace","timeout":30}')
        
        if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
            test_pass "Claude-Flow help works"
        else
            test_fail "Claude-Flow help failed"
        fi
    else
        test_fail "Claude-Flow is not available"
    fi
}

test_websocket_connectivity() {
    test_start "WebSocket connectivity"
    
    # Wait for WebSocket server
    if wait_for_service "http://localhost:5001" "WebSocket Server" 10; then
        test_pass "WebSocket server is running"
    else
        test_fail "WebSocket server is not accessible"
    fi
}

test_terminal_server() {
    test_start "Terminal server"
    
    if wait_for_service "$TERMINAL_URL" "Terminal Server" 10; then
        # Check terminal server endpoints
        response=$(curl -s "$TERMINAL_URL/" | jq -r '.name' 2>/dev/null)
        if [ "$response" = "DockerFlow Terminal Server" ]; then
            test_pass "Terminal server is working"
        else
            test_fail "Terminal server response incorrect"
        fi
        
        # Test sessions endpoint
        if curl -s -f "$TERMINAL_URL/sessions" >/dev/null 2>&1; then
            test_pass "Terminal sessions endpoint works"
        else
            test_fail "Terminal sessions endpoint failed"
        fi
        
        # Test health endpoint
        status=$(curl -s "$TERMINAL_URL/health" | jq -r '.status' 2>/dev/null)
        if [ "$status" = "healthy" ]; then
            test_pass "Terminal health endpoint works"
        else
            test_fail "Terminal health endpoint failed"
        fi
    else
        test_fail "Terminal server is not accessible"
    fi
}

test_ttyd_availability() {
    test_start "ttyd terminal availability"
    
    if wait_for_service "$TTYD_URL" "ttyd Terminal" 10; then
        test_pass "ttyd terminal is accessible"
    else
        warning "ttyd terminal is not accessible (may be expected)"
    fi
}

test_file_permissions() {
    test_start "File permissions and workspace"
    
    # Test workspace accessibility
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"ls -la /workspace","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        test_pass "Workspace is accessible"
    else
        test_fail "Workspace is not accessible"
    fi
    
    # Test write permissions
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"touch /workspace/test_file && rm /workspace/test_file","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        test_pass "Workspace has write permissions"
    else
        test_fail "Workspace write permissions failed"
    fi
}

test_environment_variables() {
    test_start "Environment variables"
    
    # Test basic environment
    response=$(curl -s -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"env | grep -E \"(HOME|USER|PATH|NODE_ENV)\"","cwd":"/workspace","timeout":10}')
    
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        output=$(echo "$response" | jq -r '.output')
        if echo "$output" | grep -q "HOME\|USER\|PATH"; then
            test_pass "Basic environment variables are set"
        else
            test_fail "Basic environment variables missing"
        fi
    else
        test_fail "Environment variable check failed"
    fi
}

test_security_restrictions() {
    test_start "Security restrictions"
    
    # Test dangerous command blocking
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/run" \
        -H "Content-Type: application/json" \
        -d '{"cmd":"rm -rf /","cwd":"/workspace","timeout":10}')
    
    if [ "$response" = "403" ]; then
        test_pass "Dangerous commands are blocked"
    else
        test_fail "Dangerous commands are not properly blocked (got HTTP $response)"
    fi
}

test_concurrent_requests() {
    test_start "Concurrent request handling"
    
    # Start multiple background requests
    pids=()
    for i in {1..5}; do
        curl -s -X POST "$API_URL/run" \
            -H "Content-Type: application/json" \
            -d "{\"cmd\":\"echo 'Request $i' && sleep 1\",\"cwd\":\"/workspace\",\"timeout\":10}" \
            > "/tmp/response_$i.json" &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    success_count=0
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            success_count=$((success_count + 1))
        fi
    done
    
    # Check results
    if [ "$success_count" -eq 5 ]; then
        test_pass "Concurrent requests handled successfully"
    else
        test_fail "Only $success_count/5 concurrent requests succeeded"
    fi
    
    # Cleanup
    rm -f /tmp/response_*.json
}

run_python_tests() {
    test_start "Python test suite"
    
    # Check if test files exist
    if [ -f "tests/test_api.py" ]; then
        if python3 -c "import pytest" 2>/dev/null; then
            log "Running Python API tests..."
            if python3 tests/test_api.py; then
                test_pass "Python API tests passed"
            else
                test_fail "Python API tests failed"
            fi
        else
            warning "pytest not available, skipping Python tests"
        fi
    else
        warning "Python test files not found, skipping"
    fi
    
    if [ -f "tests/test_ws.py" ]; then
        if python3 -c "import pytest, websockets, asyncio" 2>/dev/null; then
            log "Running Python WebSocket tests..."
            if python3 tests/test_ws.py; then
                test_pass "Python WebSocket tests passed"
            else
                test_fail "Python WebSocket tests failed"
            fi
        else
            warning "WebSocket test dependencies not available, skipping"
        fi
    fi
}

cleanup_services() {
    log "Cleaning up services..."
    
    # Try docker compose first (v2), then docker-compose (v1)
    if docker compose -f "$COMPOSE_FILE" down 2>/dev/null; then
        success "Services stopped with 'docker compose'"
    elif docker-compose -f "$COMPOSE_FILE" down 2>/dev/null; then
        success "Services stopped with 'docker-compose'"
    else
        error "Failed to stop services"
    fi
}

show_results() {
    echo
    echo "=================================="
    echo "   DockerFlow Integration Tests"
    echo "=================================="
    echo
    echo "Total Tests: $TESTS_TOTAL"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ $TESTS_FAILED test(s) failed.${NC}"
        return 1
    fi
}

show_service_logs() {
    if [ $TESTS_FAILED -gt 0 ]; then
        warning "Some tests failed. Showing service logs..."
        
        # Try docker compose first (v2), then docker-compose (v1)
        if command -v docker >/dev/null 2>&1; then
            if docker compose -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null; then
                echo "Logs shown with 'docker compose'"
            elif docker-compose -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null; then
                echo "Logs shown with 'docker-compose'"
            else
                error "Could not retrieve service logs"
            fi
        fi
    fi
}

# Main test execution
main() {
    log "Starting DockerFlow Integration Test Suite"
    
    # Change to the directory containing docker-compose.yml
    if [ -f "$COMPOSE_FILE" ]; then
        log "Found $COMPOSE_FILE in current directory"
    else
        error "$COMPOSE_FILE not found in current directory"
        exit 1
    fi
    
    # Check prerequisites
    if ! check_docker_compose; then
        exit 1
    fi
    
    # Check if jq is available (for JSON parsing)
    if ! command -v jq >/dev/null 2>&1; then
        warning "jq not available, some tests may be skipped"
    fi
    
    # Start services
    if ! start_services; then
        exit 1
    fi
    
    # Wait a bit for services to fully initialize
    log "Waiting for services to initialize..."
    sleep 10
    
    # Run all tests
    test_ui_accessibility
    test_api_endpoints
    test_command_execution
    test_claude_flow_availability
    test_websocket_connectivity
    test_terminal_server
    test_ttyd_availability
    test_file_permissions
    test_environment_variables
    test_security_restrictions
    test_concurrent_requests
    run_python_tests
    
    # Show results
    show_results
    exit_code=$?
    
    # Show logs if there were failures
    show_service_logs
    
    # Cleanup (optional, comment out if you want to keep services running)
    if [ "${KEEP_RUNNING:-}" != "true" ]; then
        cleanup_services
    else
        log "Services kept running (KEEP_RUNNING=true)"
    fi
    
    return $exit_code
}

# Handle script arguments
case "${1:-}" in
    "clean")
        cleanup_services
        exit 0
        ;;
    "logs")
        if docker compose -f "$COMPOSE_FILE" logs 2>/dev/null; then
            echo "Logs shown with 'docker compose'"
        elif docker-compose -f "$COMPOSE_FILE" logs 2>/dev/null; then
            echo "Logs shown with 'docker-compose'"
        fi
        exit 0
        ;;
    "help"|"--help"|"-h")
        echo "DockerFlow Integration Test Suite"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  (no args)  Run full integration test suite"
        echo "  clean      Stop and cleanup services"
        echo "  logs       Show service logs"
        echo "  help       Show this help message"
        echo
        echo "Environment Variables:"
        echo "  KEEP_RUNNING=true    Keep services running after tests"
        exit 0
        ;;
esac

# Run main test suite
if main; then
    exit 0
else
    exit 1
fi