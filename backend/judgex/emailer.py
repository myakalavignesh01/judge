from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib
import ssl

from .config import settings
from .database import SessionLocal
from .models import User, UserNotification


def send_email_message(recipient: str, subject: str, body: str) -> bool:
    if not settings.smtp_host or not settings.smtp_from_email:
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(body)
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20) if settings.smtp_port == 465 else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    with server as smtp:
        if settings.smtp_starttls and settings.smtp_port != 465:
            smtp.starttls(context=context)
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return True


def deliver_otp(recipient: str, code: str, purpose: str) -> None:
    action = "sign in" if purpose == "login" else "reset your JudgeX password"
    try:
        send_email_message(recipient, "Your JudgeX verification code", f"Your code to {action} is {code}. It expires in 10 minutes. If you did not request it, ignore this email.")
    except Exception:
        return


def deliver_notification(notification_id: str) -> None:
    db = SessionLocal()
    try:
        notice = db.get(UserNotification, notification_id)
        if not notice:
            return
        user = db.get(User, notice.user_id)
        if not user or not user.email:
            notice.status = "failed"
            notice.failure_detail = "Recipient account or email is unavailable"
            db.commit()
            return
        if not settings.smtp_host or not settings.smtp_from_email:
            notice.status = "disabled"
            notice.failure_detail = "SMTP is not configured"
            db.commit()
            return
        send_email_message(user.email, notice.subject, notice.body)
        notice.status = "sent"
        notice.sent_at = datetime.now(timezone.utc)
        notice.failure_detail = ""
        db.commit()
    except Exception as exc:
        notice = db.get(UserNotification, notification_id)
        if notice:
            notice.status = "failed"
            notice.failure_detail = str(exc)[:1000]
            db.commit()
    finally:
        db.close()
