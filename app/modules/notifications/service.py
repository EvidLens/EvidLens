import os
import httpx
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.modules.database import User, Notification # we will create these 2 models next

RESEND_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.com")
FROM_NAME = os.getenv("FROM_NAME", "EvidLens")

WA_TOKEN = os.getenv("WHATSAPP_TOKEN")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

AT_KEY = os.getenv("AFRICASTALKING_API_KEY")
AT_USER = os.getenv("AFRICASTALKING_USERNAME")

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    async def send(self, user_id: int, message: str, type: str = "info", channel: str = "in_app") -> Dict[str, Any]:
        # 1. GET REAL USER
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: 
            return {"error": "User not found"}

        status = "in_app_saved"
        
        # 2. SEND VIA CHANNEL
        if channel == "email" and user.email:
            await self.send_email(user.email, f"EvidLens Alert: {type}", message)
            status = "email_sent"
        elif channel == "sms" and user.phone:
            await self.send_sms(user.phone, message)
            status = "sms_sent"
        elif channel == "whatsapp" and user.phone:
            await self.send_whatsapp(user.phone, message)
            status = "whatsapp_sent"
        
        # 3. SAVE TO DB
        notif = Notification(
            user_id=user_id, message=message, type=type, channel=channel, 
            status=status, created_at=datetime.utcnow()
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)

        return {"id": notif.id, "user_id": user_id, "channel": channel, "status": status}

    async def get_for_user(self, user_id: int) -> Dict[str, Any]:
        notifs: List[Notification] = self.db.query(Notification)\
           .filter(Notification.user_id == user_id)\
           .order_by(Notification.created_at.desc())\
           .limit(20).all()
        return {"user_id": user_id, "notifications": notifs, "count": len(notifs)}

    async def send_email(self, to_email: str, subject: str, content: str):
        if not RESEND_KEY: return
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails", 
                headers={"Authorization": f"Bearer {RESEND_KEY}"}, 
                json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to_email], "subject": subject, "html": f"<p>{content}</p>"}
            )

    async def send_sms(self, phone: str, body: str):
        if not AT_KEY or not AT_USER: return
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.africastalking.com/version1/messaging", 
                headers={"apiKey": AT_KEY, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}, 
                data={"username": AT_USER, "to": phone, "message": body}
            )

    async def send_whatsapp(self, phone: str, body: str):
        if not WA_TOKEN or not WA_PHONE_ID: return
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages", 
                headers={"Authorization": f"Bearer {WA_TOKEN}"}, 
                json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": body}}
            )
