import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
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
from app.core.email import send_password_reset_email
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserOut, Token, GoogleLoginRequest, GoogleCompleteSignup,
    UserUpdate, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest,
    DeleteAccountRequest, GitHubConnectRequest,
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

    from datetime import datetime, timedelta
    from jose import jwt
    reset_token = jwt.encode(
        {"sub": str(user.id), "purpose": "password_reset", "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )

    sent = send_password_reset_email(user.email, user.username, reset_token)
    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Could not send the reset email right now. Please try again shortly or contact the admin.",
        )

    return {"message": f"A password reset link has been sent to {user.email}."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    from jose import JWTError, jwt
    try:
        claims = jwt.decode(payload.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Reset link expired or invalid. Please request a new one.")
    if claims.get("purpose") != "password_reset":
        raise HTTPException(status_code=401, detail="Invalid reset link")
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
    current_user.has_google = current_user.google_id is not None
    current_user.has_github = current_user.github_id is not None
    current_user.has_password = current_user.password is not None
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(payload: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.full_name is not None:
        name = payload.full_name.strip()
        if len(name) > 100:
            raise HTTPException(status_code=400, detail="Full name must be 100 characters or fewer")
        current_user.full_name = name or None
    if payload.date_of_birth is not None:
        current_user.date_of_birth = payload.date_of_birth or None
    if payload.phone_number is not None:
        phone = payload.phone_number.strip()
        if phone and not re.match(r'^\+?[\d\s\-().]{7,20}$', phone):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        current_user.phone_number = phone or None
    if payload.profile_picture is not None:
        pic = payload.profile_picture
        if pic and not pic.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="profile_picture must be a base64 data URL")
        if pic and len(pic) > 300_000:
            raise HTTPException(status_code=400, detail="Profile picture too large (max ~200 KB)")
        current_user.profile_picture = pic or None
    db.commit(); db.refresh(current_user)
    current_user.has_google = current_user.google_id is not None
    current_user.has_github = current_user.github_id is not None
    current_user.has_password = current_user.password is not None
    return current_user


@router.delete("/me")
def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete the calling user's account and all associated data."""
    # Password-based accounts must confirm with their password
    if current_user.password:
        if not payload.password:
            raise HTTPException(status_code=400, detail="Password confirmation is required to delete your account")
        if not verify_password(payload.password, current_user.password):
            raise HTTPException(status_code=400, detail="Incorrect password")

    # Delete submissions (foreign key dependency)
    from app.models.submission import Submission
    db.query(Submission).filter(Submission.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully"}


@router.put("/change-password")
def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    if current_user.password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(payload.current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


# ── GitHub OAuth ──────────────────────────────────────────────────────

def _github_exchange_code(code: str) -> dict:
    """Exchange a GitHub OAuth code for an access token + user info."""
    token_res = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed: could not get access token")

    user_res = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    gh_user = user_res.json()

    # Get primary verified email
    email_res = httpx.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    emails = email_res.json() if email_res.status_code == 200 else []
    primary_email = next(
        (e["email"] for e in emails if e.get("primary") and e.get("verified")),
        gh_user.get("email"),
    )

    return {
        "github_id": str(gh_user["id"]),
        "email": primary_email,
        "name": gh_user.get("name") or gh_user.get("login"),
        "avatar": gh_user.get("avatar_url"),
        "login": gh_user.get("login"),
    }


@router.get("/github")
def github_login():
    """Redirect user to GitHub OAuth authorization page."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        "&scope=user:email"
        f"&redirect_uri={settings.FRONTEND_URL}/auth/github/callback"
    )
    return RedirectResponse(url)


@router.post("/github/callback")
def github_callback(payload: GitHubConnectRequest, db: Session = Depends(get_db)):
    """
    Exchange GitHub OAuth code → JWT.
    Handles: new user, existing user (same email), account already linked.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured")

    gh = _github_exchange_code(payload.code)
    github_id = gh["github_id"]
    email = gh["email"]

    # 1. Already linked to a GitHub account
    existing_by_github = db.query(User).filter(User.github_id == github_id).first()
    if existing_by_github:
        token = create_access_token(data={"sub": str(existing_by_github.id)})
        return {"access_token": token, "token_type": "bearer", "is_new": False}

    # 2. Email matches an existing account → link GitHub to it
    if email:
        existing_by_email = db.query(User).filter(User.email == email).first()
        if existing_by_email:
            if existing_by_email.github_id and existing_by_email.github_id != github_id:
                raise HTTPException(
                    status_code=409,
                    detail="This email is already linked to a different GitHub account."
                )
            existing_by_email.github_id = github_id
            db.commit()
            token = create_access_token(data={"sub": str(existing_by_email.id)})
            return {"access_token": token, "token_type": "bearer", "is_new": False}

    # 3. New user — need to pick a username; return a setup token
    setup_token = create_setup_token({"github_id": github_id, "email": email, "name": gh["name"]})
    return {
        "requires_setup": True,
        "setup_token": setup_token,
        "suggested_username": gh["login"],
        "email": email,
        "name": gh["name"],
    }


@router.post("/complete-github-signup", response_model=Token)
def complete_github_signup(payload: GoogleCompleteSignup, db: Session = Depends(get_db)):
    """Create a new account for a first-time GitHub user after they pick a username."""
    data = decode_setup_token(payload.setup_token)
    if not data or "github_id" not in data:
        raise HTTPException(status_code=400, detail="Invalid or expired setup token")

    github_id = data["github_id"]
    email = data.get("email")
    name = data.get("name")

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered — try logging in instead")

    user = User(
        username=payload.username,
        email=email or f"github_{github_id}@placeholder.invalid",
        github_id=github_id,
        full_name=name,
    )
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/github/connect")
def github_connect(
    payload: GitHubConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect a GitHub account to an already logged-in user."""
    gh = _github_exchange_code(payload.code)
    github_id = gh["github_id"]

    # Check if this GitHub ID is already on another account
    conflict = db.query(User).filter(User.github_id == github_id).first()
    if conflict and conflict.id != current_user.id:
        raise HTTPException(
            status_code=409,
            detail="This GitHub account is already connected to a different Code Judge account."
        )
    current_user.github_id = github_id
    db.commit()
    return {"message": "GitHub connected successfully"}
