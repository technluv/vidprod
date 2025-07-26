"""
Job data models for video processing queue
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadStatus(str, Enum):
    """Upload status enumeration"""
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class Platform(str, Enum):
    """Supported social media platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class ProcessingOptions(BaseModel):
    """Video processing options"""
    eye_gaze_correction: bool = True
    eye_gaze_intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    segment_duration: int = Field(default=60, gt=0)
    output_format: str = "mp4"
    output_codec: str = "h264"
    maintain_quality: bool = True
    generate_thumbnails: bool = True


class JobMetadata(BaseModel):
    """Job metadata"""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    language: Optional[str] = "en"
    visibility: str = "public"


class Job(BaseModel):
    """Job model for video processing"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: JobStatus = JobStatus.PENDING
    video_path: str
    video_filename: str
    video_size: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Optional[JobMetadata] = None
    webhook_url: Optional[str] = None
    platforms: List[Platform] = Field(default_factory=list)
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    progress: int = Field(default=0, ge=0, le=100)
    total_segments: int = 0


class JobSegment(BaseModel):
    """Job segment model for split videos"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    job_id: str
    segment_number: int
    file_path: str
    duration: Optional[float] = None
    size: Optional[int] = None
    platform: Optional[Platform] = None
    upload_status: UploadStatus = UploadStatus.PENDING
    upload_at: Optional[datetime] = None
    upload_error: Optional[str] = None
    upload_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlatformUpload(BaseModel):
    """Platform upload tracking model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    segment_id: str
    platform: Platform
    platform_post_id: Optional[str] = None
    upload_status: UploadStatus = UploadStatus.PENDING
    scheduled_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WebhookDelivery(BaseModel):
    """Webhook delivery tracking model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    job_id: str
    webhook_url: str
    event_type: str
    payload: Dict[str, Any]
    delivery_status: str = "pending"
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None


# Request/Response models for API

class CreateJobRequest(BaseModel):
    """Request model for creating a new job"""
    webhook_url: Optional[str] = None
    platforms: List[Platform] = Field(default_factory=list)
    metadata: Optional[JobMetadata] = None
    processing_options: Optional[ProcessingOptions] = None
    schedule_upload_at: Optional[datetime] = None


class JobResponse(BaseModel):
    """Response model for job details"""
    id: str
    status: JobStatus
    video_filename: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    progress: int
    total_segments: int
    segments: List[JobSegment] = Field(default_factory=list)
    webhook_url: Optional[str] = None
    platforms: List[Platform] = Field(default_factory=list)


class JobListResponse(BaseModel):
    """Response model for job list"""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int