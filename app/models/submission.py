from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func
from app.core.database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, nullable=False, index=True)
    problem_id   = Column(Integer, nullable=False, index=True)
    language     = Column(String(20), nullable=False)
    code         = Column(Text, nullable=False)
    status       = Column(String(20), default="pending")
    verdict      = Column(String(30), nullable=True)
    runtime_ms   = Column(Float, nullable=True)
    memory_kb    = Column(Integer, nullable=True)
    error_output = Column(Text, nullable=True)
    ai_review    = Column(Text, nullable=True)   # cached AI review
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    judged_at    = Column(DateTime(timezone=True), nullable=True)
