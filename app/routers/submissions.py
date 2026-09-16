"""
Submission endpoints.
POST /submissions      → create submission, judge via background thread
GET  /submissions/{id} → poll for verdict
GET  /submissions      → list current user's submissions
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from rq import Queue

from app.core.redis_client import get_redis

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate, SubmissionOut
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/submissions", tags=["submissions"])
limiter = Limiter(key_func=get_remote_address)


class SubmissionCreateExtended(SubmissionCreate):
    sample_only: Optional[bool] = False


@router.post("", response_model=SubmissionOut, status_code=202)
@limiter.limit("30/minute")
def create_submission(
    request: Request,
    payload: SubmissionCreateExtended,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    submission, error = SubmissionService.create_submission(
        db=db,
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        code=payload.code,
        is_sample_only=bool(payload.sample_only)
    )
    if error:
        raise HTTPException(status_code=404, detail=error)

    # Enqueue the job durably in Redis using RQ
    q = Queue("judge", connection=get_redis())
    q.enqueue(
        "app.worker.judge.judge_submission",
        submission.id,
        job_timeout=120  # Give it a max of 2 minutes to completely finish everything
    )

    return submission


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    submission = SubmissionService.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    return submission


@router.get("", response_model=list[SubmissionOut])
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = 200,
    offset: int = 0,
):
    return SubmissionService.list_user_submissions(db, current_user.id, limit, offset)
