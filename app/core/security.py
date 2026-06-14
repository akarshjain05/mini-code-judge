from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# bcrypt handles password hashing — never store plain passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tells FastAPI where clients send their token (POST /auth/login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    """Hash a plain password with bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain password against a stored hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT token.
    data should contain {"sub": user_id_as_string}
    """
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency — decodes the JWT and returns the logged-in user.
    Raises 401 if the token is missing, expired, or invalid.

    Usage in a route:
        def my_route(current_user = Depends(get_current_user)):
            ...
    """
    # Import here to avoid circular imports (models → database → security → models)
    from app.models.user import User

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_error

    return user
