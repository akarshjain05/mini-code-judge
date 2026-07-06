from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

SupportedLanguage = Literal["cpp", "c", "java", "python"]

class SubmissionCreate(BaseModel):
    problem_id: int
    language: SupportedLanguage
    code: str

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code cannot be empty or whitespace only")
        if len(v) > 65_536:
            raise ValueError("Code exceeds maximum length of 64 KB")
        return v

    @field_validator("problem_id")
    @classmethod
    def problem_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("problem_id must be a positive integer")
        return v

class SubmissionOut(BaseModel):
    id: int
    problem_id: int
    language: str
    code: str
    status: str
    verdict: Optional[str] = None
    runtime_ms: Optional[float] = None
    memory_kb: Optional[int] = None
    error_output: Optional[str] = None
    ai_review: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
