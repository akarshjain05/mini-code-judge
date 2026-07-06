from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.submission import Submission

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/submissions")
def all_submissions_for_leaderboard(db: Session = Depends(get_db)):
    """Return all accepted+attempted submissions with username for leaderboard calculation.
    Excludes 'Run (Samples)' clicks — those only test a subset of cases and
    are never real submissions/attempts."""
    rows = db.query(
        Submission.id,
        Submission.user_id,
        Submission.problem_id,
        Submission.verdict,
        Submission.language,
        Submission.created_at,
        User.username,
    ).join(User, User.id == Submission.user_id).filter(Submission.is_sample_only == False).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": r.username,
            "problem_id": r.problem_id,
            "verdict": r.verdict,
            "language": r.language,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

@router.get("/users")
def all_users_for_leaderboard(db: Session = Depends(get_db)):
    """Return basic public info for all users."""
    users = db.query(User.id, User.username).all()
    return [{"id": u.id, "username": u.username} for u in users]
