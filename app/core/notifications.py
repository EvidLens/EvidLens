import requests
import smtplib
import logging
from email.mime.text import MIMEText
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlmodel import Session, select
from app.core.config import settings
from app.core.models import UserSubscription

UTC = timezone.utc
logger = logging.getLogger(__name__)

def normalize_ke_phone(phone: str) -> str:
    if not phone:
        return ""
    p = str(phone).strip().replace(" ", "").replace("-", "")
    if p.startswith("+254"):
        return p
    if p.startswith("254"):
        return "+" + p
    if p.startswith("0") and len(p) == 10:
        return "+254" + p[1:]
    if p.startswith("7") and len(p) == 9:
        return "+254" + p
    if p.startswith("1") and len(p) == 9:
        return "+254" + p
    return p

def send_sms(to: str, message: str) -> bool:
    phone = normalize_ke_phone(to)
    if not settings.AFRICASTALKING_API_KEY or not settings.AFRICASTALKING_USERNAME:
        logger.warning("SMS skipped, Africa's Talking not configured")
        return False
    if not phone:
        return False
    try:
        r = requests.post(
            "https://api.africastalking.com/version1/messaging",
            headers={"apiKey": settings.AFRICASTALKING_API_KEY, "Content-Type": "application/x-www-form-urlencoded"},
            data={"username": settings.AFRICASTALKING_USERNAME, "to": phone, "message": message},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception("SMS failed to %s: %s", phone, e)
        return False

def send_email(to: str, subject: str, html: str) -> bool:
    if not to:
        return False
    if settings.RESEND_API_KEY:
        try:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>", "to": [to], "subject": subject, "html": html},
                timeout=10,
            )
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Resend email failed to %s: %s", to, e)
            return False
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = MIMEText(html, "html")
            msg["Subject"] = subject
            msg["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg["To"] = to
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.exception("SMTP email failed to %s: %s", to, e)
            return False
    logger.warning("Email skipped, no RESEND_API_KEY or SMTP configured")
    return False

def send_whatsapp(to: str, message: str) -> bool:
    phone = normalize_ke_phone(to).lstrip("+")
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp skipped, not configured")
        return False
    if not phone:
        return False
    try:
        r = requests.post(
            f"https://graph.facebook.com/v21.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": message}},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception("WhatsApp failed to %s: %s", phone, e)
        return False

def get_lat_lng(county: str):
    if not settings.LOCATIONIQ_API_KEY or not county:
        return None, None
    try:
        r = requests.get(
            "https://us1.locationiq.com/v1/search.php",
            params={"key": settings.LOCATIONIQ_API_KEY, "q": f"{county},Kenya", "format": "json"},
            timeout=10,
        )
        if r.status_code == 200 and r.json():
            first = r.json()[0]
            return first.get("lat"), first.get("lon")
    except Exception as e:
        logger.exception("LocationIQ failed for %s: %s", county, e)
    return None, None

def get_subscription(db: Session, user_id: int):
    return db.exec(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
    ).first()

def check_subscription(user_id: int, db: Session) -> bool:
    sub = get_subscription(db, user_id)
    if not sub:
        raise HTTPException(status_code=402, detail="No active subscription. Start with FREE credits or upgrade.")
    expires = sub.expires_at or sub.renews_at
    if expires and expires < datetime.now(UTC):
        raise HTTPException(status_code=402, detail="Subscription expired. Renew to continue.")
    return True

def send_support_ticket(subject: str, body: str, user_email: str = "user@evidlens.co.ke") -> bool:
    html = f"<p><strong>From:</strong> {user_email}</p><p>{body}</p>"
    if settings.RESEND_API_KEY:
        return send_email(settings.SUPPORT_EMAIL, f"[EvidLens Ticket] {subject}", html)
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = MIMEText(f"From: {user_email}\n\n{body}")
            msg["Subject"] = f"[EvidLens Ticket] {subject}"
            msg["From"] = settings.FROM_EMAIL
            msg["To"] = settings.SUPPORT_EMAIL
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.exception("Support ticket failed: %s", e)
            return False
    logger.warning("Support ticket skipped, no email configured")
    return False

def notify_payment_success(to_email: str, to_phone: str, plan: str, amount: int, receipt: str) -> bool:
    subject = f"EvidLens payment received - {plan}"
    html = f"<p>Payment of KES {amount} for {plan} confirmed.</p><p>Receipt: {receipt}</p><p>Your plan is now active.</p>"
    sent = False
    if to_email:
        sent = send_email(to_email, subject, html) or sent
    if to_phone:
        sent = send_sms(to_phone, f"EvidLens: KES {amount} for {plan} confirmed. Receipt {receipt}. Plan active.") or sent
    return sent

def notify_credits_low(to_email: str, to_phone: str, credits: int) -> bool:
    if to_email:
        return send_email(to_email, "EvidLens credits running low", f"<p>You have {credits} credits left. Buy more to continue.</p>")
    if to_phone:
        return send_sms(to_phone, f"EvidLens: You have {credits} credits left. Buy more at app.evidlens.co.ke/billing")
    return False
