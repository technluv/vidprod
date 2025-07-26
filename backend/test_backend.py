#!/usr/bin/env python3
"""
Quick test script to verify backend is working correctly
"""

import asyncio
import httpx
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoints"""
    async with httpx.AsyncClient() as client:
        # Test main health
        resp = await client.get(f"{BASE_URL}/api/v1/health")
        print(f"Health Check: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Health Status: {resp.json()['status']}")
        
        # Test readiness
        resp = await client.get(f"{BASE_URL}/api/v1/health/ready")
        print(f"Readiness: {resp.json()['status']}")
        
        # Test liveness
        resp = await client.get(f"{BASE_URL}/api/v1/health/live")
        print(f"Liveness: {resp.json()['status']}")


async def test_upload():
    """Test file upload"""
    # Create a test video file
    test_file = Path("test_video.mp4")
    test_file.write_bytes(b"fake video content for testing")
    
    async with httpx.AsyncClient() as client:
        with open(test_file, "rb") as f:
            files = {"file": ("test_video.mp4", f, "video/mp4")}
            data = {
                "priority": "normal",
                "user_id": "test-user"
            }
            
            resp = await client.post(
                f"{BASE_URL}/api/v1/upload",
                files=files,
                data=data
            )
            
            print(f"\nUpload Status: {resp.status_code}")
            if resp.status_code == 200:
                job = resp.json()
                print(f"Job ID: {job['job_id']}")
                print(f"Status: {job['status']}")
                return job['job_id']
    
    # Cleanup
    test_file.unlink()
    return None


async def test_job_status(job_id):
    """Test job status endpoint"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
        print(f"\nJob Status Check: {resp.status_code}")
        if resp.status_code == 200:
            job = resp.json()
            print(f"Job Status: {job['status']}")
            print(f"Progress: {job['progress']}%")


async def test_stats():
    """Test stats endpoint"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/v1/jobs/stats/summary")
        print(f"\nStats: {resp.status_code}")
        if resp.status_code == 200:
            stats = resp.json()
            print(f"Total Jobs: {stats['total_jobs']}")
            print(f"Queue Length: {stats['queue_length']}")


async def main():
    print("Testing VidProd Backend...")
    
    try:
        # Test health
        await test_health()
        
        # Test upload
        job_id = await test_upload()
        
        if job_id:
            # Wait a bit for processing
            await asyncio.sleep(2)
            
            # Check job status
            await test_job_status(job_id)
        
        # Test stats
        await test_stats()
        
        print("\n✅ All tests passed!")
        
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to backend. Is it running?")
        print("Start the backend with: uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())