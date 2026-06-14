from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class Problem(Base):
    """
    A coding problem with a title, description, and test cases stored separately.
    """
    __tablename__ = "problems"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)        # Full problem statement
    difficulty  = Column(String(10), default="easy")  # easy / medium / hard
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class TestCase(Base):
    """
    Each problem has multiple test cases.
    The worker runs the submission against ALL of them.
    If any fails → Wrong Answer.
    """
    __tablename__ = "test_cases"

    id         = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, nullable=False, index=True)  # FK to problems.id
    stdin      = Column(Text, nullable=False)   # Input fed to the program
    expected   = Column(Text, nullable=False)   # Expected stdout output
    is_sample  = Column(Integer, default=0)     # 1 = shown to user, 0 = hidden
