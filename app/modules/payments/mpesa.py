from fastapi import APIRouter, Depends, Request, HTTPException
from sqlmodel import Session
from datetime import datetime, timedelta
import requests
import base64

from app.modules.core.db import get_session, get_db
from app.modules.core.models import User, Subscription
from app.modules.auth.dependencies import get_current_user
from app.core.service import _core
from app.core import settings

router = APIRouter()

# Pull from settings.py - Single source of truth
CURRENCY = settings.CURRENCY
CURRENCY_SYMBOL = settings.CURRENCY_SYMBOL
MPESA_ENV = settings.MPESA_ENV
DARAJA_CONSUMER_KEY = settings.MPESA_CONSUMER_KEY
DARAJA_CONSUMER_SECRET = settings.MPESA_CONSUMER_SECRET
MPESA_SHORTCODE = settings.MPESA_SHORTCODE
MPESA_PASSKEY = settings.MPESA_PASSKEY
MPESA_CALLBACK_URL = settings.MPESA_CALLBACK_URL

# Pull pricing from core.service.py - Single source of truth
PRICING = _core.PRICING
ADDONS = _core.ADDONS
ALC = _core.ALC

def format_kes(amount: int) -> str:
    if amount == -1:
        return "Unlimited"
    return f"{CURRENCY_SYMBOL} {amount:,}"

# ====== 1. M-PESA DARAJA HELPERS ======
def get_timestamp():
    return datetime.utcnow().strftime('%Y%m%d%H%M%S')

def get_password(shortcode, passkey, timestamp):
    data = shortcode + passkey + timestamp
    encoded = base64.b64encode(data.encode())
    return encoded.decode('utf-8')

def get_daraja_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=(DARAJA_CONSUMER_KEY, DARAJA_CONSUMER_SECRET))
    r.raise_for_status()
    return r.json()["access_token"]

def get_subscription(db: Session, user_id: int):
    return db.query(Subscription).filter(Subscription.user_id == user_id).first()

@router.get("/api/pricing")
def api_pricing():
    return {"plans": PRICING, "addons": ADDONS, "alc": ALC}

@router.post("/api/checkout")
def mpesa_stk_push(payload: dict, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    plan = payload.get("plan")
    billing = payload.get("billing")
    phone = payload.get("phone")
    price = PRICING[plan][billing]
    credits_map = {"BASIC": 10, "PROFESSIONAL": 100, "ENTERPRISE": 99999}

    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp)
    api_url = ("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
    headers = {"Authorization": "Bearer " + token}
    payload_mpesa = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": price,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": f"EvidLens-{plan}-{user.id}", # Format: EvidLens-BASIC-123
        "TransactionDesc": f"{plan} {billing} Subscription"
    }
    r = requests.post(api_url, json=payload_mpesa, headers=headers)

    session.add(Subscription(user_id=user.id, plan=plan, billing=billing, status="Pending", credits=credits_map[plan]))
    session.commit()
    return r.json()

@router.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    """Daraja will POST here after payment"""
    data = await request.json()
    try:
        stk = data["Body"]["stkCallback"]
        if stk["ResultCode"]!= 0:
            return {"ResultCode": 0, "ResultDesc": "Failed"}

        items = {i["Name"]: i["Value"] for i in stk["CallbackMetadata"]["Item"]}
        account_ref = items["AccountReference"]
        mpesa_receipt = items["MpesaReceiptNumber"]
        amount = items["Amount"]

        # AccountReference format: "EvidLens-BASIC-123"
        parts = account_ref.split("-")
        plan = parts[1]
        user_id = int(parts[2])

        # Give 30 days for monthly, 365 for annual
        plan_data = PRICING.get(plan)
        if not plan_data:
            return {"ResultCode": 0, "ResultDesc": "Plan not found"}

        is_annual = amount == plan_data["annual"]
        days = 365 if is_annual else 30
        expires = datetime.utcnow() + timedelta(days=days)

        sub = get_subscription(db, user_id)
        if sub:
            sub.plan = plan
            sub.billing = "annual" if is_annual else "monthly"
            sub.status = "active"
            sub.expires_at = expires
            sub.mpesa_receipt = mpesa_receipt
            sub.credits = plan_data["annual"] if is_annual else plan_data["monthly"]
        else:
            db.add(Subscription(
                user_id=user_id,
                plan=plan,
                billing="annual" if is_annual else "monthly",
                status="active",
                expires_at=expires,
                mpesa_receipt=mpesa_receipt,
                credits=plan_data["annual"] if is_annual else plan_data["monthly"]
            ))
        db.commit()
    except Exception as e:
        print(f"MPESA Callback Error: {e}")
        pass
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

def stk_push(user_id: int, plan_name: str, phone: str):
    plan_data = _core.PRICING.get(plan_name)
    amount = plan_data["monthly"]

    account_ref = f"EvidLens-{plan_name}-{user_id}" # MATCH checkout format

    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp)

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
        "AccountReference": account_ref, # CRITICAL
        "TransactionDesc": f"Upgrade to {plan_name}"
    }

    api_url = ("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
    headers = {"Authorization": "Bearer " + token}
    r = requests.post(api_url, json=payload, headers=headers)
    return r.json()
def get_timestamp(): 
    return datetime.now().strftime('%Y%m%d%H%M%S
