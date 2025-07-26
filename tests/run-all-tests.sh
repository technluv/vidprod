#!/bin/bash

# Comprehensive Test Runner for VidProd
# Runs all test suites and generates reports

set -e

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if running in GitHub Codespaces and make ports public for testing
if [ -n "$CODESPACE_NAME" ]; then
    echo "📍 Detected GitHub Codespaces - Opening ports for testing..."
    gh codespace ports visibility 3000:public -c $CODESPACE_NAME 2>/dev/null || true
    gh codespace ports visibility 8000:public -c $CODESPACE_NAME 2>/dev/null || true
    echo "✅ Ports are now public for testing"
    echo "  Frontend: https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "  API: https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
fi
REPORT_DIR="$SCRIPT_DIR/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
SUITES_RUN=0

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

# Create report directory
setup_reports() {
    mkdir -p "$REPORT_DIR"
    mkdir -p "$REPORT_DIR/coverage"
    mkdir -p "$REPORT_DIR/playwright"
    mkdir -p "$REPORT_DIR/performance"
}

# Run backend unit tests
run_backend_tests() {
    log "Running backend unit tests..."
    ((SUITES_RUN++))
    
    cd "$PROJECT_ROOT/backend"
    
    if python -m pytest tests/ \
        -v \
        --tb=short \
        --cov=app \
        --cov-report=html:"$REPORT_DIR/coverage/backend" \
        --cov-report=xml:"$REPORT_DIR/coverage/backend.xml" \
        --junit-xml="$REPORT_DIR/backend-junit.xml"; then
        success "Backend tests passed"
        ((TESTS_PASSED++))
    else
        error "Backend tests failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Run E2E tests
run_e2e_tests() {
    log "Running E2E tests..."
    ((SUITES_RUN++))
    
    cd "$SCRIPT_DIR"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    # Generate test videos if needed
    if [ ! -d "fixtures/videos" ]; then
        node fixtures/generate-test-videos.js
    fi
    
    # Run Playwright tests
    if npm run test -- \
        --reporter=html:"$REPORT_DIR/playwright" \
        --reporter=json:"$REPORT_DIR/e2e-results.json" \
        --reporter=junit:"$REPORT_DIR/e2e-junit.xml"; then
        success "E2E tests passed"
        ((TESTS_PASSED++))
    else
        error "E2E tests failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Run API tests
run_api_tests() {
    log "Running API tests..."
    ((SUITES_RUN++))
    
    cd "$SCRIPT_DIR"
    
    if npm run test:api -- \
        --reporter=json:"$REPORT_DIR/api-results.json"; then
        success "API tests passed"
        ((TESTS_PASSED++))
    else
        error "API tests failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Run stress tests
run_stress_tests() {
    log "Running stress tests..."
    ((SUITES_RUN++))
    
    cd "$SCRIPT_DIR"
    
    if npm run test:stress -- \
        --reporter=json:"$REPORT_DIR/stress-results.json"; then
        success "Stress tests passed"
        ((TESTS_PASSED++))
    else
        error "Stress tests failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Run performance benchmarks
run_performance_tests() {
    log "Running performance benchmarks..."
    ((SUITES_RUN++))
    
    cd "$SCRIPT_DIR"
    
    # Create performance test script
    cat > "$REPORT_DIR/performance/benchmark.js" << 'EOF'
const { chromium } = require('playwright');
const fs = require('fs');

async function runBenchmark() {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    
    const results = {
        timestamp: new Date().toISOString(),
        metrics: {}
    };
    
    // Measure page load time
    const start = Date.now();
    await page.goto(process.env.BASE_URL || 'http://localhost:8000');
    const loadTime = Date.now() - start;
    results.metrics.pageLoadTime = loadTime;
    
    // Measure upload initialization
    const uploadStart = Date.now();
    await page.click('#browseButton');
    const uploadInitTime = Date.now() - uploadStart;
    results.metrics.uploadInitTime = uploadInitTime;
    
    // Get performance metrics
    const perfMetrics = await page.evaluate(() => {
        const timing = performance.timing;
        return {
            domContentLoaded: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
            loadComplete: timing.loadEventEnd - timing.loadEventStart,
            firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
            resources: performance.getEntriesByType('resource').length
        };
    });
    
    results.metrics = { ...results.metrics, ...perfMetrics };
    
    await browser.close();
    
    // Save results
    fs.writeFileSync(
        `performance-${Date.now()}.json`,
        JSON.stringify(results, null, 2)
    );
    
    console.log('Performance benchmark completed:', results);
    
    // Check thresholds
    if (loadTime > 3000) {
        console.error('Page load time exceeds threshold (3s)');
        process.exit(1);
    }
}

runBenchmark().catch(console.error);
EOF
    
    if node "$REPORT_DIR/performance/benchmark.js"; then
        success "Performance benchmarks passed"
        ((TESTS_PASSED++))
    else
        error "Performance benchmarks failed"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Run security scan
run_security_scan() {
    log "Running security scan..."
    ((SUITES_RUN++))
    
    cd "$PROJECT_ROOT"
    
    # Check for common security issues
    local issues=0
    
    # Check for hardcoded secrets
    if grep -r "password\s*=\s*[\"'][^\"']\+[\"']" --include="*.py" --include="*.js" backend/ frontend/ 2>/dev/null; then
        warning "Potential hardcoded passwords found"
        ((issues++))
    fi
    
    # Check for SQL injection vulnerabilities
    if grep -r "f\s*[\"'].*SELECT.*{" --include="*.py" backend/ 2>/dev/null; then
        warning "Potential SQL injection vulnerability found"
        ((issues++))
    fi
    
    # Check dependencies for vulnerabilities
    if command -v safety &> /dev/null; then
        cd "$PROJECT_ROOT/backend"
        if ! safety check; then
            warning "Vulnerable dependencies found"
            ((issues++))
        fi
    fi
    
    if [ $issues -eq 0 ]; then
        success "Security scan passed"
        ((TESTS_PASSED++))
    else
        error "Security scan found $issues issues"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Generate consolidated report
generate_report() {
    log "Generating test report..."
    
    cat > "$REPORT_DIR/summary.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>VidProd Test Report - $TIMESTAMP</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .passed { color: green; }
        .failed { color: red; }
        .suite { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>VidProd Test Report</h1>
        <p>Generated: $(date)</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr>
                <th>Total Test Suites</th>
                <td>$SUITES_RUN</td>
            </tr>
            <tr>
                <th>Passed</th>
                <td class="passed">$TESTS_PASSED</td>
            </tr>
            <tr>
                <th>Failed</th>
                <td class="failed">$TESTS_FAILED</td>
            </tr>
            <tr>
                <th>Success Rate</th>
                <td>$(( TESTS_PASSED * 100 / SUITES_RUN ))%</td>
            </tr>
        </table>
    </div>
    
    <div class="details">
        <h2>Test Results</h2>
        <ul>
            <li><a href="coverage/backend/index.html">Backend Coverage Report</a></li>
            <li><a href="playwright/index.html">E2E Test Report</a></li>
            <li><a href="backend-junit.xml">Backend JUnit Results</a></li>
            <li><a href="e2e-junit.xml">E2E JUnit Results</a></li>
        </ul>
    </div>
</body>
</html>
EOF
    
    success "Test report generated at $REPORT_DIR/summary.html"
}

# Main execution
main() {
    log "Starting comprehensive test suite..."
    echo "================================================"
    
    # Setup
    setup_reports
    
    # Start local server if needed
    if [ -z "$CI" ] && [ -z "$BASE_URL" ]; then
        log "Starting local server..."
        cd "$PROJECT_ROOT"
        python -m http.server 8000 &
        SERVER_PID=$!
        export BASE_URL="http://localhost:8000"
        sleep 2
    fi
    
    # Run test suites
    run_backend_tests || true
    run_e2e_tests || true
    run_api_tests || true
    
    # Optional test suites (based on flags)
    if [[ "$*" == *"--stress"* ]]; then
        run_stress_tests || true
    fi
    
    if [[ "$*" == *"--performance"* ]]; then
        run_performance_tests || true
    fi
    
    if [[ "$*" == *"--security"* ]]; then
        run_security_scan || true
    fi
    
    # Cleanup
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    
    # Generate report
    generate_report
    
    # Summary
    echo ""
    echo "================================================"
    log "Test Suite Summary:"
    echo "Total Suites Run: $SUITES_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    # Exit code
    if [ $TESTS_FAILED -eq 0 ]; then
        success "All tests passed!"
        exit 0
    else
        error "Some tests failed!"
        exit 1
    fi
}

# Handle cleanup
trap 'if [ -n "$SERVER_PID" ]; then kill $SERVER_PID 2>/dev/null || true; fi' EXIT

# Run main function
main "$@"