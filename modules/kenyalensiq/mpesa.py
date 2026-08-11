import os
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

BASE_URL = "https://api.safaricom.co.ke" if os.getenv("ENV") == "prod" else "https://sandbox.safaricom.co.ke"

def get_mpesa_token():
    try:
        r = requests.get(
            f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
            timeout=10
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception as e:
        print(f"M-Pesa Token Error: {e}")
        raise HTTPException(500, "M-Pesa service unavailable")

def stk_push(phone: str, amount: int, tenant_id: str):
    try:
        token = get_mpesa_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
        
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": MPESA_CALLBACK_URL,
            "AccountReference": tenant_id,
            "TransactionDesc": f"EvidLens-{tenant_id}"
        }
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"STK Push Error: {e}")
        return {"ResponseCode": "1", "ResponseDescription": str(e)}
