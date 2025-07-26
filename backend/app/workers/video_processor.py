import asyncio
import json
import httpx
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.job import Job, JobStatus
from app.services.queue_service import queue_service
from app.services.webhook_service import webhook_service
from app.services.file_service import file_service
from app.db.base import AsyncSessionLocal


class VideoProcessor:
    def __init__(self):
        self.is_running = False
        self.current_jobs = {}
    
    async def start(self):
        """Start the video processor worker"""
        self.is_running = True
        print("Video processor worker started")
        
        while self.is_running:
            try:
                await self.process_next_job()
            except Exception as e:
                print(f"Error in video processor: {str(e)}")
            
            await asyncio.sleep(settings.worker_check_interval)
    
    async def stop(self):
        """Stop the video processor worker"""
        self.is_running = False
        print("Video processor worker stopped")
    
    async def process_next_job(self):
        """Process the next job in the queue"""
        async with AsyncSessionLocal() as db:
            job = await queue_service.get_next_job(db)
            if not job:
                return
            
            print(f"Processing job {job.job_id}")
            
            try:
                # Send webhook for job started
                await webhook_service.send_job_started(job)
                
                # Move file to processing directory
                new_path = file_service.move_file(
                    job.file_path, "pending", "processing"
                )
                job.file_path = new_path
                
                # Process the video
                output_path = await self.process_video(job, db)
                
                # Update job as completed
                job.status = JobStatus.COMPLETED
                job.output_path = output_path
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                job.processing_time = (job.completed_at - job.started_at).total_seconds()
                
                # Move files
                file_service.move_file(job.file_path, "processing", "completed")
                
                await db.commit()
                
                # Send completion webhook
                await webhook_service.send_job_completed(job)
                
                print(f"Job {job.job_id} completed successfully")
                
            except Exception as e:
                print(f"Error processing job {job.job_id}: {str(e)}")
                
                # Update job as failed
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                
                # Move file to failed directory
                try:
                    file_service.move_file(job.file_path, "processing", "failed")
                except:
                    pass
                
                await db.commit()
                
                # Send failure webhook
                await webhook_service.send_job_failed(job)
    
    async def process_video(self, job: Job, db: AsyncSession) -> str:
        """Process the video file"""
        # Parse processing options
        options = json.loads(job.processing_options) if job.processing_options else {}
        
        # Simulate video processing with progress updates
        steps = [
            ("Analyzing video", 10),
            ("Extracting frames", 30),
            ("Processing frames", 60),
            ("Encoding output", 90),
            ("Finalizing", 100)
        ]
        
        for step_name, progress in steps:
            # Update job progress
            job.current_step = step_name
            job.progress = progress
            await db.commit()
            
            # Send progress webhook
            await webhook_service.send_job_progress(job)
            
            # Simulate processing time
            await asyncio.sleep(2)
        
        # If external API is configured, call it
        if settings.video_processing_api_url:
            output_path = await self.call_external_api(job, options)
        else:
            # Simulate output
            output_path = job.file_path.replace("/processing/", "/completed/").replace(
                f".{job.file_format}", f"_processed.{job.file_format}"
            )
        
        return output_path
    
    async def call_external_api(self, job: Job, options: dict) -> str:
        """Call external video processing API"""
        async with httpx.AsyncClient() as client:
            # Prepare request
            files = {"video": open(job.file_path, "rb")}
            data = {
                "job_id": job.job_id,
                "options": json.dumps(options)
            }
            
            headers = {}
            if settings.video_processing_api_key:
                headers["Authorization"] = f"Bearer {settings.video_processing_api_key}"
            
            # Make request
            response = await client.post(
                f"{settings.video_processing_api_url}/process",
                files=files,
                data=data,
                headers=headers,
                timeout=settings.job_timeout_seconds
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("output_path", job.file_path)


# Global processor instance
video_processor = VideoProcessor()