#!/usr/bin/env bash
# The worker should be run separately on a Docker-capable server (e.g. AWS)
# python run_worker.py &

# Apply database migrations (creates tables on first deploy, no-op otherwise)
echo "Running Alembic migrations..."
alembic upgrade head

# Start the FastAPI web server in the foreground
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
