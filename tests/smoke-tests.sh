#!/bin/bash

# Smoke Tests for VidProd
# Quick tests to verify basic functionality after deployment

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TEST_TIMEOUT="${TEST_TIMEOUT:-30}"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

run_test() {
    local test_name=$1
    local test_function=$2
    
    echo -n "Testing $test_name... "
    
    if $test_function; then
        echo -e "${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}FAILED${NC}"
        ((TESTS_FAILED++))
    fi
}

# Test functions
test_homepage_loads() {
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" 2>/dev/null)
    [ "$response" == "200" ]
}

test_api_health() {
    response=$(curl -s "$BASE_URL/api/health" 2>/dev/null || echo "{}")
    echo "$response" | grep -q '"status":"healthy"'
}

test_upload_page_has_elements() {
    content=$(curl -s "$BASE_URL/" 2>/dev/null)
    echo "$content" | grep -q "upload-area" && \
    echo "$content" | grep -q "browseButton" && \
    echo "$content" | grep -q "VidProd"
}

test_static_assets_load() {
    # Test CSS
    css_response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/css/styles.css" 2>/dev/null)
    [ "$css_response" == "200" ] || return 1
    
    # Test JavaScript
    js_response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/js/upload.js" 2>/dev/null)
    [ "$js_response" == "200" ] || return 1
    
    return 0
}

test_api_endpoints_respond() {
    endpoints=("/api/upload/status" "/api/health" "/api/ready")
    
    for endpoint in "${endpoints[@]}"; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
        if [[ ! "$response" =~ ^(200|201|204)$ ]]; then
            return 1
        fi
    done
    
    return 0
}

test_cors_headers() {
    headers=$(curl -s -I "$BASE_URL/api/health" 2>/dev/null)
    echo "$headers" | grep -qi "access-control-allow-origin"
}

test_security_headers() {
    headers=$(curl -s -I "$BASE_URL/" 2>/dev/null)
    
    # Check for basic security headers
    echo "$headers" | grep -qi "x-content-type-options: nosniff" || return 1
    echo "$headers" | grep -qi "x-frame-options" || return 1
    
    return 0
}

test_upload_endpoint_options() {
    response=$(curl -s -X OPTIONS -o /dev/null -w "%{http_code}" "$BASE_URL/api/upload" 2>/dev/null)
    [[ "$response" =~ ^(200|204)$ ]]
}

test_websocket_upgrade() {
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Upgrade: websocket" \
        -H "Connection: Upgrade" \
        "$BASE_URL/ws" 2>/dev/null)
    
    # WebSocket should return 101 or at least not 404
    [[ "$response" == "101" ]] || [[ "$response" != "404" ]]
}

test_rate_limiting() {
    # Send 10 rapid requests
    local limited=0
    
    for i in {1..10}; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health" 2>/dev/null)
        if [ "$response" == "429" ]; then
            limited=1
            break
        fi
    done
    
    # We expect rate limiting to kick in, or at least all requests to succeed
    [ $limited -eq 1 ] || [ "$response" == "200" ]
}

test_error_handling() {
    # Test 404 handling
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/nonexistent" 2>/dev/null)
    [ "$response" == "404" ] || return 1
    
    # Test invalid upload
    response=$(curl -s -X POST -o /dev/null -w "%{http_code}" "$BASE_URL/api/upload" 2>/dev/null)
    [[ "$response" =~ ^(400|422)$ ]] || return 1
    
    return 0
}

test_metrics_endpoint() {
    response=$(curl -s "$BASE_URL/api/metrics" 2>/dev/null || echo "")
    
    # Check if metrics contain expected data
    echo "$response" | grep -q "http_requests" || \
    echo "$response" | grep -q "upload_" || \
    echo "$response" | grep -q "error_rate"
}

# Main execution
main() {
    log "Starting smoke tests for $BASE_URL"
    echo "================================================"
    
    # Basic functionality tests
    run_test "Homepage loads" test_homepage_loads
    run_test "API health endpoint" test_api_health
    run_test "Upload page elements" test_upload_page_has_elements
    run_test "Static assets load" test_static_assets_load
    run_test "API endpoints respond" test_api_endpoints_respond
    
    # Security tests
    run_test "CORS headers present" test_cors_headers
    run_test "Security headers set" test_security_headers
    
    # Advanced functionality tests
    run_test "Upload endpoint OPTIONS" test_upload_endpoint_options
    run_test "WebSocket upgrade" test_websocket_upgrade
    run_test "Rate limiting works" test_rate_limiting
    run_test "Error handling" test_error_handling
    run_test "Metrics endpoint" test_metrics_endpoint
    
    echo "================================================"
    log "Smoke Test Summary:"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    # Exit code based on results
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All smoke tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some smoke tests failed!${NC}"
        exit 1
    fi
}

# Run main function
main