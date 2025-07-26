"""
Job service for managing video processing jobs
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import structlog

from shared.database.connection import get_db
from shared.models.job import (
    Job, JobStatus, JobSegment, Platform,
    ProcessingOptions, JobMetadata
)

logger = structlog.get_logger()


class JobService:
    """Service for managing jobs in the database"""
    
    async def create_job(
        self,
        job_id: str,
        video_path: str,
        video_filename: str,
        video_size: int,
        webhook_url: Optional[str] = None,
        platforms: Optional[List[Platform]] = None,
        metadata: Optional[JobMetadata] = None,
        processing_options: Optional[ProcessingOptions] = None
    ) -> Job:
        """Create a new job in the database"""
        if processing_options is None:
            processing_options = ProcessingOptions()
        
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO jobs (
                    id, status, video_path, video_filename, video_size,
                    created_at, webhook_url, platforms, metadata, processing_options
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.PENDING,
                    video_path,
                    video_filename,
                    video_size,
                    datetime.utcnow().isoformat(),
                    webhook_url,
                    json.dumps([p.value for p in platforms]) if platforms else "[]",
                    json.dumps(metadata.dict()) if metadata else None,
                    json.dumps(processing_options.dict())
                )
            )
            await db.commit()
        
        job = Job(
            id=job_id,
            status=JobStatus.PENDING,
            video_path=video_path,
            video_filename=video_filename,
            video_size=video_size,
            webhook_url=webhook_url,
            platforms=platforms or [],
            metadata=metadata,
            processing_options=processing_options
        )
        
        logger.info("Job created", job_id=job_id)
        return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT id, status, video_path, video_filename, video_size,
                       created_at, started_at, completed_at, error,
                       metadata, webhook_url, platforms, processing_options,
                       progress, total_segments
                FROM jobs WHERE id = ?
                """,
                (job_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # Parse JSON fields
            metadata = None
            if row[9]:
                metadata = JobMetadata(**json.loads(row[9]))
            
            platforms = []
            if row[11]:
                platforms = [Platform(p) for p in json.loads(row[11])]
            
            processing_options = ProcessingOptions()
            if row[12]:
                processing_options = ProcessingOptions(**json.loads(row[12]))
            
            return Job(
                id=row[0],
                status=JobStatus(row[1]),
                video_path=row[2],
                video_filename=row[3],
                video_size=row[4],
                created_at=datetime.fromisoformat(row[5]),
                started_at=datetime.fromisoformat(row[6]) if row[6] else None,
                completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                error=row[8],
                metadata=metadata,
                webhook_url=row[10],
                platforms=platforms,
                processing_options=processing_options,
                progress=row[13] or 0,
                total_segments=row[14] or 0
            )
    
    async def get_job_segments(self, job_id: str) -> List[JobSegment]:
        """Get all segments for a job"""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT id, job_id, segment_number, file_path, duration,
                       size, platform, upload_status, upload_at, upload_error,
                       upload_url, created_at
                FROM job_segments
                WHERE job_id = ?
                ORDER BY segment_number
                """,
                (job_id,)
            )
            rows = await cursor.fetchall()
            
            segments = []
            for row in rows:
                segments.append(JobSegment(
                    id=row[0],
                    job_id=row[1],
                    segment_number=row[2],
                    file_path=row[3],
                    duration=row[4],
                    size=row[5],
                    platform=Platform(row[6]) if row[6] else None,
                    upload_status=row[7],
                    upload_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    upload_error=row[9],
                    upload_url=row[10],
                    created_at=datetime.fromisoformat(row[11])
                ))
            
            return segments
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Job], int]:
        """List jobs with pagination and filtering"""
        async with get_db() as db:
            # Build query
            where_clause = ""
            params = []
            
            if status:
                where_clause = "WHERE status = ?"
                params.append(status.value)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM jobs {where_clause}"
            cursor = await db.execute(count_query, params)
            total = (await cursor.fetchone())[0]
            
            # Get jobs
            order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
            query = f"""
                SELECT id, status, video_path, video_filename, video_size,
                       created_at, started_at, completed_at, error,
                       metadata, webhook_url, platforms, processing_options,
                       progress, total_segments
                FROM jobs
                {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            jobs = []
            for row in rows:
                # Parse JSON fields
                metadata = None
                if row[9]:
                    metadata = JobMetadata(**json.loads(row[9]))
                
                platforms = []
                if row[11]:
                    platforms = [Platform(p) for p in json.loads(row[11])]
                
                processing_options = ProcessingOptions()
                if row[12]:
                    processing_options = ProcessingOptions(**json.loads(row[12]))
                
                jobs.append(Job(
                    id=row[0],
                    status=JobStatus(row[1]),
                    video_path=row[2],
                    video_filename=row[3],
                    video_size=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    started_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    error=row[8],
                    metadata=metadata,
                    webhook_url=row[10],
                    platforms=platforms,
                    processing_options=processing_options,
                    progress=row[13] or 0,
                    total_segments=row[14] or 0
                ))
            
            return jobs, total
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        progress: Optional[int] = None,
        total_segments: Optional[int] = None
    ):
        """Update job status"""
        async with get_db() as db:
            updates = ["status = ?"]
            params = [status.value]
            
            if status == JobStatus.PROCESSING and not await self._has_started(job_id):
                updates.append("started_at = ?")
                params.append(datetime.utcnow().isoformat())
            
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                updates.append("completed_at = ?")
                params.append(datetime.utcnow().isoformat())
            
            if error is not None:
                updates.append("error = ?")
                params.append(error)
            
            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)
            
            if total_segments is not None:
                updates.append("total_segments = ?")
                params.append(total_segments)
            
            params.append(job_id)
            
            await db.execute(
                f"""
                UPDATE jobs
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                params
            )
            await db.commit()
        
        logger.info("Job status updated", job_id=job_id, status=status)
    
    async def _has_started(self, job_id: str) -> bool:
        """Check if job has already started"""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT started_at FROM jobs WHERE id = ?",
                (job_id,)
            )
            row = await cursor.fetchone()
            return row and row[0] is not None
    
    async def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        """Get pending jobs for processing"""
        jobs, _ = await self.list_jobs(
            status=JobStatus.PENDING,
            limit=limit,
            sort_by="created_at",
            sort_order="asc"
        )
        return jobs