"""
Pydantic schemas for user-related request/response shapes.

Pydantic validates incoming JSON automatically — if a required field
is missing or the wrong type, FastAPI returns a 422 before your code runs.

Schemas vs Models:
  - SQLAlchemy models  (app/models/)   → define DB tables
  - Pydantic schemas   (app/schemas/)  → define API request/response shapes
  They're kept separate so you never accidentally expose DB internals (like password hashes).
"""

from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    """Body expected by POST /auth/register"""
    username: str
    email: EmailStr          # Pydantic validates email format automatically
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be 50 characters or fewer")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserOut(BaseModel):
    """Response shape for user data — never includes the password hash."""
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}   # Lets Pydantic read SQLAlchemy model attributes


class Token(BaseModel):
    """Response shape for POST /auth/login"""
    access_token: str
    token_type: str = "bearer"
