import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
from fastapi import Request, Depends, HTTPException
from sqlmodel import Session, select
from app.modules.core.db import get_session
from app.modules.kenyalensiq.models import KenyaLensSubscription, KenyaLensApiUsage
from app.core import settings

# Pull from settings.py - Single source of truth
AFRICASTALKING_API_KEY = settings.AFRICASTALKING_API_KEY
AFRICASTALKING_USERNAME = settings.AFRICASTALKING_USERNAME
RESEND_API_KEY = settings.RESEND_API_KEY
FROM_NAME = settings.FROM_NAME
FROM_EMAIL = settings.FROM_EMAIL
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
WHATSAPP_PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID
LOCATIONIQ_KEY = settings.LOCATIONIQ_KEY
SUPPORT_EMAIL = settings.SUPPORT_EMAIL
SMTP_USER = settings.SMTP_USER
SMTP_PASS = settings.SMTP_PASS

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

def get_current_user(request: Request, session: Session = Depends(get_session)):
    # TODO: Replace with real JWT auth. This is dev only
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return int(user_id)

def get_subscription(db: Session, user_id: int):
    return db.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == user_id)).first()

def get_queries_today(db: Session, user_id: int):
    usage = db.exec(
        select(KenyaLensApiUsage).where(
            KenyaLensApiUsage.user_id == user_id,
            KenyaLensApiUsage.date == date.today()
        )
    ).all()
    return len(usage)

def log_query(db: Session, user_id: int):
    db.add(KenyaLensApiUsage(user_id=user_id, date=date.today()))
    db.commit()

def check_subscription(user_id: int, db: Session):
    sub = get_subscription(db, user_id)
    if not sub or sub.status!= "active" or sub.expires_at < datetime.utcnow():
        if get_queries_today(db, user_id) >= 3:
            raise HTTPException(status_code=402, detail="Subscribe to continue. 3 free queries used.")
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
