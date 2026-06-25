from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, nullable=False, index=True)
    full_name       = Column(String(100), nullable=True)
    email           = Column(String(255), unique=True, nullable=False)
    phone_number    = Column(String(30), nullable=True)
    password        = Column(String(255), nullable=True)
    google_id       = Column(String(255), unique=True, nullable=True, index=True)
    github_id       = Column(String(255), unique=True, nullable=True, index=True)
    is_admin        = Column(Boolean, default=False, nullable=False)
    profile_picture = Column(Text, nullable=True)
    date_of_birth   = Column(String(20), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
