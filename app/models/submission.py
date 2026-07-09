from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, func
from app.core.database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, nullable=False, index=True)
    problem_id     = Column(Integer, nullable=False, index=True)
    language       = Column(String(20), nullable=False)
    code           = Column(Text, nullable=False)
    status         = Column(String(20), default="pending")
    verdict        = Column(String(30), nullable=True)
    runtime_ms     = Column(Float, nullable=True)
    memory_kb      = Column(Integer, nullable=True)
    error_output   = Column(Text, nullable=True)
    ai_review      = Column(Text, nullable=True)   # cached AI review
    # True for "Run (Samples)" clicks — these only test sample cases and must
    # NEVER be treated as a real submission (not shown in My Submissions,
    # not counted in accepted/total stats, not used for leaderboard/acceptance
    # rate calculations, since they only ran a subset of the test cases).
    is_sample_only = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    judged_at      = Column(DateTime(timezone=True), nullable=True)
