"""
Video download endpoints
"""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.core.config import settings
from api.services.job_service import JobService

router = APIRouter()
job_service = JobService()


@router.get("/download/{job_id}/{filename}")
async def download_processed_video(job_id: str, filename: str):
    """
    Download a processed video file
    """
    # Get job details
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Job not completed. Current status: {job.status}"
        )
    
    # Construct file path
    file_path = Path(settings.PROCESSED_PATH) / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check - ensure the file is within the allowed directory
    try:
        file_path = file_path.resolve()
        allowed_path = Path(settings.PROCESSED_PATH).resolve()
        if not str(file_path).startswith(str(allowed_path)):
            raise HTTPException(status_code=403, detail="Access forbidden")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/download/{job_id}/all")
async def get_download_links(job_id: str):
    """
    Get all download links for a completed job
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status}"
        )
    
    # Get all processed files
    job_dir = Path(settings.PROCESSED_PATH) / job_id
    if not job_dir.exists():
        return {"files": []}
    
    files = []
    for file_path in job_dir.glob("*.mp4"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "download_url": f"/api/v1/download/{job_id}/{file_path.name}"
        })
    
    return {
        "job_id": job_id,
        "files": files,
        "total_files": len(files)
    }