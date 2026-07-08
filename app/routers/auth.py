import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
    create_setup_token, decode_setup_token, decode_token_full,
)
from app.core.email import send_password_reset_email, send_verification_email
from app.core.redis_client import (
    blacklist_token, is_token_blacklisted,
    record_failed_login, clear_failed_logins, is_account_locked, lockout_ttl,
    store_verification_token, consume_verification_token,
)
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserOut, Token, GoogleLoginRequest, GoogleCompleteSignup,
    UserUpdate, PasswordChange, ForgotPasswordRequest, ResetPasswordRequest,
    DeleteAccountRequest, GitHubConnectRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("10/hour")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        password=hash_password(payload.password),
        is_verified=False,
    )
    db.add(user); db.commit(); db.refresh(user)
    # Send verification email (non-blocking — failure doesn't block registration)
    import secrets as _sec
    verify_token = _sec.token_urlsafe(32)
    store_verification_token(verify_token, user.id)
    send_verification_email(user.email, user.username, verify_token)
    user.has_google = False; user.has_github = False; user.has_password = True
    return user


@router.post("/login", response_model=Token)
@limiter.limit("20/minute;100/hour")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form.username

    # Check account lockout before hitting the DB (saves a query on brute force)
    if is_account_locked(identifier):
        ttl = lockout_ttl(identifier)
        mins = max(1, ttl // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Account locked for {mins} more minute(s)."
        )

    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
    if not user or not user.password or not verify_password(form.password, user.password):
        # Record failure (uses username or email as key)
        count = record_failed_login(identifier)
        remaining = max(0, 5 - count)
        msg = "Incorrect username/email or password"
        if remaining <= 2 and remaining > 0:
            msg += f" ({remaining} attempt{'s' if remaining != 1 else ''} remaining before lockout)"
        elif remaining == 0:
            msg = "Too many failed attempts. Account locked for 15 minutes."
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    # Successful login — clear any previous failure counter
    clear_failed_logins(identifier)
    clear_failed_logins(user.username)
    clear_failed_logins(user.email)

    # Require email verification for password-based accounts
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address first. Check your inbox for the verification link.",
            headers={"X-Unverified": "true"},
        )

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Blacklist the current JWT so it can't be reused after logout."""
    auth_header = request.headers.get("Authorization", "")
    raw_token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token_full(raw_token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            import time as _time
            ttl = max(1, int(exp - _time.time()))
            blacklist_token(jti, ttl)
    except Exception:
        pass  # if decoding fails, token is already invalid
    return {"message": "Logged out successfully"}


@router.get("/verify-email/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify a user's email address via the token sent to their inbox."""
    user_id = consume_verification_token(token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Verification link is invalid or has expired.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Email already verified. You can log in."}
    user.is_verified = True
    db.commit()
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification")
@limiter.limit("3/hour")
def resend_verification(request: Request, current_user: User = Depends(get_current_user)):
    """Re-send the verification email (for logged-in but unverified users)."""
    if current_user.is_verified:
        return {"message": "Your email is already verified."}
    import secrets as _sec
    verify_token = _sec.token_urlsafe(32)
    store_verification_token(verify_token, current_user.id)
    send_verification_email(current_user.email, current_user.username, verify_token)
    return {"message": "Verification email sent. Please check your inbox."}


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
        # Google identity confirms the email — mark as verified
        if not user.is_verified:
            user.is_verified = True; db.commit()
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
    user = User(username=payload.username, email=email, password=hash_password(payload.password), google_id=google_user_id, is_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password")
@limiter.limit("5/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
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
# Flow: Frontend → GET /auth/github?state=... → GitHub → GET /auth/github/redirect?code=...
# Backend exchanges code and redirects to frontend with token/setup info in URL hash.
# No frontend /auth/github/callback route needed.

def _github_exchange_code(code: str) -> dict:
    """Exchange a GitHub OAuth code for an access token + user info."""
    token_res = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": f"{settings.API_URL}/auth/github/redirect",
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError(f"No access token: {token_data.get('error_description', token_data)}")

    user_res = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    gh_user = user_res.json()

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
        "login": gh_user.get("login"),
    }


@router.get("/github")
def github_login(state: str = ""):
    """Redirect user to GitHub OAuth. state= can carry 'connect:<jwt>' for account linking."""
    if not settings.GITHUB_CLIENT_ID:
        return RedirectResponse(f"{settings.FRONTEND_URL}/#github-error?msg=GitHub+OAuth+not+configured")
    import urllib.parse as _up
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": "user:email",
        "redirect_uri": f"{settings.API_URL}/auth/github/redirect",
    }
    if state:
        params["state"] = state
    url = "https://github.com/login/oauth/authorize?" + _up.urlencode(params)
    return RedirectResponse(url)


@router.get("/github/redirect")
def github_redirect(code: str = "", error: str = "", state: str = "", db: Session = Depends(get_db)):
    """
    GitHub redirects here after OAuth. Backend exchanges the code and redirects
    to the frontend with result info in the URL hash (works with any static host).
    """
    import urllib.parse as _up

    frontend = settings.FRONTEND_URL

    if error or not code:
        return RedirectResponse(f"{frontend}/#github-error?msg={_up.quote(error or 'No code received')}")

    try:
        gh = _github_exchange_code(code)
    except Exception as e:
        return RedirectResponse(f"{frontend}/#github-error?msg={_up.quote(str(e))}")

    github_id = gh["github_id"]
    email     = gh["email"]

    # ── Connect mode: state = "connect:<user_jwt>" ──────────────────
    if state.startswith("connect:"):
        connect_jwt = state[len("connect:"):]
        try:
            from app.core.security import decode_access_token
            user_id = decode_access_token(connect_jwt)
            current_user = db.query(User).filter(User.id == int(user_id)).first()
            if not current_user:
                raise ValueError("User not found")
        except Exception as e:
            return RedirectResponse(f"{frontend}/#github-error?msg={_up.quote('Session invalid: ' + str(e))}")

        conflict = db.query(User).filter(User.github_id == github_id).first()
        if conflict and conflict.id != current_user.id:
            msg = "This GitHub account is already linked to another Code Judge account."
            return RedirectResponse(f"{frontend}/#github-error?msg={_up.quote(msg)}")

        current_user.github_id = github_id
        db.commit()
        return RedirectResponse(f"{frontend}/#github-connected")

    # ── Login / signup mode ──────────────────────────────────────────
    # 1. Already linked
    existing_by_github = db.query(User).filter(User.github_id == github_id).first()
    if existing_by_github:
        jwt = create_access_token(data={"sub": str(existing_by_github.id)})
        return RedirectResponse(f"{frontend}/#github-login?token={jwt}")

    # 2. Email matches existing account → link and log in
    if email:
        existing_by_email = db.query(User).filter(User.email == email).first()
        if existing_by_email:
            if existing_by_email.github_id and existing_by_email.github_id != github_id:
                msg = f"This email is already linked to a different GitHub account."
                return RedirectResponse(f"{frontend}/#github-error?msg={_up.quote(msg)}")
            existing_by_email.github_id = github_id
            db.commit()
            jwt = create_access_token(data={"sub": str(existing_by_email.id)})
            return RedirectResponse(f"{frontend}/#github-login?token={jwt}")

    # 3. New user → send to frontend for username selection
    setup_token = create_setup_token({"github_id": github_id, "email": email or "", "name": gh["name"] or ""})
    params = _up.urlencode({
        "setup_token": setup_token,
        "suggested": gh["login"] or "",
        "name": gh["name"] or "",
    })
    return RedirectResponse(f"{frontend}/#github-setup?{params}")


@router.post("/complete-github-signup", response_model=Token)
def complete_github_signup(payload: GoogleCompleteSignup, db: Session = Depends(get_db)):
    """Create a new account for a first-time GitHub user after they pick a username."""
    data = decode_setup_token(payload.setup_token)
    if not data or "github_id" not in data:
        raise HTTPException(status_code=400, detail="Invalid or expired setup token")

    github_id = data["github_id"]
    email = data.get("email") or ""
    name  = data.get("name") or ""

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered — try logging in instead")

    user = User(
        username=payload.username,
        email=email or f"gh_{github_id}@noemail.invalid",
        github_id=github_id,
        full_name=name or None,
        is_verified=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    jwt = create_access_token(data={"sub": str(user.id)})
    return {"access_token": jwt, "token_type": "bearer"}


class ResendVerificationRequest(BaseModel):
    identifier: str  # username or email

@router.post("/resend-verification-public")
@limiter.limit("3/hour")
def resend_verification_public(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Public endpoint — resend verification email to an unverified user by username/email."""
    import secrets as _sec
    ident = payload.identifier.strip()
    user = db.query(User).filter(
        (User.username == ident) | (User.email == ident)
    ).first()
    # Always return 200 to prevent email enumeration
    if user and not user.is_verified:
        verify_token = _sec.token_urlsafe(32)
        store_verification_token(verify_token, user.id)
        send_verification_email(user.email, user.username, verify_token)
    return {"message": "If that account exists and is unverified, a verification email has been sent."}