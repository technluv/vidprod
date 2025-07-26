from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import os
import psutil
from app.db.base import get_db
from app.schemas.health import HealthResponse, ServiceStatus
from app.core.config import settings
from app.services.queue_service import queue_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint
    
    Returns the overall system health and status of various services
    """
    services = {}
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = {
            "status": "healthy",
            "type": "sqlite"
        }
    except Exception as e:
        services["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check file system
    try:
        upload_dir = settings.upload_dir
        if os.path.exists(upload_dir) and os.access(upload_dir, os.W_OK):
            services["filesystem"] = {
                "status": "healthy",
                "upload_dir": upload_dir,
                "writable": True
            }
        else:
            services["filesystem"] = {
                "status": "unhealthy",
                "error": "Upload directory not writable"
            }
    except Exception as e:
        services["filesystem"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check queue
    try:
        stats = await queue_service.get_queue_stats(db)
        services["queue"] = {
            "status": "healthy",
            "pending_jobs": stats["pending_jobs"],
            "processing_jobs": stats["processing_jobs"],
            "queue_length": stats["queue_length"]
        }
    except Exception as e:
        services["queue"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        services["system"] = {
            "status": "healthy",
            "cpu_usage": f"{cpu_percent}%",
            "memory_usage": f"{memory.percent}%",
            "disk_usage": f"{disk.percent}%"
        }
    except:
        services["system"] = {"status": "unknown"}
    
    # Overall status
    overall_status = "healthy"
    for service, info in services.items():
        if info.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        services=services
    )


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint
    
    Returns 200 if the service is ready to accept requests
    """
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        
        # Check file system
        if not os.path.exists(settings.upload_dir):
            return {"status": "not ready", "reason": "Upload directory missing"}
        
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint
    
    Returns 200 if the service is alive
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}