"""
Submission endpoints — the core of the entire project.

POST /submissions   → create a submission, push to queue, return immediately
GET  /submissions/{id} → poll for verdict
GET  /submissions      → list current user's submissions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import redis
from rq import Queue

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.models.problem import Problem
from app.schemas.submission import SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])


def get_queue() -> Queue:
    """
    Returns an RQ Queue connected to Redis.
    Jobs pushed here are picked up by the worker process.
    """
    r = redis.from_url(settings.REDIS_URL)
    return Queue("judge", connection=r)


@router.post("", response_model=SubmissionOut, status_code=202)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # Must be logged in
):
    """
    Submit code for judging.

    What happens here:
      1. Validate the problem exists
      2. Save submission to DB with status="pending"
      3. Push job to Redis queue (non-blocking)
      4. Return the submission immediately (status=pending)

    The client then polls GET /submissions/{id} for the verdict.
    202 Accepted = "we got it, but it's not done yet"
    """
    # Check the problem exists
    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail=f"Problem {payload.problem_id} not found")

    # Save to DB — status starts as "pending"
    submission = Submission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        code=payload.code,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Push to Redis queue
    # The worker will call judge_submission(submission.id) asynchronously
    try:
        q = get_queue()
        q.enqueue(
            "app.worker.judge.judge_submission",  # String path avoids circular imports
            submission.id,
            job_timeout=60,   # Worker has 60s total before RQ kills the job
        )
    except Exception as e:
        # If Redis is down, mark as error rather than silently losing the job
        submission.status = "queue_error"
        submission.error_output = str(e)
        db.commit()

    return submission


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Poll for the verdict of a specific submission.

    The client calls this every 1-2 seconds after submitting.
    Once status changes from "pending"/"running" to anything else, judging is done.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Users can only see their own submissions
    if submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")

    return submission


@router.get("", response_model=list[SubmissionOut])
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """
    List the current user's submission history (newest first).
    Supports pagination via limit/offset query params.
    """
    submissions = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return submissions
