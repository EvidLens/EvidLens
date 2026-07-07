import os
from sqlalchemy.orm import Session
from sqlalchemy import desc
import requests
import base64
from datetime import datetime
from typing import Dict, Any

from .models import Payment, Subscription, MpesaTransaction, PaymentStatus
from app.modules.db import get_db

# 1. MPESA ENV VARS - Set these in Render > Environment
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

# 2. TOGGLE SANDBOX / PROD URLS
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox") # set to "prod" in Render for live

if MPESA_ENV == "prod":
    MPESA_BASE_URL = "https://api.safaricom.co.ke"
else:
    MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"


def get_access_token() -> str:
    """Get M-Pesa OAuth token"""
    api_url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(api_url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return response.json()['access_token']


def initiate_stk_push(db: Session, phone_number: str, amount: float, account_reference: str, user_id: int) -> Dict[str, Any]:
    """
    Initiate M-Pesa STK Push
    """
    access_token = get_access_token()
    api_url = f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()
    
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": f"EvidLens Payment - {account_reference}"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(api_url, json=payload, headers=headers)
    data = response.json()
    
    if data.get("ResponseCode") == "0":
        new_payment = Payment(
            user_id=user_id,
            phone_number=phone_number,
            amount_kes=amount,
            checkout_request_id=data.get("CheckoutRequestID"),
            payment_type="subscription",
            status=PaymentStatus.PENDING,
            payment_metadata={"mpesa_response": data}
        )
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
    
    return data


def handle_c2b_webhook(db: Session, payload: Dict[str, Any]) -> Dict[str, str]:
    """Handle M-Pesa STK Callback"""
    result_code = payload.get("Body", {}).get("stkCallback", {}).get("ResultCode")
    checkout_id = payload.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
    
    payment = db.query(Payment).filter(Payment.checkout_request_id == checkout_id).first()
    if not payment:
        return {"status": "payment_not_found"}
    
    if result_code == 0:
        payment.status = PaymentStatus.SUCCESS
        payment.completed_at = datetime.utcnow()
        items = payload.get("Body", {}).get("stkCallback", {}).get("CallbackMetadata", {}).get("Item", [])
        for item in items:
            if item.get("Name") == "MpesaReceiptNumber":
                payment.mpesa_receipt_number = item.get("Value")
    else:
        payment.status = PaymentStatus.FAILED
    
    payment.payment_metadata = payload
    db.commit()
    
    return {"status": "ok"}


def verify_payment(db: Session, checkout_request_id: str) -> Dict[str, Any]:
    """Verify payment status by checkout_request_id"""
    payment = db.query(Payment).filter(Payment.checkout_request_id == checkout_request_id).first()
    if not payment:
        return {"status": "not_found", "message": "Payment not found"}
    
    return {
        "status": payment.status.value,
        "amount": payment.amount_kes,
        "receipt": payment.mpesa_receipt_number,
        "created_at": payment.created_at
    }


def process_b2c(db: Session, phone_number: str, amount: float, remarks: str) -> Dict[str, Any]:
    """Process M-Pesa B2C Payment - Pay out"""
    access_token = get_access_token()
    api_url = f"{MPESA_BASE_URL}/mpesa/b2c/v1/paymentrequest"
    
    payload = {
        "InitiatorName": os.getenv("MPESA_INITIATOR_NAME"),
        "SecurityCredential": os.getenv("MPESA_SECURITY_CREDENTIAL"),
        "CommandID": "BusinessPayment",
        "Amount": int(amount),
        "PartyA": MPESA_SHORTCODE,
        "PartyB": phone_number,
        "Remarks": remarks,
        "QueueTimeOutURL": MPESA_CALLBACK_URL,
        "ResultURL": MPESA_CALLBACK_URL,
        "Occasion": "EvidLens Refund"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(api_url, json=payload, headers=headers)
    return response.json()


def create_subscription(db: Session, user_id: int, plan: str, amount: float) -> Dict[str, Any]:
    """
    Create a new subscription record. STK push should be called after this
    """
    existing = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).first()
    
    if existing:
        return {"error": "User already has an active subscription"}
    
    new_sub = Subscription(
        user_id=user_id,
        plan=plan,
        amount_kes=amount,
        status="pending",
        start_date=datetime.utcnow()
    )
    
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    
    return {
        "id": new_sub.id,
        "plan": new_sub.plan,
        "amount": new_sub.amount_kes,
        "status": new_sub.status
    }


def get_subscription(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get active subscription for a user
    """
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active"
    ).first()
    
    if not sub:
        return {"status": "no_active_subscription"}
    
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "plan": sub.plan,
        "amount": sub.amount_kes,
        "status": sub.status,
        "start_date": sub.start_date,
        "end_date": sub.end_date
    }
