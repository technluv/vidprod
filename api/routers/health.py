"""
Health check endpoints for monitoring
"""
import os
import time
import psutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from api.core.config import settings
from shared.database.connection import get_db

router = APIRouter()

# Track startup time
STARTUP_TIME = time.time()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint for Fly.io
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - STARTUP_TIME)
        },
        status_code=200
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with system metrics
    """
    # Check database connection
    db_healthy = True
    db_error = None
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
    except Exception as e:
        db_healthy = False
        db_error = str(e)
    
    # Check storage
    storage_path = Path(settings.TEMP_STORAGE_PATH)
    storage_healthy = storage_path.exists() and storage_path.is_dir()
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    # Count pending jobs
    pending_jobs = 0
    if db_healthy:
        try:
            async with get_db() as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = 'pending'"
                )
                row = await cursor.fetchone()
                pending_jobs = row[0] if row else 0
        except:
            pass
    
    health_data = {
        "status": "healthy" if db_healthy and storage_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - STARTUP_TIME),
        "checks": {
            "database": {
                "healthy": db_healthy,
                "error": db_error
            },
            "storage": {
                "healthy": storage_healthy,
                "path": str(storage_path)
            }
        },
        "metrics": {
            "cpu_percent": cpu_percent,
            "memory": {
                "used_mb": memory.used // (1024 * 1024),
                "total_mb": memory.total // (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "used_gb": disk.used // (1024 * 1024 * 1024),
                "total_gb": disk.total // (1024 * 1024 * 1024),
                "percent": disk.percent
            },
            "queue": {
                "pending_jobs": pending_jobs
            }
        },
        "environment": {
            "app_env": settings.APP_ENV,
            "worker_enabled": settings.WORKER_ENABLED,
            "fly_region": os.getenv("FLY_REGION", "unknown"),
            "fly_app_name": os.getenv("FLY_APP_NAME", "unknown")
        }
    }
    
    status_code = 200 if health_data["status"] == "healthy" else 503
    return JSONResponse(content=health_data, status_code=status_code)


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe - checks if the service is ready to accept requests
    """
    # Check database
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
    except Exception:
        return JSONResponse(
            content={"status": "not_ready", "reason": "database_unavailable"},
            status_code=503
        )
    
    # Check storage
    if not Path(settings.TEMP_STORAGE_PATH).exists():
        return JSONResponse(
            content={"status": "not_ready", "reason": "storage_unavailable"},
            status_code=503
        )
    
    return JSONResponse(
        content={"status": "ready"},
        status_code=200
    )


@router.get("/live")
async def liveness_check():
    """
    Liveness probe - basic check that the service is alive
    """
    return Response(status_code=200)