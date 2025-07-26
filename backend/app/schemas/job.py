from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.job import JobStatus, JobPriority


class JobBase(BaseModel):
    processing_options: Optional[Dict[str, Any]] = None
    priority: JobPriority = JobPriority.NORMAL
    webhook_url: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    progress: Optional[float] = Field(None, ge=0, le=100)
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class JobResponse(JobBase):
    id: int
    job_id: str
    original_filename: str
    file_size: int
    file_format: str
    status: JobStatus
    progress: float
    current_step: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output_path: Optional[str]
    error_message: Optional[str]
    processing_time: Optional[float]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobStatsResponse(BaseModel):
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time: Optional[float]
    queue_length: int