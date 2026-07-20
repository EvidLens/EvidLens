import os
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session

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
        # TODO: Lookup user email/phone from DB. For now just log
        result = {"user_id": user_id, "channel": channel, "status": "sent"}
        
        if channel == "email":
            await self.send_email("test@evidlens.com", f"EvidLens Alert: {type}", message)
            result["status"] = "email_sent"
        elif channel == "sms":
            await self.send_sms("+254700000", message)
            result["status"] = "sms_sent"
        elif channel == "whatsapp":
            await self.send_whatsapp("+254700000000", message)
            result["status"] = "whatsapp_sent"
        
        return result

    async def get_for_user(self, user_id: int) -> Dict[str, Any]:
        # TODO: Query notifications table
        return {"user_id": user_id, "notifications": [], "count": 0}

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
                headers={"apiKey": AT_KEY}, 
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
