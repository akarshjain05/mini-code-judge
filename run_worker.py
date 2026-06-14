"""
Start the RQ worker. Run this in a SEPARATE terminal alongside uvicorn.

    python run_worker.py

The worker watches the "judge" queue on Redis and processes jobs as they arrive.
Each job calls app.worker.judge.judge_submission(submission_id).
"""

import redis
from rq import Worker, Queue

from app.core.config import settings

if __name__ == "__main__":
    conn = redis.from_url(settings.REDIS_URL)
    q = Queue("judge", connection=conn)
    worker = Worker([q], connection=conn)
    print("Worker started. Waiting for jobs...")
    worker.work()
