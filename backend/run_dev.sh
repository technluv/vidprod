#!/bin/bash

# Development runner script for VidProd backend

echo "🚀 Starting VidProd Backend Development Server..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration!"
fi

# Create upload directories
echo "📁 Creating upload directories..."
mkdir -p uploads/{pending,processing,completed,failed}

# Check if virtual environment exists
if [ ! -d venv ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Generate a secret key if not set
if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=your-secret-key-here-change-in-production" .env; then
    echo "🔐 Generating secret key..."
    SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    fi
    echo "✅ Secret key generated and saved to .env"
fi

# Run the application
echo "🚀 Starting FastAPI server..."
echo "📍 API will be available at http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000