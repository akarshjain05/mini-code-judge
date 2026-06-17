from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.problem import Problem, TestCase

router = APIRouter(prefix="/problems", tags=["problems"])


class ProblemCreate(BaseModel):
    title: str
    description: str
    difficulty: Optional[str] = "easy"


class TestCaseCreate(BaseModel):
    stdin: str
    expected: str
    is_sample: bool = False


class ProblemOut(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    model_config = {"from_attributes": True}


class TestCaseOut(BaseModel):
    id: int
    stdin: str
    expected: str
    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProblemOut])
def list_problems(db: Session = Depends(get_db)):
    """List all problems — public, no login needed."""
    return db.query(Problem).all()


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    p = db.query(Problem).filter(Problem.id == problem_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Problem not found")
    return p


@router.get("/{problem_id}/test-cases", response_model=list[TestCaseOut])
def get_sample_test_cases(problem_id: int, db: Session = Depends(get_db)):
    """Get sample (public) test cases for a problem — no login needed."""
    return (
        db.query(TestCase)
        .filter(TestCase.problem_id == problem_id, TestCase.is_sample == 1)
        .all()
    )


@router.post("", response_model=ProblemOut, status_code=201)
def create_problem(
    payload: ProblemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Add a new problem. Admins only."""
    p = Problem(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("/{problem_id}/test-cases", status_code=201)
def add_test_case(
    problem_id: int,
    payload: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Add a test case to a problem. Admins only."""
    if not db.query(Problem).filter(Problem.id == problem_id).first():
        raise HTTPException(status_code=404, detail="Problem not found")

    tc = TestCase(
        problem_id=problem_id,
        stdin=payload.stdin,
        expected=payload.expected,
        is_sample=int(payload.is_sample),
    )
    db.add(tc)
    db.commit()
    return {"message": "Test case added", "problem_id": problem_id}
