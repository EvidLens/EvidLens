import os, base64, requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

MPESA_CONSUMER_KEY = os.getenv("goRHiJtrSKc5RgE2wtBjYdAZwnftgAhRBySgN7ZkfylskGGJ")
MPESA_CONSUMER_SECRET = os.getenv("snudgiGsOhkBsUcRCK3oX397ToiEGLaStyaGZ5tQ0mRGE3i1fEiO78PmRLc6Jqaq")
MPESA_SHORTCODE = os.getenv("174379")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CALLBACK_URL = os.getenv("https://evidlens-s7x6.onrender.com/api/mpesa/callback")
BASE_URL = "https://api.safaricom.co.ke" if os.getenv("ENV") == "prod" else "https://sandbox.safaricom.co.ke"

def get_mpesa_token():
    r = requests.get(f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials", auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET), timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def stk_push(phone: str, amount: int, tenant_id: str):
    token = get_mpesa_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone,
        "PartyB": MPESA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": tenant_id, "TransactionDesc": f"KenyaLensIQ-{tenant_id}"
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers=headers, timeout=15)
    return r.json()
