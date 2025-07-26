# VidProd Test Suite

Comprehensive test suite for the VidProd video upload application, including E2E tests, API tests, stress tests, and deployment automation.

## Test Structure

```
tests/
├── tests/
│   ├── e2e/                    # End-to-end tests
│   │   └── upload.spec.js      # Video upload flow tests
│   ├── api/                    # API integration tests
│   │   └── upload-api.spec.js  # Upload API tests
│   └── stress/                 # Stress and performance tests
│       └── concurrent-upload.spec.js
├── fixtures/                   # Test data
│   ├── generate-test-videos.js # Test video generator
│   └── videos/                 # Generated test videos
├── reports/                    # Test reports (generated)
├── package.json               # Node dependencies
├── playwright.config.js       # Playwright configuration
├── .env.test                  # Test environment variables
├── health-check.sh            # Health monitoring script
├── smoke-tests.sh             # Quick smoke tests
├── monitor-deployment.sh      # Continuous monitoring
└── run-all-tests.sh          # Comprehensive test runner
```

## Quick Start

### 1. Install Dependencies

```bash
cd tests
npm install
npx playwright install --with-deps
```

### 2. Generate Test Videos

```bash
node fixtures/generate-test-videos.js
```

### 3. Run Tests

#### All Tests
```bash
./run-all-tests.sh
```

#### Specific Test Suites
```bash
# E2E tests only
npm run test

# API tests only
npm run test:api

# Stress tests
npm run test:stress

# With browser UI
npm run test:headed

# Debug mode
npm run test:debug
```

## Test Types

### 1. E2E Tests (`tests/e2e/upload.spec.js`)

Comprehensive browser-based tests covering:
- Upload interface rendering
- File selection (browse button)
- Drag and drop functionality
- Upload progress tracking
- Multiple file uploads
- File type validation
- Error handling
- Network failure recovery
- Accessibility features

### 2. API Tests (`tests/api/upload-api.spec.js`)

Direct API testing including:
- Multipart file uploads
- File size validation
- File type validation
- Chunked uploads
- Upload progress endpoints
- Concurrent upload handling
- Resume functionality
- Rate limiting

### 3. Stress Tests (`tests/stress/concurrent-upload.spec.js`)

Performance and reliability testing:
- 10+ concurrent uploads
- Rapid sequential uploads
- Large queue handling
- Mixed file sizes
- Partial failure recovery
- Memory leak detection
- Browser refresh handling

## Health Monitoring

### Health Check Script

```bash
# Basic health check
./health-check.sh https://vidprod.fly.dev

# With custom timeout and retries
TIMEOUT=20 RETRY_COUNT=5 ./health-check.sh https://vidprod.fly.dev
```

Checks:
- API health endpoints
- Frontend availability
- Upload functionality
- Database connectivity
- Response times
- System resources

### Smoke Tests

```bash
# Quick functionality verification
./smoke-tests.sh https://vidprod.fly.dev
```

Tests:
- Homepage loads
- Static assets available
- API endpoints respond
- Security headers present
- Error handling works
- WebSocket upgrades

### Continuous Monitoring

```bash
# Monitor for 5 minutes
./monitor-deployment.sh https://vidprod.fly.dev 300

# Monitor with custom interval
./monitor-deployment.sh https://vidprod.fly.dev 600 15
```

Features:
- Real-time health checks
- Response time tracking
- Error rate monitoring
- Resource usage alerts
- Detailed summary report

## Deployment

### Automated Deployment Script

```bash
# Full deployment with tests
./automate-everything.sh

# Skip tests (not recommended)
./automate-everything.sh --skip-tests
```

The script handles:
1. Dependency verification
2. Test execution
3. Docker image building
4. Fly.io deployment
5. Post-deployment checks
6. Automatic rollback on failure

### Manual Deployment

```bash
# Build Docker image
docker build -t vidprod:latest .

# Deploy to Fly.io
flyctl deploy

# Run post-deployment checks
./tests/smoke-tests.sh https://vidprod.fly.dev
./tests/health-check.sh https://vidprod.fly.dev
```

## CI/CD with GitHub Actions

The `.github/workflows/deploy.yml` workflow provides:

1. **Test Stage**
   - Python backend tests
   - Playwright E2E tests
   - Code coverage reporting

2. **Build Stage**
   - Multi-stage Docker build
   - Image caching
   - Registry push

3. **Deploy Staging** (on PR)
   - Deploy to staging environment
   - Run smoke tests
   - Health checks

4. **Deploy Production** (on main branch)
   - Deploy to production
   - Smoke tests
   - Health checks
   - Create release

5. **Rollback** (on failure)
   - Automatic rollback
   - Slack notifications

## Environment Variables

### Test Environment (`.env.test`)

```bash
BASE_URL=http://localhost:8000
API_URL=http://localhost:8000/api
TEST_USER_EMAIL=test@vidprod.com
TEST_USER_PASSWORD=Test123!@#
MAX_FILE_SIZE_MB=100
CONCURRENT_UPLOADS=3
```

### CI Environment

Set in GitHub Secrets:
- `FLY_API_TOKEN` - Fly.io authentication
- `SLACK_WEBHOOK` - Slack notifications

## Writing New Tests

### E2E Test Template

```javascript
test('should handle new feature', async ({ page }) => {
    await page.goto('/');
    
    // Your test logic
    await page.click('#element');
    await expect(page.locator('.result')).toBeVisible();
});
```

### API Test Template

```javascript
test('should test new endpoint', async ({ request }) => {
    const response = await request.post(`${API_URL}/new-endpoint`, {
        data: { key: 'value' }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('expected_field');
});
```

## Troubleshooting

### Common Issues

1. **Tests fail locally but pass in CI**
   - Check environment variables
   - Ensure test videos are generated
   - Verify local server is running

2. **Flaky tests**
   - Increase timeouts in playwright.config.js
   - Add explicit waits for dynamic content
   - Check for race conditions

3. **Deployment failures**
   - Check Fly.io logs: `flyctl logs`
   - Verify secrets are set: `flyctl secrets list`
   - Run health checks manually

### Debug Commands

```bash
# View Playwright trace
npx playwright show-trace trace.zip

# Debug specific test
npx playwright test upload.spec.js --debug

# Check Fly.io status
flyctl status
flyctl logs --tail

# Local Docker testing
docker run -p 8080:8080 vidprod:latest
curl http://localhost:8080/api/health
```

## Performance Benchmarks

Expected performance metrics:
- Page load: < 3 seconds
- Upload initialization: < 500ms
- API response time: < 200ms
- Concurrent uploads: 10+ without degradation
- Memory usage: < 500MB under load

## Contributing

1. Write tests for new features
2. Ensure all tests pass locally
3. Update this documentation
4. Create PR with test results

## License

[Your License]