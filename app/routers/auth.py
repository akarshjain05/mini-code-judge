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
from app.schemas.user import UserRegister, UserOut, Token, GoogleLoginRequest, GoogleCompleteSignup

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    identifier = form.username
    # allow logging in with either username or email
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
    # user.password can be None for accounts created via Google Sign-In that
    # never finished the username/password setup step
    if not user or not user.password or not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/google")
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Verify a Google ID token. If this Google account is already linked to a
    user, log them in directly. If it's brand new, do NOT create an account
    yet — return a short-lived setup_token and force the frontend to collect
    a username + password via POST /auth/complete-google-signup.
    """
    try:
        idinfo = google_id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_user_id = idinfo["sub"]
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # 1. Already linked to this Google account
    user = db.query(User).filter(User.google_id == google_user_id).first()

    # 2. Existing account with the same email -> link it and log in
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_user_id
            db.commit()

    if user:
        token = create_access_token(data={"sub": str(user.id)})
        return {"needs_setup": False, "access_token": token, "token_type": "bearer"}

    # 3. Brand new — don't create the account, require username + password first
    base_username = re.sub(r"[^a-zA-Z0-9_-]", "", email.split("@")[0]) or "user"
    if len(base_username) < 3:
        base_username = (base_username + "user")[:50]
    suggested = base_username[:50]
    suffix = 1
    while db.query(User).filter(User.username == suggested).first():
        suffix += 1
        suggested = f"{base_username}{suffix}"[:50]

    setup_token = create_setup_token(email=email, google_id=google_user_id)
    return {
        "needs_setup": True,
        "setup_token": setup_token,
        "email": email,
        "suggested_username": suggested,
    }


@router.post("/complete-google-signup", response_model=Token)
def complete_google_signup(payload: GoogleCompleteSignup, db: Session = Depends(get_db)):
    claims = decode_setup_token(payload.setup_token)
    email = claims["email"]
    google_user_id = claims["google_id"]

    # Re-check nothing was created in the meantime (race-condition safety)
    if db.query(User).filter(User.google_id == google_user_id).first():
        raise HTTPException(status_code=400, detail="This Google account is already registered")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        email=email,
        password=hash_password(payload.password),
        google_id=google_user_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user's info, including admin status."""
    return current_user
