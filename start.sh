#!/bin/bash

set -e

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
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

exec python -m uvicorn "$APP_MODULE" \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    --access-logfile - \
    --error-logfile - \
    --reload \
    "$APP_MODULE"
