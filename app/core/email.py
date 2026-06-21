"""
SMTP email sending for password reset links.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://mini-code-judge-frontend.onrender.com")


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP not configured — SMTP_USER/SMTP_PASSWORD missing")
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your Code Judge password"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False
