"""
Video processing pipeline with eye gaze correction and splitting
"""
import os
import uuid
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import structlog

from api.core.config import settings
from shared.models.job import Job, JobSegment
from shared.database.connection import get_db
from worker.processors.eye_gaze import EyeGazeCorrector

logger = structlog.get_logger()


class VideoProcessor:
    """Main video processing class"""
    
    def __init__(self):
        self.eye_gaze_corrector = EyeGazeCorrector() if settings.EYE_GAZE_ENABLED else None
    
    async def process_video(self, job: Job) -> List[JobSegment]:
        """Process video with eye gaze correction and splitting"""
        try:
            # Step 1: Apply eye gaze correction if enabled
            corrected_path = job.video_path
            if self.eye_gaze_corrector and job.processing_options.eye_gaze_correction:
                logger.info("Applying eye gaze correction", job_id=job.id)
                corrected_path = await self._apply_eye_gaze_correction(
                    job.video_path,
                    job.processing_options.eye_gaze_intensity
                )
            
            # Step 2: Split video into segments
            logger.info("Splitting video into segments", job_id=job.id)
            segments = await self._split_video(
                corrected_path,
                job.id,
                job.processing_options.segment_duration
            )
            
            # Step 3: Save segments to database
            await self._save_segments(job.id, segments)
            
            # Clean up temporary corrected file if created
            if corrected_path != job.video_path and os.path.exists(corrected_path):
                os.unlink(corrected_path)
            
            return segments
            
        except Exception as e:
            logger.error("Video processing failed", job_id=job.id, error=str(e))
            raise
    
    async def _apply_eye_gaze_correction(self, video_path: str, intensity: float) -> str:
        """Apply eye gaze correction to video"""
        output_path = video_path.replace(".mp4", "_corrected.mp4")
        
        try:
            # Process video with eye gaze correction
            await self.eye_gaze_corrector.process_video(
                video_path,
                output_path,
                intensity
            )
            
            return output_path
            
        except Exception as e:
            logger.error("Eye gaze correction failed", error=str(e))
            # Return original video if correction fails
            return video_path
    
    async def _split_video(self, video_path: str, job_id: str, segment_duration: int) -> List[JobSegment]:
        """Split video into segments using FFmpeg"""
        segments = []
        
        # Get video duration
        duration = await self._get_video_duration(video_path)
        if duration == 0:
            raise ValueError("Could not determine video duration")
        
        # Calculate number of segments
        num_segments = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
        
        # Create output directory
        output_dir = Path(settings.TEMP_STORAGE_PATH) / f"segments_{job_id}"
        output_dir.mkdir(exist_ok=True)
        
        # Split video using FFmpeg
        for i in range(num_segments):
            start_time = i * segment_duration
            segment_id = str(uuid.uuid4())
            output_file = output_dir / f"segment_{i+1:03d}.mp4"
            
            # FFmpeg command for splitting
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(start_time),
                "-t", str(segment_duration),
                "-c:v", "libx264",  # Use H.264 codec
                "-c:a", "aac",      # Use AAC audio
                "-movflags", "+faststart",  # Optimize for streaming
                "-y",  # Overwrite output
                str(output_file)
            ]
            
            # Run FFmpeg asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error("FFmpeg split failed", 
                           segment=i+1, 
                           error=stderr.decode())
                continue
            
            # Get segment info
            segment_duration_actual = min(segment_duration, duration - start_time)
            segment_size = output_file.stat().st_size
            
            # Create segment record
            segment = JobSegment(
                id=segment_id,
                job_id=job_id,
                segment_number=i + 1,
                file_path=str(output_file),
                duration=segment_duration_actual,
                size=segment_size
            )
            
            segments.append(segment)
            logger.info("Segment created", 
                       job_id=job_id,
                       segment_number=i+1,
                       duration=segment_duration_actual)
        
        return segments
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFprobe"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            try:
                return float(stdout.decode().strip())
            except ValueError:
                pass
        
        # Fallback: Try with OpenCV
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        if fps > 0 and frame_count > 0:
            return frame_count / fps
        
        return 0
    
    async def _save_segments(self, job_id: str, segments: List[JobSegment]):
        """Save segments to database"""
        async with get_db() as db:
            for segment in segments:
                await db.execute(
                    """
                    INSERT INTO job_segments (
                        id, job_id, segment_number, file_path,
                        duration, size, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        segment.id,
                        segment.job_id,
                        segment.segment_number,
                        segment.file_path,
                        segment.duration,
                        segment.size,
                        segment.created_at.isoformat()
                    )
                )
            
            await db.commit()
        
        logger.info("Segments saved to database", job_id=job_id, count=len(segments))