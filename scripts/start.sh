#!/bin/bash
# Start script for VidProd on Fly.io
# Handles both web and worker processes based on environment

set -e

# Determine which process to run based on FLY_PROCESS_GROUP
if [ "$FLY_PROCESS_GROUP" = "worker" ]; then
    echo "Starting VidProd Worker..."
    exec python -m worker.main
else
    echo "Starting VidProd API Server..."
    exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
fi