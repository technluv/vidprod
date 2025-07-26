"""
VidProd FastAPI Application
Optimized for Fly.io deployment with minimal resource usage
"""
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
import structlog

from api.core.config import settings
from api.core.logging import setup_logging
from api.routers import upload, health, jobs, download
from shared.database.connection import init_db

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting VidProd API server")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Create necessary directories
    Path(settings.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    logger.info("Storage directories created")
    
    # Start background tasks if not in worker mode
    if not os.getenv("WORKER_MODE"):
        from api.core.background import start_cleanup_task
        cleanup_task = asyncio.create_task(start_cleanup_task())
        logger.info("Cleanup task started")
    
    yield
    
    # Cleanup
    logger.info("Shutting down VidProd API server")
    if not os.getenv("WORKER_MODE") and 'cleanup_task' in locals():
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


# Create FastAPI app
app = FastAPI(
    title="VidProd API",
    description="Automated video processing and upload system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(download.router, prefix="/api/v1", tags=["download"])

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root():
    """Root endpoint - serves upload frontend"""
    return {
        "message": "VidProd API",
        "version": "1.0.0",
        "upload_ui": "/static/index.html"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
        log_config=None  # Use structlog instead
    )