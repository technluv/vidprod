"""
Upload scheduler for social media platforms
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import structlog

from api.core.config import settings
from shared.database.connection import get_db
from shared.models.job import Platform, UploadStatus
from worker.tasks.platform_uploaders import PlatformUploader

logger = structlog.get_logger()


class UploadScheduler:
    """Schedule and manage uploads to social media platforms"""
    
    def __init__(self):
        self.platform_uploader = PlatformUploader()
        self.running = False
    
    async def start(self):
        """Start the upload scheduler"""
        self.running = True
        logger.info("Upload scheduler started")
        
        while self.running:
            try:
                await self._process_pending_uploads()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error("Upload scheduler error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def stop(self):
        """Stop the upload scheduler"""
        self.running = False
        logger.info("Upload scheduler stopped")
    
    async def _process_pending_uploads(self):
        """Process pending platform uploads"""
        if not settings.PLATFORM_UPLOAD_ENABLED:
            return
        
        async with get_db() as db:
            # Get pending uploads
            cursor = await db.execute(
                """
                SELECT pu.id, pu.segment_id, pu.platform, pu.retry_count,
                       js.job_id, js.file_path, js.segment_number,
                       j.webhook_url
                FROM platform_uploads pu
                JOIN job_segments js ON pu.segment_id = js.id
                JOIN jobs j ON js.job_id = j.id
                WHERE pu.upload_status IN ('pending', 'scheduled')
                  AND (pu.scheduled_at IS NULL OR pu.scheduled_at <= ?)
                  AND pu.retry_count < ?
                ORDER BY pu.scheduled_at, js.created_at
                LIMIT 10
                """,
                (datetime.utcnow().isoformat(), settings.UPLOAD_RETRY_COUNT)
            )
            
            uploads = await cursor.fetchall()
            
            if uploads:
                logger.info("Found pending uploads", count=len(uploads))
                
                # Process uploads concurrently
                tasks = []
                for upload in uploads:
                    upload_id, segment_id, platform, retry_count, job_id, file_path, segment_number, webhook_url = upload
                    
                    task = asyncio.create_task(
                        self._upload_segment(
                            upload_id, segment_id, Platform(platform),
                            job_id, file_path, segment_number,
                            webhook_url, retry_count
                        )
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _upload_segment(self, upload_id: str, segment_id: str, 
                            platform: Platform, job_id: str, file_path: str,
                            segment_number: int, webhook_url: Optional[str],
                            retry_count: int):
        """Upload a single segment to a platform"""
        try:
            # Update status to uploading
            await self._update_upload_status(upload_id, UploadStatus.UPLOADING)
            
            # Perform the upload
            upload_url = await self.platform_uploader.upload(
                platform, file_path, job_id, segment_number
            )
            
            # Update status to completed
            await self._update_upload_status(
                upload_id, 
                UploadStatus.COMPLETED,
                upload_url=upload_url
            )
            
            logger.info("Segment uploaded successfully",
                       platform=platform.value,
                       job_id=job_id,
                       segment=segment_number)
            
            # Send webhook notification if configured
            if webhook_url:
                from worker.tasks.webhook import WebhookNotifier
                notifier = WebhookNotifier()
                await notifier.send_upload_webhook(
                    job_id, webhook_url, platform.value,
                    segment_number, upload_url
                )
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Upload failed",
                        platform=platform.value,
                        job_id=job_id,
                        segment=segment_number,
                        error=error_msg)
            
            # Schedule retry with exponential backoff
            next_retry = datetime.utcnow() + timedelta(
                seconds=settings.UPLOAD_RETRY_DELAY_SECONDS * (2 ** retry_count)
            )
            
            await self._update_upload_status(
                upload_id,
                UploadStatus.SCHEDULED,
                error=error_msg,
                scheduled_at=next_retry,
                increment_retry=True
            )
    
    async def _update_upload_status(self, upload_id: str, status: UploadStatus,
                                  upload_url: str = None, error: str = None,
                                  scheduled_at: datetime = None,
                                  increment_retry: bool = False):
        """Update platform upload status"""
        async with get_db() as db:
            updates = ["upload_status = ?"]
            params = [status.value]
            
            if status == UploadStatus.COMPLETED:
                updates.append("uploaded_at = ?")
                params.append(datetime.utcnow().isoformat())
            
            if upload_url:
                # Update both platform_uploads and job_segments tables
                await db.execute(
                    """
                    UPDATE job_segments
                    SET upload_status = ?, upload_url = ?, upload_at = ?
                    WHERE id = (SELECT segment_id FROM platform_uploads WHERE id = ?)
                    """,
                    (status.value, upload_url, datetime.utcnow().isoformat(), upload_id)
                )
            
            if error:
                updates.append("last_error = ?")
                params.append(error)
            
            if scheduled_at:
                updates.append("scheduled_at = ?")
                params.append(scheduled_at.isoformat())
            
            if increment_retry:
                updates.append("retry_count = retry_count + 1")
            
            params.append(upload_id)
            
            await db.execute(
                f"""
                UPDATE platform_uploads
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                params
            )
            
            await db.commit()
    
    async def schedule_job_uploads(self, job_id: str, platforms: list, segments: list):
        """Schedule uploads for a completed job"""
        async with get_db() as db:
            for segment in segments:
                for platform in platforms:
                    import uuid
                    upload_id = str(uuid.uuid4())
                    
                    await db.execute(
                        """
                        INSERT INTO platform_uploads (
                            id, segment_id, platform, upload_status, created_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            upload_id,
                            segment.id,
                            platform.value,
                            UploadStatus.PENDING.value,
                            datetime.utcnow().isoformat()
                        )
                    )
            
            await db.commit()
        
        logger.info("Uploads scheduled", 
                   job_id=job_id,
                   segments=len(segments),
                   platforms=[p.value for p in platforms])