import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
    create_setup_token, decode_setup_token,
)
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserOut, Token, GoogleLoginRequest, GoogleCompleteSignup,
    UserUpdate, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(username=payload.username, email=payload.email, password=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form.username
    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
    if not user or not user.password or not verify_password(form.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username/email or password")
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/google")
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = google_id_token.verify_oauth2_token(payload.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    google_user_id = idinfo["sub"]
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    user = db.query(User).filter(User.google_id == google_user_id).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_user_id; db.commit()
    if user:
        token = create_access_token(data={"sub": str(user.id)})
        return {"needs_setup": False, "access_token": token, "token_type": "bearer"}
    base_username = re.sub(r"[^a-zA-Z0-9_-]", "", email.split("@")[0]) or "user"
    if len(base_username) < 3: base_username = (base_username + "user")[:50]
    suggested = base_username[:50]; suffix = 1
    while db.query(User).filter(User.username == suggested).first():
        suffix += 1; suggested = f"{base_username}{suffix}"[:50]
    setup_token = create_setup_token(email=email, google_id=google_user_id)
    return {"needs_setup": True, "setup_token": setup_token, "email": email, "suggested_username": suggested}


@router.post("/complete-google-signup", response_model=Token)
def complete_google_signup(payload: GoogleCompleteSignup, db: Session = Depends(get_db)):
    claims = decode_setup_token(payload.setup_token)
    email = claims["email"]; google_user_id = claims["google_id"]
    if db.query(User).filter(User.google_id == google_user_id).first():
        raise HTTPException(status_code=400, detail="This Google account is already registered")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(username=payload.username, email=email, password=hash_password(payload.password), google_id=google_user_id)
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email")
    # Use setup-token mechanism with purpose=password_reset (15 min expiry)
    from datetime import datetime, timedelta
    from jose import jwt
    reset_token = jwt.encode(
        {"sub": str(user.id), "purpose": "password_reset", "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    return {"reset_token": reset_token, "message": "Copy this token and use it to reset your password"}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    from jose import JWTError, jwt
    try:
        claims = jwt.decode(payload.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Reset token expired or invalid")
    if claims.get("purpose") != "password_reset":
        raise HTTPException(status_code=401, detail="Invalid reset token")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = db.query(User).filter(User.id == int(claims["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.date_of_birth is not None:
        current_user.date_of_birth = payload.date_of_birth or None
    if payload.profile_picture is not None:
        # Only allow data URLs (base64 images) or empty string to clear
        pic = payload.profile_picture
        if pic and not pic.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="profile_picture must be a base64 data URL")
        # Limit size: base64 of 200KB image ~= 280KB string
        if pic and len(pic) > 300_000:
            raise HTTPException(status_code=400, detail="Profile picture too large (max ~200 KB)")
        current_user.profile_picture = pic or None
    db.commit(); db.refresh(current_user)
    return current_user


@router.put("/change-password")
def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    # If user has an existing password, require current_password to match
    if current_user.password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(payload.current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
