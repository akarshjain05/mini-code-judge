"""
Email sending via Brevo's HTTP API.
Render's free tier blocks outbound traffic on raw SMTP ports (25, 465, 587),
so we send over HTTPS via Brevo's REST API instead of an SMTP socket.
"""
import os
import httpx
import structlog

log = structlog.get_logger()

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")
FROM_NAME = os.environ.get("FROM_NAME", "Code Judge")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://mini-code-judge-frontend.onrender.com")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """Send a password reset link via Brevo. Returns True on success."""
    if not BREVO_API_KEY or not FROM_EMAIL:
        log.warning("Email not configured — BREVO_API_KEY/FROM_EMAIL missing")
        return False

    reset_link = f"{FRONTEND_URL}/#reset-password/{reset_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
      <h2 style="color: #1f6feb; margin-bottom: 4px;">Reset your Code Judge password</h2>
      <p>Hi {username},</p>
      <p>We received a request to reset your password. Click the button below to choose a new one. This link expires in <strong>15 minutes</strong>.</p>
      <p style="text-align:center; margin: 28px 0;">
        <a href="{reset_link}" style="background:#1f6feb;color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block;">Reset Password</a>
      </p>
      <p style="font-size:12px;color:#888;">If you didn't request this, you can safely ignore this email — your password will not be changed.</p>
      <p style="font-size:12px;color:#888;word-break:break-all;">Or copy this link into your browser:<br>{reset_link}</p>
    </div>
    """

    payload = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": to_email, "name": username}],
        "subject": "Reset your Code Judge password",
        "htmlContent": html,
    }

    try:
        resp = httpx.post(
            BREVO_URL,
            headers={
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        if resp.status_code >= 300:
            log.error("Brevo send failed", status_code=resp.status_code, text=resp.text)
            return False
        return True
    except Exception as e:
        log.exception("Failed to send reset email")
        return False


def send_verification_email(to_email: str, username: str, verify_token: str) -> bool:
    """Send an email verification link via Brevo."""
    if not BREVO_API_KEY or not FROM_EMAIL:
        log.warning("Email not configured — skipping verification email")
        return False

    verify_link = f"{FRONTEND_URL}/#verify-email/{verify_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
      <h2 style="color: #1f6feb; margin-bottom: 4px;">Verify your Code Judge email</h2>
      <p>Hi {username},</p>
      <p>Thanks for signing up! Click the button below to verify your email address. This link expires in <strong>24 hours</strong>.</p>
      <p style="text-align:center; margin: 28px 0;">
        <a href="{verify_link}" style="background:#1f6feb;color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-block;">Verify Email</a>
      </p>
      <p style="font-size:12px;color:#888;">If you didn't create a Code Judge account, you can safely ignore this email.</p>
      <p style="font-size:12px;color:#888;word-break:break-all;">Or copy this link:<br>{verify_link}</p>
    </div>
    """

    payload = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": to_email, "name": username}],
        "subject": "Verify your Code Judge email",
        "htmlContent": html,
    }

    try:
        resp = httpx.post(
            BREVO_URL,
            headers={
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        if resp.status_code >= 300:
            log.error("Brevo verification email failed", status_code=resp.status_code, text=resp.text)
            return False
        return True
    except Exception as e:
        log.exception("Failed to send verification email")
        return False