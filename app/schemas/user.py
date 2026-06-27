from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import re as _re

def _validate_username(v: str) -> str:
    v = v.strip()
    if len(v) < 3:  raise ValueError("Username must be at least 3 characters")
    if len(v) > 50: raise ValueError("Username must be 50 characters or fewer")
    if not _re.match(r'^[a-zA-Z0-9_-]+$', v):
        raise ValueError("Username can only contain letters, numbers, hyphens and underscores")
    return v

def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not _re.search(r'[A-Za-z]', v):
        raise ValueError("Password must contain at least one letter")
    if not _re.search(r'[0-9]', v):
        raise ValueError("Password must contain at least one number")
    return v

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v): return _validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v): return _validate_password(v)

class GoogleLoginRequest(BaseModel):
    credential: str

class GoogleCompleteSignup(BaseModel):
    setup_token: str
    username: str
    password: Optional[str] = None  # optional — Google/GitHub users may skip

    @field_validator("username")
    @classmethod
    def validate_username(cls, v): return _validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v is None or v == "": return v   # blank = no password (social login)
        return _validate_password(v)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: Optional[str] = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v): return _validate_password(v)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None   # required only if user has a password set

class GitHubConnectRequest(BaseModel):
    code: str   # OAuth code from GitHub callback

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    is_admin: bool = False
    profile_picture: Optional[str] = None
    date_of_birth: Optional[str] = None
    has_google: bool = False
    has_github: bool = False
    has_password: bool = True
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"