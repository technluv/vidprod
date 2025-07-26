import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings
from app.models.job import Job


class WebhookService:
    def __init__(self):
        self.timeout = settings.webhook_timeout
        self.max_retries = settings.webhook_max_retries
    
    async def send_webhook(self, job: Job, event: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send webhook notification for job event"""
        if not job.webhook_url:
            return True
        
        payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "job": {
                "id": job.job_id,
                "status": job.status.value,
                "progress": job.progress,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
        }
        
        if data:
            payload.update(data)
        
        # Add specific data based on event
        if event == "job.completed":
            payload["job"]["output_path"] = job.output_path
            payload["job"]["processing_time"] = job.processing_time
        elif event == "job.failed":
            payload["job"]["error_message"] = job.error_message
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    job.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    return True
                else:
                    print(f"Webhook failed with status {response.status_code}: {response.text}")
                    return False
                    
            except httpx.TimeoutException:
                print(f"Webhook timeout for job {job.job_id}")
                return False
            except Exception as e:
                print(f"Webhook error for job {job.job_id}: {str(e)}")
                return False
    
    async def send_job_started(self, job: Job) -> bool:
        """Send webhook when job starts processing"""
        return await self.send_webhook(job, "job.started")
    
    async def send_job_progress(self, job: Job) -> bool:
        """Send webhook for job progress update"""
        return await self.send_webhook(job, "job.progress", {
            "current_step": job.current_step
        })
    
    async def send_job_completed(self, job: Job) -> bool:
        """Send webhook when job completes successfully"""
        return await self.send_webhook(job, "job.completed")
    
    async def send_job_failed(self, job: Job) -> bool:
        """Send webhook when job fails"""
        return await self.send_webhook(job, "job.failed")


webhook_service = WebhookService()