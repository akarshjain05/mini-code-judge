from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3: raise ValueError("Username must be at least 3 characters")
        if len(v) > 50: raise ValueError("Username must be 50 characters or fewer")
        if not v.replace("_","").replace("-","").isalnum(): raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6: raise ValueError("Password must be at least 6 characters")
        return v

class GoogleLoginRequest(BaseModel):
    credential: str

class GoogleCompleteSignup(BaseModel):
    setup_token: str
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3: raise ValueError("Username must be at least 3 characters")
        if len(v) > 50: raise ValueError("Username must be 50 characters or fewer")
        if not v.replace("_","").replace("-","").isalnum(): raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6: raise ValueError("Password must be at least 6 characters")
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: Optional[str] = None
    new_password: str

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
