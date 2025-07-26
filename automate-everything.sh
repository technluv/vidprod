#!/bin/bash
# VidProd Automation Script for Fly.io Deployment
# One-click setup, test, and deployment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="vidprod"
PYTHON_VERSION="3.11"

# Functions
print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running in GitHub Codespaces
check_codespaces() {
    if [ -n "$CODESPACE_NAME" ]; then
        print_status "Detected GitHub Codespaces environment"
        export CODESPACES=true
        export PUBLIC_URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
        export FRONTEND_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    else
        export CODESPACES=false
    fi
}

# Manage Codespaces port visibility
manage_codespace_ports() {
    if [ "$CODESPACES" = true ]; then
        local action=${1:-public}  # Default to public
        print_status "Setting Codespaces ports to $action..."
        
        # Frontend port 3000
        gh codespace ports visibility 3000:$action -c $CODESPACE_NAME 2>/dev/null || true
        # API port 8000  
        gh codespace ports visibility 8000:$action -c $CODESPACE_NAME 2>/dev/null || true
        
        if [ "$action" = "public" ]; then
            print_success "Ports are now PUBLIC:"
            echo "  Frontend: $FRONTEND_URL"
            echo "  API: $PUBLIC_URL"
        else
            print_success "Ports are now PRIVATE (Codespace access only)"
        fi
    fi
}

# Install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq ffmpeg python3-pip python3-venv > /dev/null 2>&1
        print_success "System dependencies installed"
    else
        print_warning "Not a Debian-based system, skipping apt-get installations"
    fi
}

# Setup Python environment
setup_python() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install requirements
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "Python dependencies installed"
}

# Setup local development environment
setup_local_env() {
    print_status "Setting up local environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# VidProd Local Development Configuration
APP_ENV=development
LOG_LEVEL=debug

# Storage paths (local development)
TEMP_STORAGE_PATH=./data/temp
DB_PATH=./data/db/vidprod.db

# API Keys (add your own)
# TIKTOK_API_KEY=
# TIKTOK_API_SECRET=
# INSTAGRAM_USERNAME=
# INSTAGRAM_PASSWORD=
# YOUTUBE_API_KEY=
# YOUTUBE_CLIENT_ID=
# YOUTUBE_CLIENT_SECRET=
EOF
        print_success "Created .env file"
    fi
    
    # Create data directories
    mkdir -p data/temp data/db data/logs
    print_success "Data directories created"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Make ports public for testing in Codespaces
    if [ "$CODESPACES" = true ]; then
        manage_codespace_ports public
    fi
    
    # Create basic test file if it doesn't exist
    if [ ! -f "tests/test_health.py" ]; then
        mkdir -p tests
        cat > tests/test_health.py << 'EOF'
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
EOF
    fi
    
    # Run pytest
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short || print_warning "Some tests failed"
    else
        print_warning "pytest not found, skipping tests"
    fi
}

# Start local development server
start_local() {
    print_status "Starting local development server..."
    
    # Kill any existing processes on port 8000
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Killing existing process on port 8000"
        kill -9 $(lsof -Pi :8000 -sTCP:LISTEN -t) 2>/dev/null || true
    fi
    
    # Start the server
    if [ "$CODESPACES" = true ]; then
        # Make ports public for testing/UAT
        manage_codespace_ports public
        print_success "Access your app at: $PUBLIC_URL"
    else
        print_success "Access your app at: http://localhost:8000"
    fi
    
    # Run with auto-reload
    python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
}

