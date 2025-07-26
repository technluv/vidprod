"""
Video upload endpoint with async processing
"""
import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from api.core.config import settings
from shared.database.connection import get_db
from shared.models.job import (
    Job, JobStatus, CreateJobRequest, JobResponse, Platform,
    ProcessingOptions, JobMetadata
)
from api.services.job_service import JobService

logger = structlog.get_logger()
router = APIRouter()

# Initialize job service
job_service = JobService()


@router.post("/upload", response_model=JobResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    webhook_url: str = Form(None),
    platforms: str = Form(None),  # Comma-separated list
    metadata: str = Form(None),  # JSON string
    processing_options: str = Form(None),  # JSON string
):
    """
    Upload a video file for processing
    
    - **file**: Video file to upload (required)
    - **webhook_url**: URL to call when processing is complete
    - **platforms**: Comma-separated list of platforms (tiktok,instagram,youtube)
    - **metadata**: JSON string with video metadata
    - **processing_options**: JSON string with processing options
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_VIDEO_EXTENSIONS}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Parse platforms
    platform_list = []
    if platforms:
        try:
            platform_list = [Platform(p.strip()) for p in platforms.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid platform: {e}")
    
    # Parse metadata and processing options
    import json
    
    job_metadata = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            job_metadata = JobMetadata(**metadata_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid metadata: {e}")
    
    proc_options = ProcessingOptions()
    if processing_options:
        try:
            options_dict = json.loads(processing_options)
            proc_options = ProcessingOptions(**options_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid processing options: {e}")
    
    # Generate unique job ID and file path
    job_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{job_id}{file_ext}"
    file_path = Path(settings.TEMP_STORAGE_PATH) / safe_filename
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
        
        logger.info(
            "Video uploaded successfully",
            job_id=job_id,
            filename=file.filename,
            size=file_size,
            path=str(file_path)
        )
        
        # Create job in database
        job = await job_service.create_job(
            job_id=job_id,
            video_path=str(file_path),
            video_filename=file.filename,
            video_size=file_size,
            webhook_url=webhook_url,
            platforms=platform_list,
            metadata=job_metadata,
            processing_options=proc_options
        )
        
        # Queue job for processing (will be picked up by worker)
        logger.info("Job queued for processing", job_id=job_id)
        
        return JobResponse(
            id=job.id,
            status=job.status,
            video_filename=job.video_filename,
            created_at=job.created_at,
            progress=job.progress,
            total_segments=job.total_segments,
            segments=[],
            webhook_url=job.webhook_url,
            platforms=job.platforms
        )
        
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            try:
                os.unlink(file_path)
            except:
                pass
        
        logger.error("Upload failed", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Upload failed")


@router.post("/upload/url", response_model=JobResponse)
async def upload_video_from_url(request: CreateJobRequest):
    """
    Queue a video for processing from a URL
    (For future implementation - download from URL)
    """
    raise HTTPException(
        status_code=501,
        detail="URL upload not yet implemented"
    )