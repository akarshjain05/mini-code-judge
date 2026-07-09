import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["jti"] = str(uuid.uuid4())   # unique token ID for blacklisting
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """Decode a JWT and return the user_id (sub). Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No sub in token")
        return user_id
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def decode_token_full(token: str) -> dict:
    """Decode and return full payload including jti and exp."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    from app.models.user import User
    from app.core.redis_client import is_token_blacklisted

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session",
    )

    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise credentials_error

    # CSRF Protection: Require custom header for state-changing requests
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise HTTPException(status_code=403, detail="CSRF check failed: Missing X-Requested-With header")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        if user_id is None:
            raise credentials_error
        # Check JWT blacklist (covers logged-out tokens)
        if jti and is_token_blacklisted(jti):
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_error
    return user


# Setup tokens (short-lived, used for Google/GitHub signup flows)
SETUP_SECRET = settings.SECRET_KEY + ":setup"

def create_setup_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=30)
    return jwt.encode(payload, SETUP_SECRET, algorithm=settings.ALGORITHM)

def decode_setup_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SETUP_SECRET, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None