from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
from app.core.config import settings
from app.workers.video_processor import video_processor
from app.services.queue_service import queue_service
from app.db.base import AsyncSessionLocal


class WorkerScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.video_processor_task = None
    
    async def start(self):
        """Start the scheduler and workers"""
        # Start video processor as a continuous task
        self.video_processor_task = asyncio.create_task(video_processor.start())
        
        # Schedule cleanup job
        self.scheduler.add_job(
            self.cleanup_old_jobs,
            IntervalTrigger(seconds=settings.worker_cleanup_interval),
            id="cleanup_old_jobs",
            name="Clean up old jobs",
            replace_existing=True
        )
        
        # Schedule health check
        self.scheduler.add_job(
            self.health_check,
            IntervalTrigger(seconds=60),
            id="health_check",
            name="System health check",
            replace_existing=True
        )
        
        self.scheduler.start()
        print("Worker scheduler started")
    
    async def stop(self):
        """Stop the scheduler and workers"""
        # Stop video processor
        await video_processor.stop()
        if self.video_processor_task:
            self.video_processor_task.cancel()
        
        # Stop scheduler
        self.scheduler.shutdown()
        print("Worker scheduler stopped")
    
    async def cleanup_old_jobs(self):
        """Clean up old completed/failed jobs"""
        try:
            async with AsyncSessionLocal() as db:
                deleted_count = await queue_service.cleanup_old_jobs(db, days=7)
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} old jobs")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
    
    async def health_check(self):
        """Perform system health check"""
        try:
            async with AsyncSessionLocal() as db:
                stats = await queue_service.get_queue_stats(db)
                
                # Check for stuck jobs
                if stats["processing_jobs"] > 0:
                    # TODO: Implement stuck job detection and recovery
                    pass
                
                print(f"Health check - Queue: {stats['queue_length']}, "
                      f"Processing: {stats['processing_jobs']}, "
                      f"Completed: {stats['completed_jobs']}")
        except Exception as e:
            print(f"Error during health check: {str(e)}")


# Global scheduler instance
worker_scheduler = WorkerScheduler()