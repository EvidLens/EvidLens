import os, httpx
RESEND_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME")
WA_TOKEN = os.getenv("WHATSAPP_TOKEN")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
AT_KEY = os.getenv("AFRICASTALKING_API_KEY")
AT_USER = os.getenv("AFRICASTALKING_USERNAME")

async def send_email(to_email, subject, content):
    if not RESEND_KEY: return
    await httpx.AsyncClient().post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {RESEND_KEY}"}, json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to_email], "subject": subject, "html": content})

async def send_sms(phone, body):
    if not AT_KEY: return
    await httpx.AsyncClient().post("https://api.africastalking.com/version1/messaging", headers={"apiKey": AT_KEY}, data={"username": AT_USER, "to": phone, "message": body})

async def send_whatsapp(phone, body):
    if not WA_TOKEN: return
    await httpx.AsyncClient().post(f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages", headers={"Authorization": f"Bearer {WA_TOKEN}"}, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": body}})
