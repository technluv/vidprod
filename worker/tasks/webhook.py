"""
Webhook notification system
"""
import json
from datetime import datetime
from typing import List, Dict, Any

import httpx
import structlog

from api.core.config import settings
from shared.models.job import Job, JobSegment
from shared.database.connection import get_db

logger = structlog.get_logger()


class WebhookNotifier:
    """Handle webhook notifications for job events"""
    
    async def send_completion_webhook(self, job: Job, segments: List[JobSegment]):
        """Send webhook notification when job completes"""
        if not job.webhook_url:
            return
        
        payload = {
            "event": "job.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "job": {
                "id": job.id,
                "status": job.status.value,
                "video_filename": job.video_filename,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "total_segments": len(segments),
                "platforms": [p.value for p in job.platforms]
            },
            "segments": [
                {
                    "id": seg.id,
                    "segment_number": seg.segment_number,
                    "duration": seg.duration,
                    "size": seg.size
                }
                for seg in segments
            ]
        }
        
        await self._send_webhook(job.id, job.webhook_url, payload)
    
    async def send_failure_webhook(self, job: Job, error: str):
        """Send webhook notification when job fails"""
        if not job.webhook_url:
            return
        
        payload = {
            "event": "job.failed",
            "timestamp": datetime.utcnow().isoformat(),
            "job": {
                "id": job.id,
                "status": job.status.value,
                "video_filename": job.video_filename,
                "created_at": job.created_at.isoformat(),
                "error": error
            }
        }
        
        await self._send_webhook(job.id, job.webhook_url, payload)
    
    async def send_upload_webhook(self, job_id: str, webhook_url: str, 
                                 platform: str, segment_number: int, 
                                 upload_url: str):
        """Send webhook notification when segment is uploaded"""
        payload = {
            "event": "segment.uploaded",
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "segment": {
                "segment_number": segment_number,
                "platform": platform,
                "upload_url": upload_url
            }
        }
        
        await self._send_webhook(job_id, webhook_url, payload)
    
    async def _send_webhook(self, job_id: str, webhook_url: str, payload: Dict[str, Any]):
        """Send webhook with retry logic"""
        # Save webhook delivery record
        delivery_id = await self._save_webhook_delivery(job_id, webhook_url, payload)
        
        async with httpx.AsyncClient() as client:
            for attempt in range(settings.WEBHOOK_RETRY_COUNT):
                try:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-VidProd-Event": payload["event"],
                            "X-VidProd-Job-ID": job_id
                        },
                        timeout=settings.WEBHOOK_TIMEOUT_SECONDS
                    )
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        # Success
                        await self._update_webhook_delivery(delivery_id, "delivered")
                        logger.info("Webhook delivered", 
                                  job_id=job_id, 
                                  event=payload["event"],
                                  status_code=response.status_code)
                        return
                    else:
                        # Non-success status code
                        error = f"HTTP {response.status_code}: {response.text[:200]}"
                        logger.warning("Webhook delivery failed", 
                                     job_id=job_id,
                                     attempt=attempt + 1,
                                     error=error)
                        
                        if attempt == settings.WEBHOOK_RETRY_COUNT - 1:
                            await self._update_webhook_delivery(delivery_id, "failed", error)
                
                except Exception as e:
                    error = str(e)
                    logger.error("Webhook delivery error", 
                               job_id=job_id,
                               attempt=attempt + 1,
                               error=error)
                    
                    if attempt == settings.WEBHOOK_RETRY_COUNT - 1:
                        await self._update_webhook_delivery(delivery_id, "failed", error)
                
                # Exponential backoff between retries
                if attempt < settings.WEBHOOK_RETRY_COUNT - 1:
                    await asyncio.sleep(2 ** attempt)
    
    async def _save_webhook_delivery(self, job_id: str, webhook_url: str, 
                                   payload: Dict[str, Any]) -> str:
        """Save webhook delivery record"""
        import uuid
        delivery_id = str(uuid.uuid4())
        
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO webhook_deliveries (
                    id, job_id, webhook_url, event_type, payload,
                    delivery_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_id,
                    job_id,
                    webhook_url,
                    payload["event"],
                    json.dumps(payload),
                    "pending",
                    datetime.utcnow().isoformat()
                )
            )
            await db.commit()
        
        return delivery_id
    
    async def _update_webhook_delivery(self, delivery_id: str, status: str, 
                                     error: str = None):
        """Update webhook delivery status"""
        async with get_db() as db:
            if status == "delivered":
                await db.execute(
                    """
                    UPDATE webhook_deliveries
                    SET delivery_status = ?, delivered_at = ?
                    WHERE id = ?
                    """,
                    (status, datetime.utcnow().isoformat(), delivery_id)
                )
            else:
                await db.execute(
                    """
                    UPDATE webhook_deliveries
                    SET delivery_status = ?, last_error = ?, retry_count = retry_count + 1
                    WHERE id = ?
                    """,
                    (status, error, delivery_id)
                )
            
            await db.commit()