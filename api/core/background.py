"""
Background tasks for the API server
"""
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import structlog

from api.core.config import settings

logger = structlog.get_logger()


async def cleanup_old_files():
    """Clean up old temporary files"""
    try:
        temp_path = Path(settings.TEMP_STORAGE_PATH)
        if not temp_path.exists():
            return
        
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.FILE_RETENTION_HOURS)
        cleaned_count = 0
        
        for file_path in temp_path.iterdir():
            if file_path.is_file():
                # Check file age
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    try:
                        os.unlink(file_path)
                        cleaned_count += 1
                        logger.info("Cleaned old file", file=str(file_path))
                    except Exception as e:
                        logger.error("Failed to clean file", file=str(file_path), error=str(e))
        
        if cleaned_count > 0:
            logger.info("Cleanup completed", files_cleaned=cleaned_count)
            
    except Exception as e:
        logger.error("Cleanup task failed", error=str(e))


async def start_cleanup_task():
    """Start periodic cleanup task"""
    logger.info("Starting cleanup task", interval_hours=settings.CLEANUP_INTERVAL_HOURS)
    
    while True:
        try:
            await cleanup_old_files()
        except Exception as e:
            logger.error("Cleanup task error", error=str(e))
        
        # Wait for next cleanup interval
        await asyncio.sleep(settings.CLEANUP_INTERVAL_HOURS * 3600)