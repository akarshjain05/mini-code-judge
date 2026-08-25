from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func
from app.core.database import Base

class Contest(Base):
    __tablename__ = "contests"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    invite_code = Column(String(20), unique=True, nullable=False)
    created_by  = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    starts_at   = Column(DateTime(timezone=True), nullable=False)
    ends_at     = Column(DateTime(timezone=True), nullable=False)
    is_public   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

class ContestProblem(Base):
    __tablename__ = "contest_problems"
    id         = Column(Integer, primary_key=True)
    contest_id = Column(Integer, nullable=False, index=True)
    problem_id = Column(Integer, nullable=False)
    points     = Column(Integer, default=100)

class ContestParticipant(Base):
    __tablename__ = "contest_participants"
    id         = Column(Integer, primary_key=True)
    contest_id = Column(Integer, nullable=False, index=True)
    user_id    = Column(Integer, nullable=False, index=True)
    joined_at  = Column(DateTime(timezone=True), server_default=func.now())
