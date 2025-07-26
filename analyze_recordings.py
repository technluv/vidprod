#!/usr/bin/env python3
"""Analyze recorded and processed video files"""
import os
import json
from pathlib import Path
from datetime import datetime

def analyze_files():
    uploads_dir = Path("./uploads")
    processed_dir = Path("./processed")
    
    print("=== VidProd File Analysis ===\n")
    
    # Analyze uploads
    print("📤 UPLOADED FILES:")
    print("-" * 50)
    
    total_uploads = 0
    total_upload_size = 0
    
    if uploads_dir.exists():
        for file in uploads_dir.iterdir():
            if file.is_file():
                total_uploads += 1
                size = file.stat().st_size
                total_upload_size += size
                
                # Parse job ID from filename
                job_id = file.name.split('_')[0]
                
                print(f"Job ID: {job_id}")
                print(f"  File: {file.name}")
                print(f"  Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
                print(f"  Modified: {datetime.fromtimestamp(file.stat().st_mtime)}")
                print()
    
    # Analyze processed files
    print("\n📥 PROCESSED FILES:")
    print("-" * 50)
    
    total_processed = 0
    total_processed_size = 0
    
    if processed_dir.exists():
        for job_dir in processed_dir.iterdir():
            if job_dir.is_dir():
                print(f"Job ID: {job_dir.name}")
                
                for file in job_dir.iterdir():
                    if file.is_file():
                        total_processed += 1
                        size = file.stat().st_size
                        total_processed_size += size
                        
                        print(f"  Output: {file.name}")
                        print(f"  Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
                        print(f"  Created: {datetime.fromtimestamp(file.stat().st_mtime)}")
                        
                        # Check if it's a copy (mock processing)
                        upload_path = uploads_dir / f"{job_dir.name}_recording.webm"
                        if not upload_path.exists():
                            upload_path = uploads_dir / f"{job_dir.name}_test.webm"
                        
                        if upload_path.exists():
                            if size == upload_path.stat().st_size:
                                print(f"  Status: Mock processed (copy of original)")
                            else:
                                print(f"  Status: Processed (size changed)")
                print()
    
    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 50)
    print(f"Total uploads: {total_uploads} files")
    print(f"Total upload size: {total_upload_size:,} bytes ({total_upload_size/1024/1024:.2f} MB)")
    print(f"Total processed: {total_processed} files")
    print(f"Total processed size: {total_processed_size:,} bytes ({total_processed_size/1024/1024:.2f} MB)")
    
    # Processing ratio
    if total_uploads > 0:
        success_rate = (total_processed / total_uploads) * 100
        print(f"Success rate: {success_rate:.0f}%")
    
    # Docker container check
    print("\n🐳 DOCKER ANALYSIS:")
    print("-" * 50)
    
    # Check if running in container
    if os.path.exists('/.dockerenv'):
        print("Running inside Docker container")
    else:
        print("NOT running in Docker container")
    
    # Check for Dockerfile
    if os.path.exists('Dockerfile'):
        print("Dockerfile found in project")
    
    if os.path.exists('Dockerfile.simple'):
        print("Dockerfile.simple found in project")
    
    # Current working directory
    print(f"\nCurrent directory: {os.getcwd()}")
    print(f"Files are stored locally in:")
    print(f"  - Uploads: {uploads_dir.absolute()}")
    print(f"  - Processed: {processed_dir.absolute()}")
    
    # Eye gaze correction status
    print("\n👁️ EYE GAZE CORRECTION:")
    print("-" * 50)
    print("Status: Using MOCK processing (file copy)")
    print("Real implementation would use:")
    print("  - MediaPipe for face/eye detection")
    print("  - OpenCV for video processing")
    print("  - FFmpeg for video splitting/encoding")

if __name__ == "__main__":
    analyze_files()