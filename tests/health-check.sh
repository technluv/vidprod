#!/bin/bash

# Health Check Script for VidProd
# Monitors application health across multiple endpoints

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-10}"

# Check if running in GitHub Codespaces and make ports public for health checks
if [ -n "$CODESPACE_NAME" ]; then
    echo "📍 Detected GitHub Codespaces - Ensuring ports are public for health checks..."
    gh codespace ports visibility 3000:public -c $CODESPACE_NAME 2>/dev/null || true
    gh codespace ports visibility 8000:public -c $CODESPACE_NAME 2>/dev/null || true
    # Update BASE_URL if not provided
    if [ "$1" = "" ]; then
        BASE_URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    fi
fi
RETRY_COUNT="${RETRY_COUNT:-3}"
RETRY_DELAY="${RETRY_DELAY:-5}"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Health check endpoints
declare -A ENDPOINTS=(
    ["API_HEALTH"]="/api/health"
    ["API_READY"]="/api/ready"
    ["FRONTEND"]="/"
    ["UPLOAD_ENDPOINT"]="/api/upload/status"
    ["METRICS"]="/api/metrics"
    ["WEBSOCKET"]="/ws/health"
)

# Expected responses
declare -A EXPECTED_STATUS=(
    ["API_HEALTH"]=200
    ["API_READY"]=200
    ["FRONTEND"]=200
    ["UPLOAD_ENDPOINT"]=200
    ["METRICS"]=200
    ["WEBSOCKET"]=101
)

# Results tracking
declare -A CHECK_RESULTS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

check_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=$3
    local retries=$RETRY_COUNT
    
    log "Checking $name at $BASE_URL$endpoint..."
    
    while [ $retries -gt 0 ]; do
        if [ "$name" == "WEBSOCKET" ]; then
            # Special handling for WebSocket
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                --connect-timeout $TIMEOUT \
                -H "Upgrade: websocket" \
                -H "Connection: Upgrade" \
                "$BASE_URL$endpoint" 2>/dev/null || echo "000")
        else
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                --connect-timeout $TIMEOUT \
                "$BASE_URL$endpoint" 2>/dev/null || echo "000")
        fi
        
        if [ "$response" == "$expected_status" ]; then
            echo -e "${GREEN}✓${NC} $name: OK (Status: $response)"
            CHECK_RESULTS[$name]="PASSED"
            ((PASSED_CHECKS++))
            return 0
        fi
        
        ((retries--))
        if [ $retries -gt 0 ]; then
            log "Retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
        fi
    done
    
    echo -e "${RED}✗${NC} $name: FAILED (Expected: $expected_status, Got: $response)"
    CHECK_RESULTS[$name]="FAILED"
    ((FAILED_CHECKS++))
    return 1
}

check_response_time() {
    local endpoint=$1
    local max_time=${2:-5000}  # Max response time in milliseconds
    
    log "Checking response time for $endpoint..."
    
    response_time=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL$endpoint" 2>/dev/null || echo "999")
    response_time_ms=$(awk "BEGIN {print $response_time * 1000}")
    
    if (( $(echo "$response_time_ms < $max_time" | bc -l) )); then
        echo -e "${GREEN}✓${NC} Response time: ${response_time_ms}ms"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Slow response: ${response_time_ms}ms (threshold: ${max_time}ms)"
        return 1
    fi
}

check_disk_space() {
    log "Checking disk space..."
    
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $disk_usage -lt 90 ]; then
        echo -e "${GREEN}✓${NC} Disk usage: ${disk_usage}%"
        return 0
    else
        echo -e "${RED}✗${NC} High disk usage: ${disk_usage}%"
        return 1
    fi
}

check_memory_usage() {
    log "Checking memory usage..."
    
    if command -v free &> /dev/null; then
        memory_usage=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
        
        if [ $memory_usage -lt 90 ]; then
            echo -e "${GREEN}✓${NC} Memory usage: ${memory_usage}%"
            return 0
        else
            echo -e "${RED}✗${NC} High memory usage: ${memory_usage}%"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} Cannot check memory (free command not available)"
        return 0
    fi
}

check_upload_functionality() {
    log "Testing upload functionality..."
    
    # Create a small test file
    test_file="/tmp/health-check-test.mp4"
    dd if=/dev/urandom of="$test_file" bs=1024 count=100 &>/dev/null
    
    # Try to upload
    response=$(curl -s -X POST \
        -F "file=@$test_file" \
        "$BASE_URL/api/upload" \
        -w "\n%{http_code}" 2>/dev/null || echo "000")
    
    status_code=$(echo "$response" | tail -n1)
    
    # Clean up
    rm -f "$test_file"
    
    if [[ "$status_code" =~ ^(200|201|202)$ ]]; then
        echo -e "${GREEN}✓${NC} Upload endpoint functional"
        return 0
    else
        echo -e "${RED}✗${NC} Upload endpoint error (Status: $status_code)"
        return 1
    fi
}

check_database_connection() {
    log "Checking database connection..."
    
    response=$(curl -s "$BASE_URL/api/health/db" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        echo -e "${GREEN}✓${NC} Database connection healthy"
        return 0
    else
        echo -e "${RED}✗${NC} Database connection issues"
        return 1
    fi
}

# Main execution
main() {
    log "Starting health checks for $BASE_URL"
    echo "================================================"
    
    # Basic endpoint checks
    for name in "${!ENDPOINTS[@]}"; do
        check_endpoint "$name" "${ENDPOINTS[$name]}" "${EXPECTED_STATUS[$name]}"
        ((TOTAL_CHECKS++))
    done
    
    echo "================================================"
    
    # Performance checks
    check_response_time "/" 2000
    check_response_time "/api/health" 500
    
    echo "================================================"
    
    # System checks
    check_disk_space
    check_memory_usage
    
    echo "================================================"
    
    # Functional checks
    check_upload_functionality
    check_database_connection
    
    echo "================================================"
    log "Health Check Summary:"
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    
    # Exit code based on results
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "\n${GREEN}All health checks passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}Some health checks failed!${NC}"
        exit 1
    fi
}

# Run main function
main