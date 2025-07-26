#!/usr/bin/env python3
"""
Simple backend for VidProd - handles video upload and processing with real eye gaze correction
"""
import os
import json
import shutil
import asyncio
import uuid
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import eye gaze correction module
import sys
sys.path.append(str(Path(__file__).parent))
from worker.processors.eye_gaze import EyeGazeCorrector

# Create FastAPI app
app = FastAPI(title="VidProd Simple Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("./uploads")
PROCESSED_DIR = Path("./processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# In-memory job storage (for simplicity)
jobs = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vidprod-simple"}


@app.post("/api/v1/upload")
async def upload_video(
    video: UploadFile = File(...),
    apply_gaze_correction: Optional[bool] = Form(True),
    split_duration: Optional[int] = Form(60)
):
    """Upload a video for processing"""
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_path = UPLOAD_DIR / f"{job_id}_{video.filename}"
        with open(upload_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Create job
        job = {
            "job_id": job_id,
            "status": "processing",
            "filename": video.filename,
            "upload_path": str(upload_path),
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "result": None,
            "error": None
        }
        jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(process_video(job_id))
        
        return JSONResponse(content={
            "job_id": job_id,
            "status": "processing",
            "message": "Video uploaded successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_video_duration(video_path: Path) -> float:
    """Get video duration using FFprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


async def split_video(input_path: Path, output_dir: Path, segment_duration: int = 60) -> List[Dict]:
    """Split video into segments using FFmpeg"""
    segments = []
    duration = await get_video_duration(input_path)
    
    if duration <= 0:
        return segments
    
    # Calculate number of segments
    num_segments = int((duration + segment_duration - 1) // segment_duration)
    
    for i in range(num_segments):
        start_time = i * segment_duration
        segment_filename = f"segment_{i+1}.mp4"
        segment_path = output_dir / segment_filename
        
        # Use FFmpeg to extract segment
        cmd = [
            "ffmpeg", "-i", str(input_path),
            "-ss", str(start_time),
            "-t", str(segment_duration),
            "-c", "copy",
            "-y", str(segment_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and segment_path.exists():
            segments.append({
                "filename": segment_filename,
                "path": str(segment_path),
                "duration": min(segment_duration, duration - start_time),
                "start_time": start_time,
                "end_time": min(start_time + segment_duration, duration),
                "size": segment_path.stat().st_size
            })
    
    return segments


async def process_video(job_id: str):
    """Process video with real eye gaze correction"""
    job = jobs.get(job_id)
    if not job:
        return
    
    try:
        # Initialize eye gaze corrector
        eye_gaze_corrector = EyeGazeCorrector()
        
        # Update progress
        job["progress"] = 10
        
        # Create output directory
        output_dir = PROCESSED_DIR / job_id
        output_dir.mkdir(exist_ok=True)
        
        upload_path = Path(job["upload_path"])
        
        # Get video duration
        video_duration = await get_video_duration(upload_path)
        if video_duration <= 0:
            video_duration = 6  # Fallback for testing
        
        job["progress"] = 20
        
        processed_files = []
        split_duration = 60  # Default to 60 seconds
        
        if video_duration <= split_duration:
            # Process as single file
            output_filename = f"processed_{upload_path.stem}.mp4"
            output_path = output_dir / output_filename
            
            # Apply eye gaze correction
            job["progress"] = 40
            await eye_gaze_corrector.process_video(
                str(upload_path),
                str(output_path),
                intensity=0.7
            )
            job["progress"] = 80
            
            if output_path.exists():
                processed_files.append({
                    "filename": output_filename,
                    "duration": video_duration,
                    "start_time": 0,
                    "end_time": video_duration,
                    "size": output_path.stat().st_size,
                    "gaze_corrected": True
                })
        else:
            # Split into segments and process each
            job["progress"] = 30
            
            # First split the video
            segments = await split_video(upload_path, output_dir, split_duration)
            
            # Process each segment
            for i, segment in enumerate(segments):
                segment_path = Path(segment["path"])
                processed_filename = f"processed_{segment['filename']}"
                processed_path = output_dir / processed_filename
                
                # Apply eye gaze correction to segment
                await eye_gaze_corrector.process_video(
                    str(segment_path),
                    str(processed_path),
                    intensity=0.7
                )
                
                # Remove original segment, keep only processed
                segment_path.unlink(missing_ok=True)
                
                if processed_path.exists():
                    processed_files.append({
                        "filename": processed_filename,
                        "duration": segment["duration"],
                        "start_time": segment["start_time"],
                        "end_time": segment["end_time"],
                        "size": processed_path.stat().st_size,
                        "gaze_corrected": True
                    })
                
                # Update progress
                job["progress"] = 30 + int((i + 1) / len(segments) * 60)
        
        # Update job with results
        job["status"] = "completed"
        job["progress"] = 100
        job["result"] = {
            "processed_videos": processed_files,
            "total_segments": len(processed_files),
            "processing_time": (datetime.now() - datetime.fromisoformat(job["created_at"])).total_seconds(),
            "gaze_corrected": True
        }
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        print(f"Error processing video {job_id}: {e}")


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Add download URLs for completed jobs
    if job["status"] == "completed" and job["result"]:
        for video in job["result"]["processed_videos"]:
            video["download_url"] = f"/api/v1/download/{job_id}/{video['filename']}"
    
    return job


@app.get("/api/v1/download/{job_id}/{filename}")
async def download_video(job_id: str, filename: str):
    """Download processed video"""
    file_path = PROCESSED_DIR / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# Mount frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# Additional route for test page
@app.get("/test")
async def test_page():
    """Serve test page"""
    return FileResponse("test_full_flow.html")


if __name__ == "__main__":
    print("🚀 Starting VidProd Simple Backend...")
    print("📍 Frontend: http://localhost:8000")
    print("📍 API: http://localhost:8000/api/v1")
    print("📍 Health: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)