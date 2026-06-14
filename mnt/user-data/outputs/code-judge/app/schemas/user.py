from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """What the client sends to POST /auth/register"""
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """What we send back — never include the password hash"""
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}  # Lets Pydantic read SQLAlchemy models


class Token(BaseModel):
    """Returned after a successful login"""
    access_token: str
    token_type: str = "bearer"
