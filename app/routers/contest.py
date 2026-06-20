"""
Contest Mode endpoints.
POST /contests              → create a contest (admin only)
GET  /contests              → list all contests
GET  /contests/{id}         → get contest details + leaderboard
POST /contests/{id}/join    → join a contest
POST /contests/{id}/submit  → submit code for a contest problem
GET  /contests/{id}/leaderboard → live leaderboard
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import secrets

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.problem import Problem
from app.models.submission import Submission

router = APIRouter(prefix="/contests", tags=["contests"])


# ── Models ──────────────────────────────────────────────────────────
class Contest(Base):
    __tablename__ = "contests"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    invite_code = Column(String(20), unique=True, nullable=False)
    created_by  = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    starts_at   = Column(DateTime(timezone=True), nullable=False)
    ends_at     = Column(DateTime(timezone=True), nullable=False)
    is_public   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ContestProblem(Base):
    __tablename__ = "contest_problems"
    id         = Column(Integer, primary_key=True)
    contest_id = Column(Integer, nullable=False, index=True)
    problem_id = Column(Integer, nullable=False)
    points     = Column(Integer, default=100)


class ContestParticipant(Base):
    __tablename__ = "contest_participants"
    id         = Column(Integer, primary_key=True)
    contest_id = Column(Integer, nullable=False, index=True)
    user_id    = Column(Integer, nullable=False, index=True)
    joined_at  = Column(DateTime(timezone=True), server_default=func.now())


# ── Schemas ─────────────────────────────────────────────────────────
class ContestCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    duration_minutes: int = 60
    starts_at: datetime
    problem_ids: List[int]
    points_per_problem: Optional[List[int]] = None
    is_public: bool = False


class ContestOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    invite_code: str
    duration_minutes: int
    starts_at: datetime
    ends_at: datetime
    is_public: bool
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Helpers ─────────────────────────────────────────────────────────
def _now():
    return datetime.now(timezone.utc)


def _contest_status(contest: Contest) -> str:
    now = _now()
    starts = contest.starts_at.replace(tzinfo=timezone.utc) if contest.starts_at.tzinfo is None else contest.starts_at
    ends = contest.ends_at.replace(tzinfo=timezone.utc) if contest.ends_at.tzinfo is None else contest.ends_at
    if now < starts:
        return "upcoming"
    if now > ends:
        return "ended"
    return "live"


# ── Routes ──────────────────────────────────────────────────────────
@router.post("", status_code=201)
def create_contest(
    payload: ContestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    for pid in payload.problem_ids:
        if not db.query(Problem).filter(Problem.id == pid).first():
            raise HTTPException(status_code=404, detail=f"Problem {pid} not found")

    starts = payload.starts_at.replace(tzinfo=timezone.utc) if payload.starts_at.tzinfo is None else payload.starts_at
    ends = starts + timedelta(minutes=payload.duration_minutes)

    contest = Contest(
        title=payload.title,
        description=payload.description,
        invite_code=secrets.token_urlsafe(8),
        created_by=current_user.id,
        duration_minutes=payload.duration_minutes,
        starts_at=starts,
        ends_at=ends,
        is_public=payload.is_public,
    )
    db.add(contest)
    db.flush()

    for i, pid in enumerate(payload.problem_ids):
        points = payload.points_per_problem[i] if payload.points_per_problem and i < len(payload.points_per_problem) else 100
        db.add(ContestProblem(contest_id=contest.id, problem_id=pid, points=points))

    db.add(ContestParticipant(contest_id=contest.id, user_id=current_user.id))
    db.commit()
    db.refresh(contest)

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
    # Show every contest to every logged-in user so they can discover and join it
    joined_ids = {p.contest_id for p in db.query(ContestParticipant).filter(
        ContestParticipant.user_id == current_user.id).all()}

    all_contests = db.query(Contest).all()
    result = []
    for c in all_contests:
        result.append({
            "id": c.id,
            "title": c.title,
            "invite_code": c.invite_code,
            "duration_minutes": c.duration_minutes,
            "starts_at": c.starts_at,
            "ends_at": c.ends_at,
            "status": _contest_status(c),
            "is_mine": c.created_by == current_user.id,
            "is_joined": c.id in joined_ids,
        })
    result.sort(key=lambda x: x["starts_at"], reverse=True)
    return result


@router.get("/join/{invite_code}")
def get_contest_by_code(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.invite_code == invite_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found. Check your invite code.")
    return _contest_detail(contest, current_user.id, db)


@router.post("/join/{invite_code}")
def join_contest(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.invite_code == invite_code).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    existing = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest.id,
        ContestParticipant.user_id == current_user.id
    ).first()
    if not existing:
        db.add(ContestParticipant(contest_id=contest.id, user_id=current_user.id))
        db.commit()

    return {"message": "Joined successfully", "contest_id": contest.id}


@router.get("/{contest_id}")
def get_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return _contest_detail(contest, current_user.id, db)


@router.get("/{contest_id}/leaderboard")
def get_leaderboard(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(status_code=404, detail="Contest not found")
    return _build_leaderboard(contest, db)


def _contest_detail(contest, user_id, db):
    problems = db.query(ContestProblem).filter(ContestProblem.contest_id == contest.id).all()
    problem_details = []
    for cp in problems:
        p = db.query(Problem).filter(Problem.id == cp.problem_id).first()
        if p:
            problem_details.append({
                "id": p.id, "title": p.title,
                "difficulty": p.difficulty, "points": cp.points
            })

    participants = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest.id).count()

    is_joined = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest.id,
        ContestParticipant.user_id == user_id).first() is not None

    return {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description,
        "invite_code": contest.invite_code,
        "duration_minutes": contest.duration_minutes,
        "starts_at": contest.starts_at,
        "ends_at": contest.ends_at,
        "status": _contest_status(contest),
        "problems": problem_details,
        "participants": participants,
        "is_joined": is_joined,
        "is_mine": contest.created_by == user_id,
        "leaderboard": _build_leaderboard(contest, db),
    }


def _build_leaderboard(contest, db):
    participants = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest.id).all()
    contest_problems = db.query(ContestProblem).filter(
        ContestProblem.contest_id == contest.id).all()

    starts = contest.starts_at.replace(tzinfo=timezone.utc) if contest.starts_at.tzinfo is None else contest.starts_at
    ends = contest.ends_at.replace(tzinfo=timezone.utc) if contest.ends_at.tzinfo is None else contest.ends_at

    leaderboard = []
    for p in participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        if not user:
            continue
        total_points = 0
        solved = 0
        penalty = 0
        problem_status = {}

        for cp in contest_problems:
            subs = db.query(Submission).filter(
                Submission.user_id == p.user_id,
                Submission.problem_id == cp.problem_id,
                Submission.created_at >= starts,
                Submission.created_at <= ends,
            ).order_by(Submission.created_at.asc()).all()

            wrong = 0
            accepted_at = None
            for s in subs:
                if s.verdict == 'accepted':
                    accepted_at = s.created_at
                    break
                else:
                    wrong += 1

            if accepted_at:
                elapsed = (accepted_at.replace(tzinfo=timezone.utc) - starts).seconds // 60
                total_points += cp.points
                penalty += elapsed + wrong * 20
                solved += 1
                problem_status[cp.problem_id] = {"status": "accepted", "attempts": wrong + 1, "time": elapsed}
            elif wrong > 0:
                problem_status[cp.problem_id] = {"status": "wrong", "attempts": wrong}
            else:
                problem_status[cp.problem_id] = {"status": "none", "attempts": 0}

        leaderboard.append({
            "user_id": p.user_id,
            "username": user.username,
            "points": total_points,
            "solved": solved,
            "penalty": penalty,
            "problem_status": problem_status,
        })

    leaderboard.sort(key=lambda x: (-x["points"], x["penalty"]))
    for i, row in enumerate(leaderboard):
        row["rank"] = i + 1

    return leaderboard
