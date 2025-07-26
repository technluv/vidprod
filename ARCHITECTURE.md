# VidProd System Architecture

## Overview

VidProd is a lightweight, async video processing system designed for Fly.io deployment with minimal resource usage and maximum efficiency. The system uses a queue-based architecture with SQLite persistence and webhook notifications.

## Architecture Diagram

```
┌─────────────────────┐         ┌──────────────────┐
│   Upload Frontend   │         │  Mobile Device   │
│   (Minimal HTML)    │◄────────┤  (Android)       │
└──────────┬──────────┘         └──────────────────┘
           │
           │ HTTP Upload
           ▼
┌─────────────────────┐         ┌──────────────────┐
│   FastAPI Server    │────────►│  SQLite Queue    │
│   (Upload Only)     │         │  (Persistent)    │
└──────────┬──────────┘         └──────────────────┘
           │
           │ Job Queue
           ▼
┌─────────────────────┐         ┌──────────────────┐
│  Background Worker  │◄────────┤  Job Scheduler   │
│  (Video Processing) │         │  (Cron-based)    │
└──────────┬──────────┘         └──────────────────┘
           │
           ├─────────────┬──────────────┬─────────────┐
           ▼             ▼              ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  FFmpeg  │  │MediaPipe │  │ TikTok   │  │ YouTube  │
    │(Splitter)│  │(Eye Gaze)│  │   API    │  │   API    │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
           │
           ▼
    ┌──────────────┐
    │   Webhooks   │
    │(Notification)│
    └──────────────┘
```

## Components

### 1. Upload Frontend (Minimal Resources)
- **Purpose**: Simple HTML5 upload interface
- **Memory**: < 50MB
- **Features**:
  - Drag & drop upload
  - Progress tracking
  - Mobile-responsive
  - No framework dependencies

### 2. FastAPI Upload Server
- **Purpose**: Handle uploads and queue jobs
- **Memory**: < 100MB
- **Endpoints**:
  - `POST /upload` - Video upload endpoint
  - `GET /status/{job_id}` - Job status check
  - `GET /health` - Health check for Fly.io
- **Features**:
  - Async request handling
  - Multipart upload support
  - Job queuing to SQLite
  - Minimal CPU usage

### 3. SQLite Job Queue
- **Purpose**: Persistent job storage
- **Schema**:
  ```sql
  CREATE TABLE jobs (
      id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      video_path TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      started_at TIMESTAMP,
      completed_at TIMESTAMP,
      error TEXT,
      metadata JSON,
      webhook_url TEXT,
      platforms JSON
  );
  
  CREATE TABLE job_segments (
      id TEXT PRIMARY KEY,
      job_id TEXT NOT NULL,
      segment_number INTEGER NOT NULL,
      file_path TEXT NOT NULL,
      duration REAL,
      platform TEXT,
      upload_status TEXT,
      upload_at TIMESTAMP,
      FOREIGN KEY (job_id) REFERENCES jobs(id)
  );
  ```

### 4. Background Worker
- **Purpose**: Process videos asynchronously
- **Memory**: < 512MB (configurable)
- **Processing Pipeline**:
  1. Fetch pending jobs from SQLite
  2. Download video from storage
  3. Apply eye gaze correction
  4. Split into 60-second segments
  5. Queue uploads to platforms
  6. Send webhook notification
  7. Clean up temporary files

### 5. Video Processors
- **FFmpeg Splitter**:
  - 60-second segments
  - Maintain quality
  - Handle transitions
- **MediaPipe Eye Gaze**:
  - Real-time correction
  - Configurable intensity
  - Fallback to no correction if resources limited

### 6. Platform Uploaders
- **Scheduled Uploads**:
  - Rate limit aware
  - Retry mechanism
  - Platform-specific formatting
- **Supported Platforms**:
  - TikTok
  - Instagram Reels
  - YouTube Shorts

## Fly.io Optimization

### Resource Allocation
```toml
[services]
  internal_port = 8000
  protocol = "tcp"
  
  [[services.ports]]
    port = 80
    handlers = ["http"]
  
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[env]
  WORKER_CONCURRENCY = "1"
  MAX_UPLOAD_SIZE = "500MB"
  QUEUE_POLL_INTERVAL = "30"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

### Scaling Strategy
1. **Upload Server**: Always on, minimal resources
2. **Worker**: Scale to zero when idle
3. **Storage**: Use Fly.io volumes for temporary storage
4. **Database**: SQLite on persistent volume

## Security Considerations

### API Security
- Rate limiting per IP
- Upload size limits
- File type validation
- Temporary file cleanup

### Data Privacy
- No permanent video storage
- Automatic cleanup after processing
- Secure API key management
- Webhook URL validation

## Deployment Flow

1. **Build**: Docker multi-stage build
2. **Deploy**: `fly deploy` with optimized config
3. **Scale**: Auto-scale workers based on queue depth
4. **Monitor**: Built-in health checks and metrics

## Performance Targets

- **Upload Response**: < 100ms
- **Queue Latency**: < 1s
- **Processing Time**: < 2 minutes per video
- **Memory Usage**: < 512MB per worker
- **Startup Time**: < 10s

## Error Handling

### Retry Strategy
- Exponential backoff for platform uploads
- Max 3 retries per segment
- Dead letter queue for failed jobs

### Monitoring
- Health endpoint for Fly.io
- Prometheus metrics endpoint
- Structured logging
- Error tracking

## Development vs Production

### Development
- SQLite file-based
- Local file storage
- Mock platform APIs
- Verbose logging

### Production
- SQLite on volume
- Fly.io volumes for temp storage
- Real platform APIs
- JSON structured logs