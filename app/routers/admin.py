"""
Admin-only endpoints — restricted to user 'akarsh'.
GET /admin/users        → list all registered users
GET /admin/submissions  → list all submissions with username
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.submission import Submission

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_USERNAME = "akarsh"


def require_admin(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user).first()
    if not user or user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Admin access only")
    return user


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


class SubOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    problem_id: int
    language: str
    verdict: Optional[str]
    status: str
    runtime_ms: Optional[float]
    created_at: Optional[datetime]
    model_config = {"from_attributes": True}


@router.get("/users", response_model=list[UserOut])
def list_users(admin=Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/submissions")
def list_all_submissions(admin=Depends(require_admin), db: Session = Depends(get_db)):
    subs = db.query(Submission).order_by(Submission.id.desc()).all()
    result = []
    for s in subs:
        user = db.query(User).filter(User.id == s.user_id).first()
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": user.username if user else str(s.user_id),
            "problem_id": s.problem_id,
            "language": s.language,
            "verdict": s.verdict,
            "status": s.status,
            "runtime_ms": s.runtime_ms,
            "created_at": s.created_at,
        })
    return result
