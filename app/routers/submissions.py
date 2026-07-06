"""
Submission endpoints.
POST /submissions      → create submission, judge via background thread
GET  /submissions/{id} → poll for verdict
GET  /submissions      → list current user's submissions
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import threading

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.submission import Submission
from app.models.problem import Problem
from app.schemas.submission import SubmissionCreate, SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])


class SubmissionCreateExtended(SubmissionCreate):
    sample_only: Optional[bool] = False


@router.post("", response_model=SubmissionOut, status_code=202)
def create_submission(
    payload: SubmissionCreateExtended,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail=f"Problem {payload.problem_id} not found")

    submission = Submission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        language=payload.language,
        code=payload.code,
        status="pending",
        is_sample_only=bool(payload.sample_only),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Always judge in a background thread — no Redis needed
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
    limit: int = 200,
    offset: int = 0,
):
    return (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .filter(Submission.is_sample_only == False)  # "Run (Samples)" is never a real submission
        .order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )