from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    subject = "Reset your Shyfty password"
    text_body = f"""Hi,

You requested a password reset for your Shyfty account.

Click the link below to set a new password. It expires in 1 hour.

{reset_link}

If you didn't request this, you can safely ignore this email.

— Shyfty
"""
    html_body = f"""<html><body style="font-family:sans-serif;color:#1a1a2e;background:#f9f9f9;padding:32px">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;border:1px solid #e5e7eb">
  <h2 style="margin:0 0 8px;font-size:20px">Reset your password</h2>
  <p style="color:#6b7280;margin:0 0 24px">Click below to set a new password. This link expires in 1 hour.</p>
  <a href="{reset_link}" style="display:inline-block;background:#f97316;color:#fff;font-weight:600;padding:12px 28px;border-radius:8px;text-decoration:none">Reset Password</a>
  <p style="color:#9ca3af;font-size:12px;margin:24px 0 0">If you didn't request this, ignore this email.</p>
</div>
</body></html>"""

    if not _smtp_configured():
        logger.warning("SMTP not configured — password reset link for %s: %s", to_email, reset_link)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.sendmail(settings.smtp_from_address, to_email, msg.as_string())
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        raise
