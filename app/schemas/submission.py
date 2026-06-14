from pydantic import BaseModel
from typing import Optional


class SubmissionCreate(BaseModel):
    problem_id: int
    language: str
    code: str


class SubmissionOut(BaseModel):
    id: int
    user_id: int
    problem_id: int
    language: str
    status: str

    verdict: Optional[str] = None
    runtime_ms: Optional[float] = None
    memory_kb: Optional[int] = None
    error_output: Optional[str] = None

    class Config:
        from_attributes = True