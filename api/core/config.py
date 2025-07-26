"""
Application configuration using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_ENV: str = Field(default="development", description="Application environment")
    LOG_LEVEL: str = Field(default="info", description="Logging level")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Upload settings
    MAX_UPLOAD_SIZE_MB: int = Field(default=500, description="Maximum upload size in MB")
    UPLOAD_TIMEOUT_SECONDS: int = Field(default=300, description="Upload timeout in seconds")
    ALLOWED_VIDEO_EXTENSIONS: List[str] = Field(
        default=[".mp4", ".mov", ".avi", ".mkv"],
        description="Allowed video file extensions"
    )
    
    # Storage settings
    TEMP_STORAGE_PATH: str = Field(default="/data/temp", description="Temporary storage path")
    PROCESSED_PATH: str = Field(default="/data/processed", description="Processed files storage path")
    DB_PATH: str = Field(default="/data/db/vidprod.db", description="SQLite database path")
    CLEANUP_INTERVAL_HOURS: int = Field(default=1, description="Cleanup interval in hours")
    FILE_RETENTION_HOURS: int = Field(default=24, description="File retention period in hours")
    
    # Worker settings
    WORKER_ENABLED: bool = Field(default=True, description="Enable background worker")
    WORKER_CONCURRENCY: int = Field(default=1, description="Number of concurrent workers")
    QUEUE_POLL_INTERVAL_SECONDS: int = Field(default=30, description="Queue poll interval")
    JOB_TIMEOUT_SECONDS: int = Field(default=600, description="Job processing timeout")
    
    # Video processing settings
    VIDEO_SEGMENT_DURATION: int = Field(default=60, description="Video segment duration in seconds")
    EYE_GAZE_ENABLED: bool = Field(default=True, description="Enable eye gaze correction")
    EYE_GAZE_INTENSITY: float = Field(default=0.7, description="Eye gaze correction intensity")
    OUTPUT_VIDEO_FORMAT: str = Field(default="mp4", description="Output video format")
    OUTPUT_VIDEO_CODEC: str = Field(default="h264", description="Output video codec")
    
    # Platform settings
    PLATFORM_UPLOAD_ENABLED: bool = Field(default=True, description="Enable platform uploads")
    UPLOAD_RETRY_COUNT: int = Field(default=3, description="Upload retry count")
    UPLOAD_RETRY_DELAY_SECONDS: int = Field(default=60, description="Upload retry delay")
    
    # Security settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    
    # Social media API keys (set via environment variables)
    TIKTOK_API_KEY: Optional[str] = Field(default=None, description="TikTok API key")
    TIKTOK_API_SECRET: Optional[str] = Field(default=None, description="TikTok API secret")
    INSTAGRAM_USERNAME: Optional[str] = Field(default=None, description="Instagram username")
    INSTAGRAM_PASSWORD: Optional[str] = Field(default=None, description="Instagram password")
    YOUTUBE_API_KEY: Optional[str] = Field(default=None, description="YouTube API key")
    YOUTUBE_CLIENT_ID: Optional[str] = Field(default=None, description="YouTube client ID")
    YOUTUBE_CLIENT_SECRET: Optional[str] = Field(default=None, description="YouTube client secret")
    
    # Webhook settings
    WEBHOOK_TIMEOUT_SECONDS: int = Field(default=30, description="Webhook timeout")
    WEBHOOK_RETRY_COUNT: int = Field(default=3, description="Webhook retry count")
    
    # Fly.io specific settings
    FLY_APP_NAME: Optional[str] = Field(default=None, description="Fly.io app name")
    FLY_REGION: Optional[str] = Field(default=None, description="Fly.io region")
    PRIMARY_REGION: Optional[str] = Field(default="iad", description="Primary Fly.io region")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.APP_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.APP_ENV == "development"


# Create global settings instance
settings = Settings()