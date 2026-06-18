from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from app.core.database import Base


class User(Base):
    """
    Represents a registered user.
    Each submission is linked to a user via user_id (foreign key).
    """
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50), unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False)
    password   = Column(String(255), nullable=True)   # nullable: Google-only accounts have no password
    google_id  = Column(String(255), unique=True, nullable=True, index=True)
    is_admin   = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
