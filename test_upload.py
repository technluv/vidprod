#!/usr/bin/env python3
"""Test the upload endpoint"""
import requests
import time

# Create a test video file (small dummy data)
with open("test_video.webm", "wb") as f:
    f.write(b"dummy video data for testing")

# Upload the video
print("Uploading test video...")
with open("test_video.webm", "rb") as f:
    files = {"video": ("test.webm", f, "video/webm")}
    data = {
        "apply_gaze_correction": "true",
        "split_duration": "60"
    }
    
    response = requests.post("http://localhost:8000/api/v1/upload", files=files, data=data)
    
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    result = response.json()
    job_id = result["job_id"]
    
    # Check job status
    print(f"\nJob ID: {job_id}")
    
    # Wait for processing
    for i in range(10):
        time.sleep(1)
        status_response = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}")
        if status_response.status_code == 200:
            job_status = status_response.json()
            print(f"Status: {job_status['status']} - Progress: {job_status['progress']}%")
            
            if job_status["status"] == "completed":
                print("\nProcessing complete!")
                print(f"Results: {job_status['result']}")
                
                # Try to download the first processed video
                if job_status["result"]["processed_videos"]:
                    video = job_status["result"]["processed_videos"][0]
                    download_url = video["download_url"]
                    print(f"\nDownloading from: {download_url}")
                    
                    download_response = requests.get(f"http://localhost:8000{download_url}")
                    print(f"Download status: {download_response.status_code}")
                    
                    if download_response.status_code == 200:
                        with open("downloaded_video.mp4", "wb") as f:
                            f.write(download_response.content)
                        print("Video downloaded successfully!")
                break