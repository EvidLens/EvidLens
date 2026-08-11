import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date, timezone
from sqlmodel import Session, select
from app.core.config import settings
from app.core.db import get_session
from app.modules.core.models import UserSubscription

UTC = timezone.utc

# Pull from settings.py - Single source of truth
AFRICASTALKING_API_KEY = settings.AFRICA_IS_TALKING_API_KEY
AFRICASTALKING_USERNAME = settings.AFRICA_IS_TALKING_USERNAME
RESEND_API_KEY = settings.RESEND_API_KEY if hasattr(settings, 'RESEND_API_KEY') else ""
FROM_NAME = settings.APP_NAME
FROM_EMAIL = settings.FROM_EMAIL if hasattr(settings, 'FROM_EMAIL') else "noreply@evidlens.co.ke"
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN if hasattr(settings, 'WHATSAPP_TOKEN') else ""
WHATSAPP_PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID if hasattr(settings, 'WHATSAPP_PHONE_NUMBER_ID') else ""
LOCATIONIQ_KEY = settings.LOCATIONIQ_KEY if hasattr(settings, 'LOCATIONIQ_KEY') else ""
SUPPORT_EMAIL = settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else "support@evidlens.co.ke"
SMTP_USER = settings.SMTP_USER if hasattr(settings, 'SMTP_USER') else ""
SMTP_PASS = settings.SMTP_PASS if hasattr(settings, 'SMTP_PASS') else ""

def send_sms(to: str, message: str):
    if not AFRICASTALKING_API_KEY or not AFRICASTALKING_USERNAME: return
    url = "https://api.africastalking.com/version1/messaging"
    headers = {"apiKey": AFRICASTALKING_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    data = {"username": AFRICASTALKING_USERNAME, "to": to, "message": message}
    try:
        r = requests.post(url, data=data, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"SMS Error: {e}")

def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY: return
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to], "subject": subject, "html": html},
            timeout=10
        )
        r.raise_for_status()
    except Exception as e:
        print(f"Email Error: {e}")

def send_whatsapp(to: str, message: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID: return
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"WhatsApp Error: {e}")

def get_lat_lng(county: str):
    if not LOCATIONIQ_KEY: return None, None
    try:
        r = requests.get(
            f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&q={county},Kenya&format=json",
            timeout=10
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]["lat"], r.json()[0]["lon"]
    except Exception as e:
        print(f"LocationIQ Error: {e}")
    return None, None

def get_subscription(db: Session, user_id: int):
    return db.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()

def check_subscription(user_id: int, db: Session):
    sub = get_subscription(db, user_id)
    if not sub or sub.status!= "active" or sub.renews_at < datetime.now(UTC):
        # Free tier: 3 queries limit
        raise HTTPException(status_code=402, detail="Subscribe to continue. Free queries exhausted.")
    return True

def send_support_ticket(subject: str, body: str, user_email: str = "user@evidlens.co.ke"):
    """Raises a ticket to support@evidlens.co.ke via SMTP"""
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP creds missing")
        return False
    try:
        msg = MIMEText(f"From: {user_email}\n\n{body}")
        msg['Subject'] = f"[EvidLens Ticket] {subject}"
        msg['From'] = SMTP_USER
        msg['To'] = SUPPORT_EMAIL

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Ticket Error: {e}")
        return False
