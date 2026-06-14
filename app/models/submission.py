from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func
from app.core.database import Base


class Submission(Base):
    """
    One row per code submission.

    Lifecycle:
      pending  →  (worker picks it up)
      running  →  accepted / wrong_answer / time_limit / runtime_error / compile_error
    """
    __tablename__ = "submissions"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, nullable=False, index=True)    # FK to users.id
    problem_id   = Column(Integer, nullable=False, index=True)    # FK to problems.id
    language     = Column(String(20), nullable=False)             # "cpp" (add more later)
    code         = Column(Text, nullable=False)                   # The raw source code

    # Verdict — updated by the worker after execution
    status       = Column(String(20), default="pending")          # see lifecycle above
    verdict      = Column(String(30), nullable=True)              # AC / WA / TLE / RE / CE
    runtime_ms   = Column(Float, nullable=True)                   # Execution time in ms
    memory_kb    = Column(Integer, nullable=True)                 # Peak memory used

    # stderr / compiler output — useful for debugging CE
    error_output = Column(Text, nullable=True)

    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    judged_at    = Column(DateTime(timezone=True), nullable=True)
