from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    # Application Settings
    app_name: str = "VidProd"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./vidprod.db"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File Upload Settings
    max_upload_size: int = 524288000  # 500MB
    upload_dir: str = "./uploads"
    allowed_extensions: str = "mp4,avi,mov,mkv,webm"
    
    # Queue Settings
    max_concurrent_jobs: int = 3
    job_timeout_seconds: int = 3600
    
    # Worker Settings
    worker_check_interval: int = 10
    worker_cleanup_interval: int = 300
    
    # Webhook Settings
    webhook_timeout: int = 30
    webhook_max_retries: int = 3
    
    # External Services
    video_processing_api_url: Optional[str] = None
    video_processing_api_key: Optional[str] = None
    
    @validator("allowed_extensions")
    def parse_extensions(cls, v):
        return [ext.strip().lower() for ext in v.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()