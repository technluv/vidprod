from fastapi import APIRouter
from app.api.endpoints import upload, jobs, health

api_router = APIRouter()

# Include routers
api_router.include_router(upload.router, prefix="/api/v1", tags=["upload"])
api_router.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
api_router.include_router(health.router, prefix="/api/v1", tags=["health"])