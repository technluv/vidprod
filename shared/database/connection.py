"""
SQLite database connection manager with async support
"""
import aiosqlite
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import structlog

from api.core.config import settings

logger = structlog.get_logger()

# Global database connection
_db_connection: Optional[aiosqlite.Connection] = None
_db_lock = asyncio.Lock()


async def init_db():
    """Initialize SQLite database with schema"""
    global _db_connection
    
    # Ensure database directory exists
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with _db_lock:
        if _db_connection is None:
            _db_connection = await aiosqlite.connect(
                settings.DB_PATH,
                isolation_level=None  # Auto-commit mode
            )
            
            # Enable WAL mode for better concurrency
            await _db_connection.execute("PRAGMA journal_mode=WAL")
            await _db_connection.execute("PRAGMA synchronous=NORMAL")
            
            # Create tables
            await create_tables()
            
            logger.info("Database initialized", path=settings.DB_PATH)


async def create_tables():
    """Create database tables if they don't exist"""
    async with get_db() as db:
        # Jobs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                video_path TEXT NOT NULL,
                video_filename TEXT NOT NULL,
                video_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                metadata JSON,
                webhook_url TEXT,
                platforms JSON,
                processing_options JSON,
                progress INTEGER DEFAULT 0,
                total_segments INTEGER DEFAULT 0
            )
        """)
        
        # Job segments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS job_segments (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                segment_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                duration REAL,
                size INTEGER,
                platform TEXT,
                upload_status TEXT DEFAULT 'pending',
                upload_at TIMESTAMP,
                upload_error TEXT,
                upload_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(job_id, segment_number, platform)
            )
        """)
        
        # Platform uploads table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS platform_uploads (
                id TEXT PRIMARY KEY,
                segment_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                platform_post_id TEXT,
                upload_status TEXT DEFAULT 'pending',
                scheduled_at TIMESTAMP,
                uploaded_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                metadata JSON,
                FOREIGN KEY (segment_id) REFERENCES job_segments(id) ON DELETE CASCADE
            )
        """)
        
        # Webhooks table for tracking webhook deliveries
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                webhook_url TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload JSON,
                delivery_status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better query performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status 
            ON jobs(status, created_at)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_segments_job_id 
            ON job_segments(job_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_platform_uploads_status 
            ON platform_uploads(upload_status, scheduled_at)
        """)
        
        await db.commit()
        logger.info("Database tables created")


@asynccontextmanager
async def get_db():
    """Get database connection context manager"""
    if _db_connection is None:
        await init_db()
    
    try:
        yield _db_connection
    except Exception as e:
        logger.error("Database error", error=str(e))
        raise


async def close_db():
    """Close database connection"""
    global _db_connection
    
    async with _db_lock:
        if _db_connection:
            await _db_connection.close()
            _db_connection = None
            logger.info("Database connection closed")