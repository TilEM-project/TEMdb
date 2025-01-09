#!/bin/bash

set -e

if ! command -v gunicorn &> /dev/null; then
    echo "Error: gunicorn is not installed"
    exit 1
fi

# Get CPU info and get threads per core from system
CORES=$(nproc)
THREADS_PER_CORE=$(lscpu | grep "Thread(s) per core:" | awk '{print $4}')
WORKERS=$((CORES * THREADS_PER_CORE + 1))

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
APP_MODULE=${APP_MODULE:-"run:app"}
LOG_LEVEL=${LOG_LEVEL:-"info"}

echo "=== Server Configuration ==="
echo "Workers: $WORKERS (Cores: $CORES, Threads per core: $THREADS_PER_CORE)"
echo "Host: $HOST:$PORT"
echo "App: $APP_MODULE"
echo "=========================="

# Start Gunicorn with Uvicorn workers
exec gunicorn \
    --bind $HOST:$PORT \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --log-level $LOG_LEVEL \
    --access-logfile - \
    --error-logfile - \
    --reload \
    "$APP_MODULE"