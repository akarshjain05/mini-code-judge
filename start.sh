#!/usr/bin/env bash
# Start the RQ worker in the background
python run_worker.py &

# Start the FastAPI web server in the foreground
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
