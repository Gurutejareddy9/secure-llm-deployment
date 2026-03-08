#!/usr/bin/env bash
# Run the application in development mode with hot-reload
set -euo pipefail

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

export APP_DEBUG=true

echo "Starting Secure LLM Gateway in development mode..."
uvicorn src.api_gateway.app:app \
    --host "${APP_HOST:-0.0.0.0}" \
    --port "${APP_PORT:-8000}" \
    --reload \
    --log-level info
