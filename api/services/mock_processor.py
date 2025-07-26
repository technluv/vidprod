"""
Mock video processor for testing WebRTC functionality
"""
import os
import shutil
import time
import asyncio
from pathlib import Path
from typing import Dict, List

from api.core.config import settings


class MockVideoProcessor:
    """Mock video processor that simulates processing without actual video manipulation"""
    
    @staticmethod
    async def process_video(job_id: str, input_path: str, job_data: Dict) -> Dict:
        """
        Mock process video - creates dummy output files
        """
        # Create output directory
        output_dir = Path(settings.PROCESSED_PATH) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate processing delay
        await asyncio.sleep(5)
        
        # For testing, just copy the input file as segments
        # In real implementation, this would use FFmpeg and MediaPipe
        segments = []
        
        # Create 1-minute segments (mock)
        num_segments = 3  # Simulate 3 one-minute segments
        
        for i in range(num_segments):
            segment_filename = f"segment_{i+1}.mp4"
            segment_path = output_dir / segment_filename
            
            # Copy input file as segment (mock)
            shutil.copy2(input_path, segment_path)
            
            segments.append({
                "filename": segment_filename,
                "path": str(segment_path),
                "duration": 60,
                "start_time": i * 60,
                "end_time": (i + 1) * 60,
                "size": segment_path.stat().st_size if segment_path.exists() else 0
            })
            
            # Simulate processing time
            await asyncio.sleep(1)
        
        return {
            "processed_videos": segments,
            "total_segments": len(segments),
            "processing_time": 8.0,  # Mock processing time
            "gaze_corrected": True,
            "output_dir": str(output_dir)
        }
    
    @staticmethod
    async def apply_gaze_correction(video_path: str) -> bool:
        """
        Mock eye gaze correction
        """
        # In real implementation, this would use MediaPipe
        await asyncio.sleep(2)
        return True
    
    @staticmethod
    async def split_video(video_path: str, segment_duration: int = 60) -> List[Dict]:
        """
        Mock video splitting
        """
        # In real implementation, this would use FFmpeg
        await asyncio.sleep(1)
        return [
            {"start": 0, "end": 60, "duration": 60},
            {"start": 60, "end": 120, "duration": 60},
            {"start": 120, "end": 180, "duration": 60}
        ]