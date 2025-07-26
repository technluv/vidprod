#!/bin/bash

# Deployment Monitoring Script for VidProd
# Continuously monitors application health and performance metrics

set -e

# Configuration
APP_URL="${1:-https://vidprod.fly.dev}"
MONITOR_DURATION="${2:-300}"  # Default 5 minutes
CHECK_INTERVAL="${3:-10}"      # Check every 10 seconds
ALERT_THRESHOLD="${4:-3}"      # Alert after 3 consecutive failures

# Monitoring state
FAILURES=0
CHECKS=0
START_TIME=$(date +%s)

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Metrics storage
declare -A RESPONSE_TIMES
declare -A ERROR_COUNTS
declare -A STATUS_CODES

# Functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check application health
check_health() {
    local start_time=$(date +%s%N)
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/api/health" 2>/dev/null || echo "000")
    local end_time=$(date +%s%N)
    local response_time=$((($end_time - $start_time) / 1000000))  # Convert to ms
    
    ((CHECKS++))
    
    # Store metrics
    STATUS_CODES[$response]=$((${STATUS_CODES[$response]:-0} + 1))
    RESPONSE_TIMES[$CHECKS]=$response_time
    
    if [ "$response" == "200" ]; then
        success "Health check OK (${response_time}ms)"
        FAILURES=0
        return 0
    else
        error "Health check failed (Status: $response)"
        ((FAILURES++))
        ERROR_COUNTS[$response]=$((${ERROR_COUNTS[$response]:-0} + 1))
        return 1
    fi
}

# Check specific endpoints
check_endpoints() {
    local endpoints=("/" "/api/ready" "/api/upload/status" "/api/metrics")
    
    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL$endpoint" 2>/dev/null || echo "000")
        
        if [[ "$response" =~ ^(200|204)$ ]]; then
            echo "  ✓ $endpoint: OK"
        else
            echo "  ✗ $endpoint: Failed (Status: $response)"
        fi
    done
}

# Monitor resources via metrics endpoint
check_metrics() {
    local metrics=$(curl -s "$APP_URL/api/metrics" 2>/dev/null || echo "{}")
    
    if [ -n "$metrics" ] && [ "$metrics" != "{}" ]; then
        # Extract key metrics (adjust based on your metrics format)
        local cpu=$(echo "$metrics" | grep -o '"cpu_percent":[0-9.]*' | cut -d: -f2 || echo "N/A")
        local memory=$(echo "$metrics" | grep -o '"memory_mb":[0-9.]*' | cut -d: -f2 || echo "N/A")
        local active_uploads=$(echo "$metrics" | grep -o '"active_uploads":[0-9]*' | cut -d: -f2 || echo "0")
        local error_rate=$(echo "$metrics" | grep -o '"error_rate":[0-9.]*' | cut -d: -f2 || echo "0")
        
        log "Metrics: CPU: ${cpu}%, Memory: ${memory}MB, Active Uploads: $active_uploads, Error Rate: ${error_rate}%"
        
        # Alert on high resource usage
        if [ "$cpu" != "N/A" ] && (( $(echo "$cpu > 80" | bc -l) )); then
            warning "High CPU usage: ${cpu}%"
        fi
        
        if [ "$memory" != "N/A" ] && (( $(echo "$memory > 1024" | bc -l) )); then
            warning "High memory usage: ${memory}MB"
        fi
    fi
}

# Generate summary report
generate_report() {
    local end_time=$(date +%s)
    local duration=$(($end_time - $START_TIME))
    
    echo ""
    echo "================================================"
    echo "Deployment Monitoring Summary"
    echo "================================================"
    echo "URL: $APP_URL"
    echo "Duration: ${duration}s"
    echo "Total Checks: $CHECKS"
    echo ""
    
    # Calculate average response time
    local total_rt=0
    for rt in "${RESPONSE_TIMES[@]}"; do
        total_rt=$((total_rt + rt))
    done
    local avg_rt=$((total_rt / CHECKS))
    
    echo "Response Times:"
    echo "  Average: ${avg_rt}ms"
    echo "  Min: $(printf '%s\n' "${RESPONSE_TIMES[@]}" | sort -n | head -1)ms"
    echo "  Max: $(printf '%s\n' "${RESPONSE_TIMES[@]}" | sort -n | tail -1)ms"
    echo ""
    
    echo "Status Code Distribution:"
    for code in "${!STATUS_CODES[@]}"; do
        local percentage=$((${STATUS_CODES[$code]} * 100 / CHECKS))
        echo "  $code: ${STATUS_CODES[$code]} (${percentage}%)"
    done
    echo ""
    
    if [ ${#ERROR_COUNTS[@]} -gt 0 ]; then
        echo "Errors:"
        for code in "${!ERROR_COUNTS[@]}"; do
            echo "  $code: ${ERROR_COUNTS[$code]} occurrences"
        done
    else
        echo "No errors detected!"
    fi
    
    # Overall status
    echo ""
    local success_rate=$(( (CHECKS - ${ERROR_COUNTS[@]/%/+}0) * 100 / CHECKS ))
    if [ $success_rate -ge 99 ]; then
        success "Overall Status: HEALTHY (${success_rate}% success rate)"
    elif [ $success_rate -ge 95 ]; then
        warning "Overall Status: DEGRADED (${success_rate}% success rate)"
    else
        error "Overall Status: UNHEALTHY (${success_rate}% success rate)"
    fi
}

# Alert function
send_alert() {
    local message=$1
    
    error "ALERT: $message"
    
    # Send alerts via webhook if configured
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"VidProd Alert: $message\"}" \
            2>/dev/null || true
    fi
    
    # Log to file
    echo "[$(date)] ALERT: $message" >> /tmp/vidprod-alerts.log
}

# Main monitoring loop
main() {
    log "Starting deployment monitoring for $APP_URL"
    log "Duration: ${MONITOR_DURATION}s, Check Interval: ${CHECK_INTERVAL}s"
    echo "================================================"
    
    # Initial endpoint check
    log "Checking all endpoints..."
    check_endpoints
    echo ""
    
    # Main monitoring loop
    while true; do
        # Check if monitoring duration exceeded
        local current_time=$(date +%s)
        local elapsed=$((current_time - START_TIME))
        
        if [ $elapsed -ge $MONITOR_DURATION ]; then
            break
        fi
        
        # Perform health check
        if ! check_health; then
            if [ $FAILURES -ge $ALERT_THRESHOLD ]; then
                send_alert "Application health check failed $FAILURES times consecutively"
            fi
        fi
        
        # Check metrics every 30 seconds
        if [ $((CHECKS % 3)) -eq 0 ]; then
            check_metrics
        fi
        
        # Sleep before next check
        sleep $CHECK_INTERVAL
    done
    
    # Generate final report
    generate_report
}

# Handle interruption
trap 'echo ""; log "Monitoring interrupted"; generate_report; exit 0' INT TERM

# Run main function
main