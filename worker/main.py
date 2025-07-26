"""
Background worker for video processing
Polls SQLite queue and processes videos asynchronously
"""
import asyncio
import os
import signal
import sys
from datetime import datetime

import structlog

from api.core.config import settings
from api.core.logging import setup_logging
from shared.database.connection import init_db
from shared.models.job import JobStatus
from api.services.job_service import JobService
from worker.processors.video_processor import VideoProcessor
from worker.tasks.webhook import WebhookNotifier
from worker.schedulers.upload_scheduler import UploadScheduler

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()


async def process_job(job_id: str):
    """Process a single job"""
    job_service = JobService()
    video_processor = VideoProcessor()
    webhook_notifier = WebhookNotifier()
    
    try:
        # Update job status to processing
        await job_service.update_job_status(job_id, JobStatus.PROCESSING)
        logger.info("Processing job started", job_id=job_id)
        
        # Get job details
        job = await job_service.get_job(job_id)
        if not job:
            logger.error("Job not found", job_id=job_id)
            return
        
        # Process video
        segments = await video_processor.process_video(job)
        
        # Update job with segments
        await job_service.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100,
            total_segments=len(segments)
        )
        
        logger.info("Job processing completed", job_id=job_id, segments=len(segments))
        
        # Send webhook notification if configured
        if job.webhook_url:
            await webhook_notifier.send_completion_webhook(job, segments)
        
    except Exception as e:
        logger.error("Job processing failed", job_id=job_id, error=str(e))
        await job_service.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e)
        )
        
        # Send failure webhook if configured
        try:
            job = await job_service.get_job(job_id)
            if job and job.webhook_url:
                await webhook_notifier.send_failure_webhook(job, str(e))
        except:
            pass


async def worker_loop():
    """Main worker loop"""
    job_service = JobService()
    upload_scheduler = UploadScheduler()
    
    logger.info("Worker started", 
                poll_interval=settings.QUEUE_POLL_INTERVAL_SECONDS,
                concurrency=settings.WORKER_CONCURRENCY)
    
    # Start upload scheduler
    scheduler_task = asyncio.create_task(upload_scheduler.start())
    
    try:
        while not shutdown_event.is_set():
            try:
                # Get pending jobs
                pending_jobs = await job_service.get_pending_jobs(
                    limit=settings.WORKER_CONCURRENCY
                )
                
                if pending_jobs:
                    logger.info("Found pending jobs", count=len(pending_jobs))
                    
                    # Process jobs concurrently
                    tasks = [
                        asyncio.create_task(process_job(job.id))
                        for job in pending_jobs
                    ]
                    
                    # Wait for all jobs to complete with timeout
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=settings.JOB_TIMEOUT_SECONDS
                    )
                
                # Wait before next poll
                await asyncio.sleep(settings.QUEUE_POLL_INTERVAL_SECONDS)
                
            except asyncio.TimeoutError:
                logger.error("Job processing timeout exceeded")
            except Exception as e:
                logger.error("Worker loop error", error=str(e))
                await asyncio.sleep(5)  # Brief pause on error
                
    finally:
        # Cleanup
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        
        logger.info("Worker stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received", signal=signum)
    shutdown_event.set()


async def main():
    """Main entry point for worker"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Run worker loop
    await worker_loop()


if __name__ == "__main__":
    # Set worker mode environment variable
    os.environ["WORKER_MODE"] = "true"
    
    # Run the worker
    asyncio.run(main())