from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

SUPPORTED_LANGUAGES = {"cpp"}


class SubmissionCreate(BaseModel):
    """
    What the client sends to POST /submissions.
    Only these three fields — user_id comes from the JWT token.
    """
    problem_id: int
    language: str
    code: str

    @field_validator("language")
    @classmethod
    def language_must_be_supported(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{v}' not supported. Use: {SUPPORTED_LANGUAGES}")
        return v

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Code cannot be empty")
        if len(v) > 50_000:
            raise ValueError("Code exceeds 50,000 character limit")
        return v


class SubmissionOut(BaseModel):
    """What we send back after creating or fetching a submission."""
    id: int
    user_id: int
    problem_id: int
    language: str
    status: str
    verdict: Optional[str]
    runtime_ms: Optional[float]
    memory_kb: Optional[int]
    error_output: Optional[str]
    created_at: datetime
    judged_at: Optional[datetime]

    model_config = {"from_attributes": True}
