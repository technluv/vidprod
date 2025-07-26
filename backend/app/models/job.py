from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    
    # File information
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_format = Column(String, nullable=False)
    
    # Job details
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    priority = Column(SQLEnum(JobPriority), default=JobPriority.NORMAL, nullable=False)
    processing_options = Column(Text, nullable=True)  # JSON string
    
    # Progress tracking
    progress = Column(Float, default=0.0)
    current_step = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    output_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)  # seconds
    
    # Webhook
    webhook_url = Column(String, nullable=True)
    webhook_status = Column(String, nullable=True)
    webhook_attempts = Column(Integer, default=0)
    
    # Metadata
    user_id = Column(String, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string