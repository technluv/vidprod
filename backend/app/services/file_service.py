import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from app.core.config import settings


class FileService:
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.upload_dir / "pending").mkdir(exist_ok=True)
        (self.upload_dir / "processing").mkdir(exist_ok=True)
        (self.upload_dir / "completed").mkdir(exist_ok=True)
        (self.upload_dir / "failed").mkdir(exist_ok=True)
    
    async def save_upload_file(self, file: UploadFile) -> tuple[str, str, int]:
        """Save uploaded file and return (file_path, file_format, file_size)"""
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()[1:]
        if file_ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_ext}' not allowed. Allowed types: {settings.allowed_extensions}"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_ext}"
        file_path = self.upload_dir / "pending" / filename
        
        # Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.max_upload_size} bytes)"
            )
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            return str(file_path), file_ext, file_size
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    def move_file(self, file_path: str, from_status: str, to_status: str) -> str:
        """Move file between status directories"""
        old_path = Path(file_path)
        new_dir = self.upload_dir / to_status
        new_path = new_dir / old_path.name
        
        try:
            shutil.move(str(old_path), str(new_path))
            return str(new_path)
        except Exception as e:
            raise Exception(f"Failed to move file: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        try:
            Path(file_path).unlink(missing_ok=True)
            return True
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get file information"""
        path = Path(file_path)
        if not path.exists():
            return None
        
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "name": path.name,
            "extension": path.suffix[1:] if path.suffix else ""
        }


file_service = FileService()