from sqlalchemy.orm import Session
from app.models.submission import Submission
from app.models.problem import Problem
from typing import Optional

class SubmissionService:
    @staticmethod
    def create_submission(db: Session, user_id: int, problem_id: int, language: str, code: str, is_sample_only: bool = False):
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return None, f"Problem {problem_id} not found"
        
        submission = Submission(
            user_id=user_id,
            problem_id=problem_id,
            language=language,
            code=code,
            status="pending",
            is_sample_only=is_sample_only,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission, None

    @staticmethod
    def get_submission(db: Session, submission_id: int):
        return db.query(Submission).filter(Submission.id == submission_id).first()

    @staticmethod
    def list_user_submissions(db: Session, user_id: int, limit: int = 200, offset: int = 0):
        return (
            db.query(Submission)
            .filter(Submission.user_id == user_id)
            .filter(Submission.is_sample_only == False)
            .order_by(Submission.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
