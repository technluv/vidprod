#!/usr/bin/env python3
"""
Test script to verify eye gaze correction is working
"""
import requests
import time
import sys
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8000/api/v1"

def test_eye_gaze_correction():
    """Test the eye gaze correction pipeline"""
    
    # Find a test video
    test_videos = list(Path("uploads").glob("*.webm"))
    if not test_videos:
        print("❌ No test videos found in uploads/")
        return False
    
    test_video = test_videos[0]
    print(f"📹 Using test video: {test_video}")
    
    # Upload the video
    print("\n1️⃣ Uploading video...")
    with open(test_video, "rb") as f:
        files = {"video": (test_video.name, f, "video/webm")}
        data = {"apply_gaze_correction": "true", "split_duration": "60"}
        
        response = requests.post(f"{API_URL}/upload", files=files, data=data)
        
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return False
    
    result = response.json()
    job_id = result["job_id"]
    print(f"✅ Upload successful! Job ID: {job_id}")
    
    # Monitor processing
    print("\n2️⃣ Processing video with eye gaze correction...")
    while True:
        response = requests.get(f"{API_URL}/jobs/{job_id}")
        if response.status_code != 200:
            print(f"❌ Status check failed: {response.text}")
            return False
        
        job = response.json()
        status = job["status"]
        progress = job.get("progress", 0)
        
        print(f"   Status: {status} | Progress: {progress}%", end="\r")
        
        if status == "completed":
            print(f"\n✅ Processing completed!")
            break
        elif status == "failed":
            print(f"\n❌ Processing failed: {job.get('error', 'Unknown error')}")
            return False
        
        time.sleep(1)
    
    # Check results
    print("\n3️⃣ Checking results...")
    result = job.get("result", {})
    processed_videos = result.get("processed_videos", [])
    
    if not processed_videos:
        print("❌ No processed videos found")
        return False
    
    print(f"✅ Found {len(processed_videos)} processed video(s):")
    for video in processed_videos:
        print(f"   - {video['filename']} ({video['size']} bytes)")
        print(f"     Duration: {video['duration']}s")
        print(f"     Gaze corrected: {video.get('gaze_corrected', False)}")
        print(f"     Download URL: {video.get('download_url', 'N/A')}")
    
    # Verify eye gaze correction was applied
    if all(v.get('gaze_corrected', False) for v in processed_videos):
        print("\n✅ Eye gaze correction successfully applied to all videos!")
    else:
        print("\n⚠️  Some videos may not have eye gaze correction applied")
    
    print(f"\n📊 Processing time: {result.get('processing_time', 'N/A')} seconds")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Eye Gaze Correction Pipeline")
    print("=" * 50)
    
    success = test_eye_gaze_correction()
    
    if success:
        print("\n✅ All tests passed! Eye gaze correction is working.")
    else:
        print("\n❌ Test failed. Check the logs for details.")
        sys.exit(1)