# Setup Fly.io
setup_fly() {
    print_status "Setting up Fly.io deployment..."
    
    # Check if fly CLI is installed
    if ! command -v fly &> /dev/null; then
        print_status "Installing Fly.io CLI..."
        curl -L https://fly.io/install.sh | sh
        export PATH="$HOME/.fly/bin:$PATH"
    fi
    
    # Check if logged in to Fly.io
    if ! fly auth whoami &> /dev/null; then
        print_warning "Please log in to Fly.io"
        fly auth login
    fi
    
    # Check if app exists
    if ! fly apps list | grep -q "$APP_NAME"; then
        print_status "Creating Fly.io app..."
        fly apps create "$APP_NAME" || print_error "Failed to create app (name might be taken)"
    else
        print_success "App '$APP_NAME' already exists"
    fi
    
    # Create volume for persistent storage
    if ! fly volumes list | grep -q "vidprod_data"; then
        print_status "Creating persistent volume..."
        fly volumes create vidprod_data --size 10 --region iad
    fi
    
    # Set secrets (only if not already set)
    print_status "Setting up secrets..."
    fly secrets set APP_ENV=production --stage || true
    
    print_success "Fly.io setup complete"
}

# Deploy to Fly.io
deploy_fly() {
    print_status "Deploying to Fly.io..."
    
    # Deploy the app
    fly deploy
    
    # Show app status
    fly status
    
    # Get app URL
    APP_URL=$(fly info --json | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['hostname'])")
    print_success "Deployment complete! App available at: https://$APP_URL"
}

# Run end-to-end tests
run_e2e_tests() {
    print_status "Running E2E tests..."
    
    # Create E2E test script if it doesn't exist
    if [ ! -f "tests/e2e_test.py" ]; then
        cat > tests/e2e_test.py << 'EOF'
import asyncio
import httpx
import sys

async def test_upload_flow():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health check
        response = await client.get(f"{base_url}/health")
        assert response.status_code == 200
        print("✓ Health check passed")
        
        # Test upload page
        response = await client.get(f"{base_url}/static/index.html")
        assert response.status_code == 200
        print("✓ Upload page accessible")
        
        # Test API endpoints
        response = await client.get(f"{base_url}/api/v1/jobs")
        assert response.status_code == 200
        print("✓ Jobs API accessible")

if __name__ == "__main__":
    asyncio.run(test_upload_flow())
EOF
    fi
    
    # Run E2E tests
    python tests/e2e_test.py "${PUBLIC_URL:-http://localhost:8000}" || print_warning "E2E tests failed"
}

# Main menu
show_menu() {
    echo
    echo -e "${BLUE}VidProd Automation Menu${NC}"
    echo "========================"
    echo "1) Setup local environment"
    echo "2) Run tests"
    echo "3) Start local server"
    echo "4) Setup Fly.io"
    echo "5) Deploy to Fly.io"
    echo "6) Run E2E tests"
    echo "7) Full setup and deploy"
    echo "8) Exit"
    echo
}

# Main execution
main() {
    print_status "VidProd Automation Script Started"
    check_codespaces
    
    # If no arguments, show menu
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
            read -p "Select an option: " choice
            
            case $choice in
                1)
                    install_dependencies
                    setup_python
                    setup_local_env
                    ;;
                2)
                    setup_python
                    run_tests
                    ;;
                3)
                    setup_python
                    start_local
                    ;;
                4)
                    setup_fly
                    ;;
                5)
                    deploy_fly
                    ;;
                6)
                    run_e2e_tests
                    ;;
                7)
                    install_dependencies
                    setup_python
                    setup_local_env
                    run_tests
                    setup_fly
                    deploy_fly
                    run_e2e_tests
                    ;;
                8)
                    print_status "Exiting..."
                    exit 0
                    ;;
                *)
                    print_error "Invalid option"
                    ;;
            esac
        done
    else
        # Run specific command
        case $1 in
            setup)
                install_dependencies
                setup_python
                setup_local_env
                ;;
            test)
                setup_python
                run_tests
                ;;
            start)
                setup_python
                start_local
                ;;
            deploy)
                setup_fly
                deploy_fly
                ;;
            all)
                install_dependencies
                setup_python
                setup_local_env
                run_tests
                setup_fly
                deploy_fly
                run_e2e_tests
                ;;
            *)
                print_error "Unknown command: $1"
                echo "Usage: $0 [setup|test|start|deploy|all]"
                exit 1
                ;;
        esac
    fi
}

# Run main function
main "$@"