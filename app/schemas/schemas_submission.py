"""
Pydantic schemas for submission request/response shapes.

SubmissionCreate  → what the client sends (POST /submissions body)
SubmissionOut     → what the API returns (after saving / on poll)
"""

from typing import Literal, Optional
from pydantic import BaseModel, field_validator


# Only languages the judge currently supports
SupportedLanguage = Literal["cpp"]


class SubmissionCreate(BaseModel):
    """Body expected by POST /submissions"""
    problem_id: int
    language: SupportedLanguage    # Pydantic rejects anything not in the Literal — gives 422
    code: str

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code cannot be empty or whitespace only")
        if len(v) > 65_536:   # 64 KB limit — prevents huge uploads
            raise ValueError("Code exceeds maximum length of 64 KB")
        return v

    @field_validator("problem_id")
    @classmethod
    def problem_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("problem_id must be a positive integer")
        return v


class SubmissionOut(BaseModel):
    """
    Response shape for a submission.
    Returned immediately after POST (status=pending) and on every GET poll.

    The client polls GET /submissions/{id} until status is no longer
    'pending' or 'running' — at that point judging is complete.
    """
    id: int
    problem_id: int
    language: str
    code: str

    # These start as None and are filled in by the worker
    status: str                        # pending → running → accepted / wrong_answer / etc.
    verdict: Optional[str] = None      # AC / WA / TLE / RE / CE  (human-readable label)
    runtime_ms: Optional[float] = None
    memory_kb: Optional[int] = None
    error_output: Optional[str] = None # Compiler errors / stderr — shown on CE/RE

    model_config = {"from_attributes": True}
