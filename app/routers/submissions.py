"""
Submission endpoints.
POST /submissions      → create submission, judge via background poller
GET  /submissions/{id} → poll for verdict
GET  /submissions      → list current user's submissions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.models.problem import Problem, TestCase
from app.schemas.submission import SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])


class SubmissionCreateExtended(BaseModel):
    problem_id: int
    language: str
    code: str
    sample_only: Optional[bool] = False  # True = Run (sample tests only), False = Submit (all tests)


@router.post("", response_model=SubmissionOut, status_code=202)
def create_submission(
    payload: SubmissionCreateExtended,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail=f"Problem {payload.problem_id} not found")

    # For sample_only runs, tag in the code comment so judge knows
    # We store sample_only flag by prefixing status
    submission = Submission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        code=payload.code,
        # Use error_output field temporarily to flag sample_only
        # Judge will check this before running
        status="pending",
        error_output="SAMPLE_ONLY" if payload.sample_only else None,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Try Redis queue first, fall back to direct judging
    try:
        import redis as redis_lib
        from rq import Queue
        from app.core.config import settings
        r = redis_lib.from_url(settings.REDIS_URL)
        q = Queue("judge", connection=r)
        q.enqueue(
            "app.worker.judge.judge_submission",
            submission.id,
            job_timeout=60,
        )
    except Exception:
        # Redis unavailable — judge inline in background thread
        import threading
        from app.worker.judge import judge_submission
        t = threading.Thread(target=judge_submission, args=(submission.id,), daemon=True)
        t.start()

    return submission


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
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
    return (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )