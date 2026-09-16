from datetime import datetime, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, constr, Field
from typing import List, Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.contest import Contest, ContestProblem, ContestParticipant
from app.models.problem import Problem
from app.models.user import User
from app.models.submission import Submission
from app.services.contest_service import ContestService

router = APIRouter(prefix="/contests", tags=["contests"])
limiter = Limiter(key_func=get_remote_address)


class ContestCreate(BaseModel):
    title: constr(min_length=3, max_length=100)
    description: str = ""
    duration_minutes: int = Field(default=120, ge=5, le=60*24*7)
    starts_at: datetime
    problem_ids: List[int] = Field(min_items=1)
    points_per_problem: Optional[List[int]] = None
    is_public: bool = True


@router.post("", status_code=201)
@limiter.limit("5/minute")
def create_contest(
    request: Request,
    payload: ContestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = ContestService.create_contest(db, payload, current_user.id)
    return {
        "id": contest.id,
        "title": contest.title,
        "invite_code": contest.invite_code,
        "starts_at": contest.starts_at,
        "ends_at": contest.ends_at,
        "duration_minutes": contest.duration_minutes,
        "invite_link": f"/contest/{contest.invite_code}",
    }


@router.get("")
def list_contests(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ContestService.list_contests(db, current_user.id)


@router.get("/join/{invite_code}")
def get_contest_by_code(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.invite_code == invite_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found. Check your invite code.")
    return ContestService.get_contest_detail(db, contest, current_user.id)


@router.post("/join/{invite_code}")
def join_contest(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.invite_code == invite_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    return ContestService.join_contest(db, contest, current_user.id)


@router.get("/{contest_id}")
def get_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return ContestService.get_contest_detail(db, contest, current_user.id)


@router.get("/{contest_id}/leaderboard")
def get_leaderboard(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return ContestService.build_leaderboard(db, contest)
