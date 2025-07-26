from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job, JobStatus, JobPriority
from app.schemas.job import JobCreate, JobUpdate


class QueueService:
    async def create_job(
        self,
        db: AsyncSession,
        job_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_format: str,
        job_data: JobCreate
    ) -> Job:
        """Create a new job in the queue"""
        job = Job(
            job_id=job_id,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_format=file_format,
            priority=job_data.priority,
            webhook_url=job_data.webhook_url,
            user_id=job_data.user_id,
            processing_options=json.dumps(job_data.processing_options) if job_data.processing_options else None,
            metadata=json.dumps(job_data.metadata) if job_data.metadata else None
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job
    
    async def get_job(self, db: AsyncSession, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        result = await db.execute(
            select(Job).where(Job.job_id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_next_job(self, db: AsyncSession) -> Optional[Job]:
        """Get the next job to process based on priority and creation time"""
        # Check if we're at max concurrent jobs
        processing_count = await db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.PROCESSING)
        )
        if processing_count.scalar() >= settings.max_concurrent_jobs:
            return None
        
        # Get next pending job ordered by priority and creation time
        result = await db.execute(
            select(Job)
            .where(Job.status == JobStatus.PENDING)
            .order_by(
                Job.priority.desc(),  # Higher priority first
                Job.created_at.asc()   # Older jobs first
            )
            .limit(1)
        )
        
        job = result.scalar_one_or_none()
        if job:
            # Update job status to processing
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(job)
        
        return job
    
    async def update_job(
        self,
        db: AsyncSession,
        job_id: str,
        job_update: JobUpdate
    ) -> Optional[Job]:
        """Update a job"""
        job = await self.get_job(db, job_id)
        if not job:
            return None
        
        update_data = job_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        # Handle status transitions
        if job_update.status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.processing_time = (job.completed_at - job.started_at).total_seconds()
        
        await db.commit()
        await db.refresh(job)
        return job
    
    async def list_jobs(
        self,
        db: AsyncSession,
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Job], int]:
        """List jobs with optional filtering"""
        query = select(Job)
        count_query = select(func.count(Job.id))
        
        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)
        
        if user_id:
            query = query.where(Job.user_id == user_id)
            count_query = count_query.where(Job.user_id == user_id)
        
        # Get total count
        total = await db.execute(count_query)
        total_count = total.scalar()
        
        # Get jobs
        query = query.order_by(Job.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        return jobs, total_count
    
    async def get_queue_stats(self, db: AsyncSession) -> dict:
        """Get queue statistics"""
        stats = await db.execute(
            select(
                func.count(Job.id).label("total"),
                func.sum(func.cast(Job.status == JobStatus.PENDING, int)).label("pending"),
                func.sum(func.cast(Job.status == JobStatus.PROCESSING, int)).label("processing"),
                func.sum(func.cast(Job.status == JobStatus.COMPLETED, int)).label("completed"),
                func.sum(func.cast(Job.status == JobStatus.FAILED, int)).label("failed"),
                func.avg(Job.processing_time).label("avg_processing_time")
            )
        )
        
        result = stats.first()
        return {
            "total_jobs": result.total or 0,
            "pending_jobs": result.pending or 0,
            "processing_jobs": result.processing or 0,
            "completed_jobs": result.completed or 0,
            "failed_jobs": result.failed or 0,
            "average_processing_time": result.avg_processing_time,
            "queue_length": (result.pending or 0) + (result.processing or 0)
        }
    
    async def cancel_job(self, db: AsyncSession, job_id: str) -> Optional[Job]:
        """Cancel a job"""
        job = await self.get_job(db, job_id)
        if not job:
            return None
        
        if job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            await db.commit()
            await db.refresh(job)
        
        return job
    
    async def cleanup_old_jobs(self, db: AsyncSession, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            delete(Job).where(
                and_(
                    Job.created_at < cutoff_date,
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
                )
            )
        )
        
        await db.commit()
        return result.rowcount


import json
from datetime import timedelta
from sqlalchemy import delete
from app.core.config import settings

queue_service = QueueService()