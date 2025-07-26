# Multi-stage Dockerfile optimized for Fly.io deployment
# Builds both frontend and backend in a single image

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ ./

# Build frontend (if build script exists)
RUN npm run build 2>/dev/null || echo "No build script found"

# Optimize assets
RUN find . -name "*.js" -not -path "./node_modules/*" -exec npx terser {} -o {} \; 2>/dev/null || true
RUN find . -name "*.css" -not -path "./node_modules/*" -exec npx cssnano {} {} \; 2>/dev/null || true

# Stage 2: Python base
FROM python:3.11-slim AS python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Stage 3: Python dependencies
FROM python-base AS python-deps

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 4: Final application
FROM python-base AS runtime

# Create non-root user
RUN useradd -m -u 1000 vidprod && \
    mkdir -p /app /data /logs && \
    chown -R vidprod:vidprod /app /data /logs

WORKDIR /app

# Copy Python dependencies from deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy backend application
COPY --chown=vidprod:vidprod backend/ ./backend/

# Copy frontend build from frontend-builder
COPY --from=frontend-builder --chown=vidprod:vidprod /app/frontend ./frontend/

# Copy configuration files
COPY --chown=vidprod:vidprod fly.toml ./
COPY --chown=vidprod:vidprod scripts/start.sh ./start.sh

# Make start script executable
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p /app/uploads /app/temp /app/logs && \
    chown -R vidprod:vidprod /app/uploads /app/temp /app/logs

# Switch to non-root user
USER vidprod

# Environment variables
ENV PORT=8080 \
    HOST=0.0.0.0 \
    WORKERS=4 \
    ENVIRONMENT=production \
    UPLOAD_PATH=/data/uploads \
    TEMP_PATH=/data/temp \
    LOG_PATH=/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Expose port
EXPOSE 8080

# Volume for persistent data
VOLUME ["/data", "/logs"]

# Build arguments
ARG BUILD_DATE
ARG VERSION
LABEL build_date=$BUILD_DATE \
      version=$VERSION \
      maintainer="VidProd Team" \
      description="VidProd video upload service"

# Start command
CMD ["./start.sh"]