"""
Admin-only endpoints — restricted to user 'akarsh'.
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


def require_admin(current_user=Depends(get_current_user)):
    if current_user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Admin access only")
    return current_user


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


@router.get("/users", response_model=list[UserOut])
def list_users(
    admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(User.id.asc()).all()


@router.get("/submissions")
def list_all_submissions(
    admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    subs = db.query(Submission).order_by(Submission.id.desc()).all()
    result = []
    for s in subs:
        user = db.query(User).filter(User.id == s.user_id).first()
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": user.username if user else f"user_{s.user_id}",
            "problem_id": s.problem_id,
            "language": s.language,
            "code": s.code,
            "verdict": s.verdict or s.status,
            "status": s.status,
            "runtime_ms": s.runtime_ms,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return result
