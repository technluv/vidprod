# VidProd Backend

A FastAPI-based video processing queue service with minimal dependencies, optimized for deployment on Fly.io.

## Features

- **Video Upload Endpoints**: Accept single or batch video file uploads
- **SQLite Queue Management**: Lightweight job tracking with priority support
- **Background Worker**: APScheduler-based video processing with configurable concurrency
- **Webhook Notifications**: Real-time job status updates
- **Health Check Endpoints**: Comprehensive health monitoring
- **Environment Configuration**: Flexible configuration via environment variables
- **Minimal Dependencies**: Optimized for serverless/edge deployment

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── upload.py      # Video upload endpoints
│   │   │   ├── jobs.py        # Job management endpoints
│   │   │   └── health.py      # Health check endpoints
│   │   └── api.py             # API router configuration
│   ├── core/
│   │   └── config.py          # Settings and configuration
│   ├── db/
│   │   └── base.py            # Database setup
│   ├── models/
│   │   └── job.py             # SQLAlchemy models
│   ├── schemas/
│   │   ├── job.py             # Pydantic schemas for jobs
│   │   └── health.py          # Health check schemas
│   ├── services/
│   │   ├── file_service.py    # File handling
│   │   ├── queue_service.py   # Queue management
│   │   └── webhook_service.py # Webhook notifications
│   ├── workers/
│   │   ├── scheduler.py       # APScheduler setup
│   │   └── video_processor.py # Video processing logic
│   └── main.py                # FastAPI application
├── requirements.txt           # Python dependencies
├── Dockerfile                # Container configuration
├── fly.toml                  # Fly.io deployment config
└── .env.example              # Environment variables template
```

## API Endpoints

### Upload
- `POST /api/v1/upload` - Upload single video file
- `POST /api/v1/upload/batch` - Upload multiple video files

### Jobs
- `GET /api/v1/jobs/{job_id}` - Get job details
- `PATCH /api/v1/jobs/{job_id}` - Update job status/priority
- `DELETE /api/v1/jobs/{job_id}` - Cancel job
- `GET /api/v1/jobs` - List jobs with filtering
- `GET /api/v1/jobs/stats/summary` - Get queue statistics

### Health
- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

## Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Deployment to Fly.io

1. Install Fly CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

2. Login to Fly:
```bash
fly auth login
```

3. Launch the app:
```bash
fly launch
```

4. Set secrets:
```bash
fly secrets set SECRET_KEY=your-secret-key-here
```

5. Deploy:
```bash
fly deploy
```

6. Create persistent volume for uploads:
```bash
fly volumes create vidprod_data --size 10
```

## Environment Variables

Key configuration options:

- `SECRET_KEY`: JWT secret key for security
- `DATABASE_URL`: SQLite database path
- `MAX_UPLOAD_SIZE`: Maximum file size (bytes)
- `MAX_CONCURRENT_JOBS`: Concurrent processing limit
- `WEBHOOK_TIMEOUT`: Webhook request timeout
- `VIDEO_PROCESSING_API_URL`: External processing API (optional)

See `.env.example` for complete list.

## Testing

Run tests with pytest:
```bash
pytest
```

## Docker

Build and run with Docker:
```bash
docker build -t vidprod-backend .
docker run -p 8000:8000 --env-file .env vidprod-backend
```

## Production Considerations

1. **Database**: Consider PostgreSQL for production workloads
2. **Storage**: Use cloud storage (S3, GCS) for video files
3. **Queue**: Consider Redis/RabbitMQ for distributed processing
4. **Monitoring**: Add APM and logging aggregation
5. **Security**: Implement proper authentication and rate limiting