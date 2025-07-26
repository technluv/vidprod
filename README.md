# VidProd - Automated Video Production & Upload System

[![GitHub](https://img.shields.io/github/license/technluv/vidprod)](https://github.com/technluv/vidprod)
[![GitHub Stars](https://img.shields.io/github/stars/technluv/vidprod)](https://github.com/technluv/vidprod)

📺 **Repository**: [https://github.com/technluv/vidprod](https://github.com/technluv/vidprod)

VidProd is a lightweight, async video processing system designed for automated video production with eye gaze correction and multi-platform distribution. Optimized for deployment on Fly.io with minimal resource usage.

## Features

- **Async Video Processing**: Queue-based architecture with 24-hour processing window
- **Eye Gaze Correction**: MediaPipe-powered eye contact correction for natural-looking videos
- **Automatic Video Splitting**: FFmpeg-based splitting into 60-second segments
- **Multi-Platform Upload**: Automated uploads to TikTok, Instagram Reels, and YouTube Shorts
- **Webhook Notifications**: Real-time notifications for job completion and upload status
- **Minimal Resource Usage**: Optimized for Fly.io's free tier with < 512MB memory footprint
- **Mobile-Friendly**: Drag-and-drop upload interface optimized for mobile devices

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Upload Frontend│         │ Background Worker│
│   (FastAPI)     │────────►│ (Video Processor)│
└─────────────────┘         └──────────────────┘
         │                           │
         ▼                           ▼
    ┌─────────┐              ┌──────────────┐
    │ SQLite  │              │Platform APIs │
    │  Queue  │              │(TikTok, etc.)│
    └─────────┘              └──────────────┘
```

## Quick Start

### One-Click Setup and Deployment

```bash
# Clone the repository
git clone <repository-url>
cd vidprod

# Run the automation script
./automate-everything.sh

# Or run specific commands:
./automate-everything.sh setup    # Setup local environment
./automate-everything.sh test     # Run tests
./automate-everything.sh start    # Start local server
./automate-everything.sh deploy   # Deploy to Fly.io
./automate-everything.sh all      # Do everything
```

### Manual Setup

1. **Install Dependencies**:
   ```bash
   # System dependencies
   sudo apt-get install ffmpeg python3-pip python3-venv

   # Python environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit .env with your API keys
   ```

3. **Run Locally**:
   ```bash
   # Start API server
   uvicorn api.main:app --reload

   # In another terminal, start worker
   python -m worker.main
   ```

## Deployment

### Fly.io Deployment

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**:
   ```bash
   fly auth login
   ```

3. **Deploy**:
   ```bash
   fly deploy
   ```

### Configuration

The `fly.toml` file is pre-configured with:
- Minimal resource allocation (512MB RAM, 1 shared CPU)
- Persistent volume for SQLite and temporary files
- Health checks and auto-scaling
- Separate processes for web and worker

## API Documentation

### Endpoints

#### Upload Video
```http
POST /api/v1/upload
Content-Type: multipart/form-data

Parameters:
- file: Video file (required)
- webhook_url: URL for completion notification (optional)
- platforms: Comma-separated list (tiktok,instagram,youtube)
- metadata: JSON string with video metadata
- processing_options: JSON string with processing options
```

#### Get Job Status
```http
GET /api/v1/jobs/{job_id}
```

#### List Jobs
```http
GET /api/v1/jobs?status=pending&page=1&page_size=20
```

#### Health Check
```http
GET /health
```

### Webhook Events

#### Job Completed
```json
{
  "event": "job.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "job": {
    "id": "uuid",
    "status": "completed",
    "total_segments": 3,
    "platforms": ["tiktok", "instagram"]
  },
  "segments": [...]
}
```

#### Segment Uploaded
```json
{
  "event": "segment.uploaded",
  "timestamp": "2024-01-01T00:00:00Z",
  "job_id": "uuid",
  "segment": {
    "segment_number": 1,
    "platform": "tiktok",
    "upload_url": "https://tiktok.com/..."
  }
}
```

## Processing Options

### Eye Gaze Correction
```json
{
  "eye_gaze_correction": true,
  "eye_gaze_intensity": 0.7  // 0.0 to 1.0
}
```

### Video Splitting
```json
{
  "segment_duration": 60,  // seconds
  "maintain_quality": true,
  "generate_thumbnails": true
}
```

## Development

### Project Structure
```
vidprod/
├── api/              # FastAPI application
│   ├── routers/      # API endpoints
│   ├── services/     # Business logic
│   └── core/         # Configuration
├── worker/           # Background worker
│   ├── processors/   # Video processing
│   ├── tasks/        # Async tasks
│   └── schedulers/   # Upload scheduling
├── shared/           # Shared models and utilities
├── frontend/         # Minimal upload UI
└── tests/            # Test suite
```

### Running Tests
```bash
# Unit tests
pytest tests/

# E2E tests
python tests/e2e_test.py

# With coverage
pytest --cov=api --cov=worker tests/
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload size | 500 |
| `WORKER_CONCURRENCY` | Concurrent video processing | 1 |
| `EYE_GAZE_ENABLED` | Enable eye gaze correction | true |
| `PLATFORM_UPLOAD_ENABLED` | Enable platform uploads | true |

## Performance

- **Upload Response Time**: < 100ms
- **Processing Time**: < 2 minutes per video
- **Memory Usage**: < 512MB per worker
- **Queue Latency**: < 1 second

## Troubleshooting

### Common Issues

1. **FFmpeg not found**:
   ```bash
   sudo apt-get install ffmpeg
   ```

2. **Memory issues on Fly.io**:
   - Reduce `WORKER_CONCURRENCY` to 1
   - Disable eye gaze correction temporarily
   - Scale up memory in fly.toml

3. **Upload failures**:
   - Check file size limits
   - Verify allowed file extensions
   - Check webhook URL accessibility

### Logs

```bash
# View Fly.io logs
fly logs

# Local logs
tail -f data/logs/vidprod.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: [Report bugs or request features]
- Documentation: See `/docs` directory
- API Docs: Visit `/docs` endpoint when running locally