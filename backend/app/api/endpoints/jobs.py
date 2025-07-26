from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.base import get_db
from app.schemas.job import JobResponse, JobListResponse, JobUpdate, JobStatsResponse
from app.services.queue_service import queue_service
from app.models.job import JobStatus

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get job details by ID"""
    job = await queue_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update job status or priority"""
    job = await queue_service.update_job(db, job_id, job_update)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.delete("/jobs/{job_id}", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending or processing job"""
    job = await queue_service.cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List jobs with optional filtering"""
    offset = (page - 1) * page_size
    
    jobs, total = await queue_service.list_jobs(
        db=db,
        status=status,
        user_id=user_id,
        limit=page_size,
        offset=offset
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return JobListResponse(
        jobs=[JobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/jobs/stats/summary", response_model=JobStatsResponse)
async def get_job_stats(
    user_id: Optional[str] = Query(None, description="Filter stats by user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get job queue statistics"""
    # TODO: Add user_id filtering to stats
    stats = await queue_service.get_queue_stats(db)
    return JobStatsResponse(**stats)