"""
Job management endpoints
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from shared.models.job import JobResponse, JobListResponse, JobStatus
from api.services.job_service import JobService

router = APIRouter()
job_service = JobService()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get job details by ID
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    segments = await job_service.get_job_segments(job_id)
    
    return JobResponse(
        id=job.id,
        status=job.status,
        video_filename=job.video_filename,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        progress=job.progress,
        total_segments=job.total_segments,
        segments=segments,
        webhook_url=job.webhook_url,
        platforms=job.platforms
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """
    List jobs with pagination and filtering
    """
    offset = (page - 1) * page_size
    
    jobs, total = await job_service.list_jobs(
        status=status,
        offset=offset,
        limit=page_size,
        sort_by=sort,
        sort_order=order
    )
    
    # Convert to response models
    job_responses = []
    for job in jobs:
        segments = await job_service.get_job_segments(job.id)
        job_responses.append(
            JobResponse(
                id=job.id,
                status=job.status,
                video_filename=job.video_filename,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error=job.error,
                progress=job.progress,
                total_segments=job.total_segments,
                segments=segments,
                webhook_url=job.webhook_url,
                platforms=job.platforms
            )
        )
    
    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a pending or processing job
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    await job_service.update_job_status(
        job_id,
        JobStatus.CANCELLED,
        error="Cancelled by user"
    )
    
    return JSONResponse(
        content={"message": "Job cancelled successfully"},
        status_code=200
    )


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Retry a failed job
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed jobs. Current status: {job.status}"
        )
    
    # Reset job status to pending
    await job_service.update_job_status(job_id, JobStatus.PENDING)
    
    return JSONResponse(
        content={"message": "Job queued for retry"},
        status_code=200
    )