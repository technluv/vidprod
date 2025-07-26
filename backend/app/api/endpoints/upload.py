from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.base import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services.file_service import file_service
from app.services.queue_service import queue_service

router = APIRouter()


@router.post("/upload", response_model=JobResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    priority: str = "normal",
    webhook_url: str = None,
    user_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a video file for processing
    
    - **file**: Video file to upload
    - **priority**: Processing priority (low, normal, high, urgent)
    - **webhook_url**: URL to receive job status updates
    - **user_id**: Optional user identifier
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        file_path, file_format, file_size = await file_service.save_upload_file(file)
        
        # Create job in database
        job_create = JobCreate(
            priority=priority,
            webhook_url=webhook_url,
            user_id=user_id
        )
        
        job = await queue_service.create_job(
            db=db,
            job_id=job_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_format=file_format,
            job_data=job_create
        )
        
        return JobResponse.from_orm(job)
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file if job creation failed
        if 'file_path' in locals():
            file_service.delete_file(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.post("/upload/batch", response_model=list[JobResponse])
async def upload_batch(
    files: list[UploadFile] = File(...),
    priority: str = "normal",
    webhook_url: str = None,
    user_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload multiple video files for processing
    
    - **files**: List of video files to upload
    - **priority**: Processing priority for all files
    - **webhook_url**: URL to receive job status updates
    - **user_id**: Optional user identifier
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")
    
    jobs = []
    failed_uploads = []
    
    for file in files:
        try:
            # Generate job ID
            job_id = str(uuid.uuid4())
            
            # Save uploaded file
            file_path, file_format, file_size = await file_service.save_upload_file(file)
            
            # Create job in database
            job_create = JobCreate(
                priority=priority,
                webhook_url=webhook_url,
                user_id=user_id
            )
            
            job = await queue_service.create_job(
                db=db,
                job_id=job_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_format=file_format,
                job_data=job_create
            )
            
            jobs.append(JobResponse.from_orm(job))
            
        except Exception as e:
            failed_uploads.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    if failed_uploads:
        # Return partial success with error details
        return {
            "successful_uploads": jobs,
            "failed_uploads": failed_uploads
        }
    
    return jobs